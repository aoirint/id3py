import codecs
import csv
import importlib.resources as ILR
import re
from dataclasses import dataclass
from io import BytesIO, StringIO
from typing import List, Literal, Optional

from pydantic import BaseModel, parse_obj_as

from .utils import decode_padded_str, safe_ljust

TextEncodingDescription = Literal["ISO-8859-1", "UTF-16", "UTF-16BE", "UTF-8"]


class AvailableFrameId(BaseModel):
    frame_id: str
    frame_name: str


def __load_available_frame_ids() -> List[AvailableFrameId]:
    frame_ids_csv_text = ILR.read_text("aoirint_id3", "id3v2_4_available_frame_ids.csv")
    reader = csv.DictReader(
        StringIO(frame_ids_csv_text), fieldnames=["frame_id", "frame_name"]
    )

    records = list(reader)
    return parse_obj_as(List[AvailableFrameId], records)


available_frame_ids = __load_available_frame_ids()
available_text_information_frame_ids = list(
    filter(
        lambda frame_id: frame_id[0] == "T",
        map(lambda item: item.frame_id, available_frame_ids),
    )
)


def decode_id3v2_4_synchsafe_integer(encoded: bytes, length: int) -> int:
    raw = int.from_bytes(encoded, byteorder="big")
    value = 0

    for index in range(length):
        mask = 0b0111_1111 << (index * 8)
        value = value | ((raw & mask) >> index)

    return value


def encode_id3v2_4_synchsafe_integer(value: int, length: int) -> bytes:
    encoded = 0

    for index in range(length):
        mask = 0b0111_1111 << (index * 7)
        encoded = encoded | ((value & mask) << index)

    return encoded.to_bytes(length=length, byteorder="big")


def encode_id3v2_4_header(
    size: int,  # tag size excluding padding and header
    flag_is_unsynchronisation: bool = False,
    flag_is_extended_header: bool = False,
    flag_is_experimental_indicator: bool = False,
    flag_is_footer_present: bool = False,
) -> bytes:
    bio = BytesIO()
    bio.write(b"ID3")  # 3 bytes

    major_version = 4
    bio.write(major_version.to_bytes(1, byteorder="big"))

    revision_number = 0
    bio.write(revision_number.to_bytes(1, byteorder="big"))

    flag = 0b0000_0000
    if flag_is_unsynchronisation:
        flag |= 0b1000_0000

    if flag_is_extended_header:
        flag |= 0b0100_0000

    if flag_is_experimental_indicator:
        flag |= 0b0010_0000

    if flag_is_footer_present:
        flag |= 0b0001_0000

    bio.write(flag.to_bytes(1, byteorder="big"))

    bio.write(encode_id3v2_4_synchsafe_integer(value=size, length=4))

    return bio.getvalue()


def encode_id3v2_4_extended_header(
    flag_tag_is_update: bool,
    crc_data_present: Optional[bytes],
    tag_restrictions: Optional[bytes],
) -> bytes:
    if crc_data_present is not None and len(crc_data_present) != 5:
        raise Exception(
            f"Total frame CRC (CRC-32 data) must be 5 bytes synchsafe integer ({len(crc_data_present)} != 5)."
        )

    if tag_restrictions is not None and len(tag_restrictions) != 1:
        raise Exception(
            f"Tag restrictions must be 1 byte ({len(tag_restrictions)} != 1)."
        )

    bio = BytesIO()

    size = 6
    if flag_tag_is_update is not None:
        size += 1

    if crc_data_present is not None:
        size += 5

    if tag_restrictions is not None:
        size += 2

    bio.write(encode_id3v2_4_synchsafe_integer(value=size, length=4))

    number_of_flag_bytes = 1  # always 1
    bio.write(number_of_flag_bytes.to_bytes(1, byteorder="big"))

    flag = 0b0000_0000

    if flag_tag_is_update:
        flag |= 0b1000_0000

    if crc_data_present is not None:
        flag |= 0b0100_0000

    if tag_restrictions is not None:
        flag |= 0b0010_0000

    bio.write(flag.to_bytes(1, byteorder="big"))

    # Extended header data
    if flag_tag_is_update:
        flag_data_length = 0
        bio.write(flag_data_length.to_bytes(1, byteorder="big"))

    if crc_data_present is not None:
        flag_data_length = 5
        bio.write(flag_data_length.to_bytes(1, byteorder="big"))
        bio.write(crc_data_present)  # 5 bytes synchsafe integer

    if tag_restrictions is not None:
        flag_data_length = 1
        bio.write(flag_data_length.to_bytes(1, byteorder="big"))
        bio.write(tag_restrictions)  # 1 byte

    return bio.getvalue()


def encode_id3v2_4_frame(
    frame_id: str,
    frame_data: bytes,
    flag_is_tag_alter_preservation: bool = False,
    flag_is_file_alter_preservation: bool = False,
    flag_is_read_only: bool = False,
    flag_is_grouping_identity: bool = False,
    flag_is_compression: bool = False,
    flag_is_encryption: bool = False,
    flag_is_unsynchronisation: bool = False,
    flag_data_length_indicator: bool = False,
) -> bytes:
    bio = BytesIO()

    frame_id_bytes = frame_id.encode(encoding="ascii")
    if len(frame_id_bytes) != 4:
        raise Exception(f"Invalid Frame ID ({frame_id}). Size {len(frame_id)} != 4")

    bio.write(frame_id_bytes)

    frame_size = len(frame_data)
    bio.write(encode_id3v2_4_synchsafe_integer(frame_size, length=4))

    flag1 = 0b0000_0000
    if flag_is_tag_alter_preservation:
        flag1 |= 0b0100_0000

    if flag_is_file_alter_preservation:
        flag1 |= 0b0010_0000

    if flag_is_read_only:
        flag1 |= 0b0001_0000

    bio.write(flag1.to_bytes(1, byteorder="big"))

    flag2 = 0b0000_0000
    if flag_is_grouping_identity:
        flag2 |= 0b0100_0000

    if flag_is_compression:
        flag2 |= 0b0000_1000

    if flag_is_encryption:
        flag2 |= 0b0000_0100

    if flag_is_unsynchronisation:
        flag2 |= 0b0000_0010

    if flag_data_length_indicator:
        flag2 |= 0b0000_0001

    bio.write(flag2.to_bytes(1, byteorder="big"))

    bio.write(frame_data)

    return bio.getvalue()


def encode_id3v2_4_text_information_frame_data(
    text_encoding: TextEncodingDescription,
    information: str,
) -> bytes:
    bio = BytesIO()

    if text_encoding == "ISO-8859-1":
        text_encoding_python = "latin-1"
        text_encoding_bom_bytes = b""
        text_encoding_byte = 0
    elif text_encoding == "UTF-16":  # UTF-16 Big Endian with BOM
        text_encoding_python = "utf-16be"  # UTF-16 Big Endian without BOM
        text_encoding_bom_bytes = codecs.BOM_UTF16_BE
        text_encoding_byte = 1
    elif text_encoding == "UTF-16BE":  # UTF-16 Big Endian without BOM
        text_encoding_python = "utf-16be"  # UTF-16 Big Endian without BOM
        text_encoding_bom_bytes = b""
        text_encoding_byte = 2
    elif text_encoding == "UTF-8":
        text_encoding_python = "utf-8"  # UTF-8
        text_encoding_bom_bytes = b""
        text_encoding_byte = 3
    else:
        raise Exception(
            f"Unsupported text encoding ({text_encoding}). "
            "Use ISO-8859-1 (latin-1), UTF-16 (utf-16be with BOM), UTF-16BE (utf-16be without BOM), or UTF-8 (utf-8)."
        )

    information_bytes = text_encoding_bom_bytes + information.encode(
        encoding=text_encoding_python
    )

    bio.write(text_encoding_byte.to_bytes(1, byteorder="big"))
    bio.write(information_bytes)

    return bio.getvalue()


@dataclass
class DecodeId3v2_4TextInformationFrameResult:
    information: str


def decode_id3v2_4_text_information_frame_data(
    data: bytes,
) -> DecodeId3v2_4TextInformationFrameResult:
    text_encoding_byte = data[0]

    if text_encoding_byte == 0:
        text_encoding_python = "latin-1"
    elif text_encoding_byte == 1:
        text_encoding_python = "utf-16"  # UTF-16 with BOM
    elif text_encoding_byte == 2:
        text_encoding_python = "utf-16be"  # UTF-16 Big Endian without BOM
    elif text_encoding_byte == 3:
        text_encoding_python = "utf-8"  # UTF-8
    else:
        raise Exception(
            f"Unsupported text encoding byte ({text_encoding_byte}). "
            "Only 0 (ISO-8859-1, latin-1), 1 (UTF-16, utf-16 with BOM), 2 (UTF-16BE, utf-16be without BOM), or 3 (UTF-8, utf-8) is allowed."
        )

    information = data[1:].decode(encoding=text_encoding_python)  # BOM removed

    return DecodeId3v2_4TextInformationFrameResult(
        information=information,
    )


def encode_id3v2_4_comment_frame_data(
    text_encoding: TextEncodingDescription,
    language: str,  # ISO 639-2
    content_description: str,
    actual_comment: str,
) -> bytes:
    bio = BytesIO()

    if text_encoding == "ISO-8859-1":
        text_encoding_python = "latin-1"
        text_encoding_bom_bytes = b""
        text_encoding_byte = 0
        text_termination_bytes = b"\x00"
    elif text_encoding == "UTF-16":  # UTF-16 Big Endian with BOM
        text_encoding_python = "utf-16be"  # UTF-16 Big Endian without BOM
        text_encoding_bom_bytes = codecs.BOM_UTF16_BE
        text_encoding_byte = 1
        text_termination_bytes = b"\x00\x00"
    elif text_encoding == "UTF-16BE":  # UTF-16 Big Endian without BOM
        text_encoding_python = "utf-16be"  # UTF-16 Big Endian without BOM
        text_encoding_bom_bytes = b""
        text_encoding_byte = 2
        text_termination_bytes = b"\x00\x00"
    elif text_encoding == "UTF-8":
        text_encoding_python = "utf-8"  # UTF-8
        text_encoding_bom_bytes = b""
        text_encoding_byte = 3
        text_termination_bytes = b"\x00"
    else:
        raise Exception(
            f"Unsupported text encoding ({text_encoding}). "
            "Use ISO-8859-1 (latin-1), UTF-16 (utf-16be with BOM), UTF-16BE (utf-16be without BOM), or UTF-8 (utf-8)."
        )

    # 2 or 3 latin alphabet code in lower case
    if not re.match("^[a-z]{2,3}$", language):
        raise Exception("Unsupported language. Use ISO 639-2.")

    language_bytes = language.encode("ascii")
    if len(language_bytes) == 3:
        pass
    elif len(language_bytes) == 2:
        language_bytes += safe_ljust(language_bytes, 3)  # always 3 bytes
    else:
        raise Exception("Invalid language bytes. This is bug?")

    content_description_bytes = text_encoding_bom_bytes + content_description.encode(
        encoding=text_encoding_python
    )
    actual_comment_bytes = text_encoding_bom_bytes + actual_comment.encode(
        encoding=text_encoding_python
    )

    bio.write(text_encoding_byte.to_bytes(1, byteorder="big"))
    bio.write(language_bytes)
    bio.write(content_description_bytes)
    bio.write(text_termination_bytes)  # NULL termination of content description
    bio.write(actual_comment_bytes)

    return bio.getvalue()


@dataclass
class DecodeId3v2_4CommentFrameResult:
    language: str  # ISO 639-2
    content_description: str
    actual_comment: str


def decode_id3v2_4_comment_frame_data(data: bytes) -> DecodeId3v2_4CommentFrameResult:
    text_encoding_byte = data[0]

    if text_encoding_byte == 0:
        text_encoding_python = "latin-1"
        text_termination_bytes = b"\x00"
    elif text_encoding_byte == 1:
        text_encoding_python = "utf-16"  # UTF-16 with BOM
        text_termination_bytes = b"\x00\x00"
    elif text_encoding_byte == 2:
        text_encoding_python = "utf-16be"  # UTF-16 Big Endian without BOM
        text_termination_bytes = b"\x00\x00"
    elif text_encoding_byte == 3:
        text_encoding_python = "utf-8"  # UTF-8
        text_termination_bytes = b"\x00"
    else:
        raise Exception(
            f"Unsupported text encoding byte ({text_encoding_byte}). "
            "Only 0 (ISO-8859-1, latin-1), 1 (UTF-16, utf-16 with BOM), 2 (UTF-16BE, utf-16be), or 3 (UTF-8, utf-8) is allowed."
        )

    language = decode_padded_str(data[1:4], encoding="ascii")

    content_descirption_bytes, actual_comment_bytes = data[4:].split(
        text_termination_bytes, maxsplit=1
    )
    content_descirption = content_descirption_bytes.decode(
        encoding=text_encoding_python
    )
    actual_comment = actual_comment_bytes.decode(encoding=text_encoding_python)

    return DecodeId3v2_4CommentFrameResult(
        language=language,
        content_description=content_descirption,
        actual_comment=actual_comment,
    )


def encode_id3v2_4_attached_picture_frame(
    text_encoding: TextEncodingDescription,
    mime_type: str,
    picture_type: int,
    description: str,
    picture_data: bytes,
) -> bytes:
    bio = BytesIO()

    if text_encoding == "ISO-8859-1":
        text_encoding_python = "latin-1"
        text_encoding_bom_bytes = b""
        text_encoding_byte = 0
        text_termination_bytes = b"\x00"
    elif text_encoding == "UTF-16":  # UTF-16 Big Endian with BOM
        text_encoding_python = "utf-16be"  # UTF-16 Big Endian without BOM
        text_encoding_bom_bytes = codecs.BOM_UTF16_BE
        text_encoding_byte = 1
        text_termination_bytes = b"\x00\x00"
    elif text_encoding == "UTF-16BE":
        text_encoding_python = "utf-16be"  # UTF-16 Big Endian without BOM
        text_encoding_bom_bytes = b""
        text_encoding_byte = 2
        text_termination_bytes = b"\x00\x00"
    elif text_encoding == "UTF-8":
        text_encoding_python = "utf-8"  # UTF-8
        text_encoding_bom_bytes = b""
        text_encoding_byte = 3
        text_termination_bytes = b"\x00"
    else:
        raise Exception(
            f"Unsupported text encoding ({text_encoding}). "
            "Use ISO-8859-1 (latin-1), UTF-16 (utf-16be with BOM), UTF-16BE (utf-16be), or UTF-8 (utf-8)."
        )

    description_bytes = text_encoding_bom_bytes + description.encode(
        encoding=text_encoding_python
    )

    bio.write(text_encoding_byte.to_bytes(1, byteorder="big"))
    bio.write(mime_type.encode("ascii"))
    bio.write(b"\x00")
    bio.write(picture_type.to_bytes(1, byteorder="big"))
    bio.write(description_bytes)
    bio.write(text_termination_bytes)  # NULL termination of content description
    bio.write(picture_data)

    return bio.getvalue()


@dataclass
class DecodeId3v2_4AttachedPictureFrameResult:
    mime_type: str
    picture_type: int
    description: str
    picture_data: bytes


def decode_id3v2_4_attached_picture_frame_data(
    data: bytes,
) -> DecodeId3v2_4AttachedPictureFrameResult:
    text_encoding_byte = data[0]

    if text_encoding_byte == 0:
        text_encoding_python = "latin-1"
        text_termination_bytes = b"\x00"
    elif text_encoding_byte == 1:
        text_encoding_python = "utf-16"  # UTF-16 with BOM
        text_termination_bytes = b"\x00\x00"
    elif text_encoding_byte == 2:
        text_encoding_python = "utf-16be"  # UTF-16 Big Endian without BOM
        text_termination_bytes = b"\x00\x00"
    elif text_encoding_byte == 3:
        text_encoding_python = "utf-8"  # UTF-8
        text_termination_bytes = b"\x00"
    else:
        raise Exception(
            f"Unsupported text encoding byte ({text_encoding_byte}). "
            "Only 0 (ISO-8859-1, latin-1), 1 UTF-16 (utf-16), 2 (UTF-16BE, utf-16be), or 3 (UTF-8, utf-8) is allowed."
        )

    mime_type_bytes, data_left = data[1:].split(b"\x00", maxsplit=1)
    mime_type = mime_type_bytes.decode(encoding="ascii")

    picture_type = data_left[0]
    descirption_bytes, picture_data = data_left[1:].split(
        text_termination_bytes, maxsplit=1
    )

    description = descirption_bytes.decode(encoding=text_encoding_python)

    return DecodeId3v2_4AttachedPictureFrameResult(
        mime_type=mime_type,
        picture_type=picture_type,
        description=description,
        picture_data=picture_data,
    )


def encode_id3v2_4(
    title: str,
    artist: str,
    album: str,
    year: str,
    comment: str,
    track_number: int,
    total_track_number: Optional[int],
    text_encoding: TextEncodingDescription,
    flag_is_unsynchronisation: bool = False,
    flag_is_extended_header: bool = False,
    flag_is_experimental_indicator: bool = False,
    flag_is_footer_present: bool = False,
) -> bytes:
    if track_number < 0:
        raise Exception(f"Invalid Track Number: {track_number}")
    if total_track_number is not None and total_track_number < 0:
        raise Exception(f"Invalid Total Track Number: {total_track_number}")

    frames_bio = BytesIO()

    # TT2 frame
    frames_bio.write(
        encode_id3v2_4_frame(
            frame_id="TIT2",
            frame_data=encode_id3v2_4_text_information_frame_data(
                text_encoding=text_encoding,
                information=title,
            ),
        ),
    )
    frames_bio.write(
        encode_id3v2_4_frame(
            frame_id="TPE1",
            frame_data=encode_id3v2_4_text_information_frame_data(
                text_encoding=text_encoding,
                information=artist,
            ),
        ),
    )
    frames_bio.write(
        encode_id3v2_4_frame(
            frame_id="TALB",
            frame_data=encode_id3v2_4_text_information_frame_data(
                text_encoding=text_encoding,
                information=album,
            ),
        ),
    )
    frames_bio.write(
        encode_id3v2_4_frame(
            frame_id="TYER",
            frame_data=encode_id3v2_4_text_information_frame_data(
                text_encoding=text_encoding,
                information=year,
            ),
        ),
    )
    frames_bio.write(
        encode_id3v2_4_frame(
            frame_id="COMM",
            frame_data=encode_id3v2_4_comment_frame_data(
                text_encoding=text_encoding,
                language="eng",  # English
                content_description="Comment",
                actual_comment=comment,
            ),
        ),
    )
    frames_bio.write(
        encode_id3v2_4_frame(
            frame_id="TRCK",
            frame_data=encode_id3v2_4_text_information_frame_data(
                text_encoding=text_encoding,
                information=f"{track_number}/{total_track_number}"
                if total_track_number is not None
                else str(track_number),
            ),
        ),
    )

    frames_bytes = frames_bio.getvalue()

    extended_header_bytes = (
        encode_id3v2_4_extended_header(
            flag_tag_is_update=False,
            crc_data_present=None,
            tag_restrictions=None,
        )
        if flag_is_extended_header
        else b""
    )

    # header
    size = len(extended_header_bytes) + len(frames_bytes)

    bio = BytesIO()
    bio.write(
        encode_id3v2_4_header(
            size=size,
            flag_is_unsynchronisation=flag_is_unsynchronisation,
            flag_is_extended_header=flag_is_extended_header,
            flag_is_experimental_indicator=flag_is_experimental_indicator,
            flag_is_footer_present=flag_is_footer_present,
        )
    )
    bio.write(extended_header_bytes)
    bio.write(frames_bytes)

    return bio.getvalue()


@dataclass
class DecodeId3v2_4Result:
    title: Optional[str]
    artist: Optional[str]
    album: Optional[str]
    year: Optional[str]
    comment: Optional[str]
    track_number: Optional[int]
    total_track_number: Optional[int]
    attached_picture: Optional[DecodeId3v2_4AttachedPictureFrameResult]
    flag_is_unsynchronisation: bool
    flag_is_extended_header: bool
    flag_is_experimental_indicator: bool
    flag_is_footer_present: bool


def decode_id3v2_4(data: bytes) -> DecodeId3v2_4Result:
    bio = BytesIO(data)
    identifier = bio.read(3)
    if identifier != b"ID3":
        raise Exception("ID3v2_4: Invalid identifier")

    major_version = int.from_bytes(bio.read(1), byteorder="big")
    revision_number = int.from_bytes(bio.read(1), byteorder="big")
    if major_version != 4 or revision_number != 0:
        raise Exception("ID3v2_4: Invalid version")

    flag = int.from_bytes(bio.read(1), byteorder="big")
    flag_is_unsynchronisation = (flag & 0b1000_0000) == 0b1000_0000
    flag_is_extended_header = (flag & 0b0100_0000) == 0b0100_0000
    flag_is_experimental_indicator = (flag & 0b0010_0000) == 0b0010_0000
    flag_is_footer_present = (flag & 0b0001_0000) == 0b0001_0000

    size_left = decode_id3v2_4_synchsafe_integer(encoded=bio.read(4), length=4)
    if size_left == 0:
        raise Exception("ID3v2_4: Invalid size")

    # crc_data: Optional[bytes] = None
    if flag_is_extended_header:
        extended_header_size = decode_id3v2_4_synchsafe_integer(
            encoded=bio.read(4), length=4
        )
        int.from_bytes(bio.read(1), byteorder="big")  # number_of_flag_bytes

        extended_flag = int.from_bytes(bio.read(1), byteorder="big")

        extended_flag_tag_is_update = (extended_flag & 0b1000_0000) == 0b1000_0000
        extended_flag_is_crc_data_present = (extended_flag & 0b0100_0000) == 0b0100_0000
        extended_flag_tag_restrictions = (extended_flag & 0b0010_0000) == 0b0010_0000

        if extended_flag_tag_is_update:
            bio.read(1)  # size

        if extended_flag_is_crc_data_present:
            bio.read(1)  # size
            bio.read(5)  # crc_data (5 bytes synchsafe integer)

        if extended_flag_tag_restrictions:
            bio.read(1)  # size
            bio.read(1)  # tag_restrictions

        size_left -= 4 + extended_header_size

    title: Optional[str] = None
    artist: Optional[str] = None
    album: Optional[str] = None
    year: Optional[str] = None
    comment: Optional[str] = None
    attached_picture: Optional[DecodeId3v2_4AttachedPictureFrameResult] = None
    track_number: Optional[int] = None
    total_track_number: Optional[int] = None

    while size_left > 0:
        frame_id = bio.read(4).decode("ascii")
        frame_size = decode_id3v2_4_synchsafe_integer(encoded=bio.read(4), length=4)
        frame_flag1 = int.from_bytes(bio.read(1), byteorder="big")  # frame_flag1
        frame_flag2 = int.from_bytes(bio.read(1), byteorder="big")  # frame_flag2

        if (frame_flag2 & 0b0100_0000) == 0b0100_0000:  # group identity
            bio.read(1)  # group identifier byte

        if (frame_flag2 & 0b0000_1000) == 0b0000_1000:  # compression
            pass  # TODO: not implemented. ignore

        if (frame_flag2 & 0b0000_0100) == 0b0000_0100:  # encryption
            # TODO: not implemented. ignore
            bio.read(1)  # encryption method byte

        if (frame_flag2 & 0b0000_0010) == 0b0000_0010:  # unsynchronisation
            pass

        if (frame_flag2 & 0b0000_0001) == 0b0000_0001:  # data length indicator
            decode_id3v2_4_synchsafe_integer(encoded=bio.read(4), length=4)  # data length indicator (32 bit synchsafe integer)

        frame_data = bio.read(frame_size)

        if frame_id[0] == "T":
            text_information_frame = decode_id3v2_4_text_information_frame_data(
                data=frame_data
            )
            if frame_id == "TIT2":
                title = text_information_frame.information
            elif frame_id == "TPE1":
                artist = text_information_frame.information
            elif frame_id == "TALB":
                album = text_information_frame.information
            elif frame_id == "TYER":
                year = text_information_frame.information
            elif frame_id == "TRCK":
                value = text_information_frame.information.split("/", maxsplit=1)
                track_number = int(value[0])
                if len(value) == 2:
                    total_track_number = int(value[1])
            else:
                # unsupported frame
                pass
        elif frame_id == "COMM":
            comment_frame = decode_id3v2_4_comment_frame_data(data=frame_data)
            comment = comment_frame.actual_comment
        elif frame_id == "APIC":
            attached_picture = decode_id3v2_4_attached_picture_frame_data(
                data=frame_data
            )
        else:
            # unsupported frame
            pass

        size_left -= 10 + frame_size

    # TODO: CRC-32 validation

    return DecodeId3v2_4Result(
        title=title,
        artist=artist,
        album=album,
        year=year,
        comment=comment,
        track_number=track_number,
        total_track_number=total_track_number,
        attached_picture=attached_picture,
        flag_is_unsynchronisation=flag_is_unsynchronisation,
        flag_is_extended_header=flag_is_extended_header,
        flag_is_experimental_indicator=flag_is_experimental_indicator,
        flag_is_footer_present=flag_is_footer_present,
    )
