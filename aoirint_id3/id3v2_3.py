import csv
import importlib.resources as ILR
import re
from dataclasses import dataclass
from io import BytesIO, StringIO
from typing import List, Literal, Optional

from pydantic import BaseModel, parse_obj_as

from .utils import decode_padded_str, safe_ljust

TextEncodingDescription = Literal["ISO-8859-1", "Unicode"]


class AvailableFrameId(BaseModel):
    frame_id: str
    frame_name: str


def __load_available_frame_ids() -> List[AvailableFrameId]:
    frame_ids_csv_text = ILR.read_text("aoirint_id3", "id3v2_3_available_frame_ids.csv")
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


def decode_id3v2_3_size(data: bytes) -> int:
    raw = int.from_bytes(data, byteorder="big")

    return (
        (raw & 0b00000000_00000000_00000000_01111111)
        | ((raw & 0b00000000_00000000_01111111_00000000) >> 1)
        | ((raw & 0b00000000_01111111_00000000_00000000) >> 2)
        | ((raw & 0b01111111_00000000_00000000_00000000) >> 3)
    )


def encode_id3v2_3_size(value: int) -> bytes:
    return (
        (value & 0b00000000_00000000_00000000_01111111)
        | ((value & 0b00000000_00000000_00111111_10000000) << 1)
        | ((value & 0b00000000_00011111_11000000_00000000) << 2)
        | ((value & 0b00001111_11100000_00000000_00000000) << 3)
    ).to_bytes(length=4, byteorder="big")


def encode_id3v2_3_header(
    size: int,  # tag size excluding padding and header
    flag_is_unsynchronisation: bool = False,
    flag_is_extended_header: bool = False,
    flag_is_experimental_indicator: bool = False,
) -> bytes:
    bio = BytesIO()
    bio.write(b"ID3")  # 3 bytes

    major_version = 3
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

    bio.write(flag.to_bytes(1, byteorder="big"))

    bio.write(encode_id3v2_3_size(value=size))

    return bio.getvalue()


def encode_id3v2_3_extended_header(
    crc_data_present: Optional[bytes],
    size_of_padding: int,
) -> bytes:
    if crc_data_present is not None and len(crc_data_present) != 4:
        raise Exception(
            f"Total frame CRC (CRC-32 data) must be 4 bytes ({len(crc_data_present)} != 4)."
        )

    bio = BytesIO()

    size = 6
    if crc_data_present:
        size += 4

    bio.write(size.to_bytes(4, byteorder="big"))

    flag1 = 0b0000_0000

    if crc_data_present is not None:
        flag1 |= 0b1000_0000

    bio.write(flag1.to_bytes(1, byteorder="big"))

    flag2 = 0b0000_0000

    bio.write(flag2.to_bytes(1, byteorder="big"))

    bio.write(size_of_padding.to_bytes(4, byteorder="big"))

    # Extended header data
    if crc_data_present is not None:
        bio.write(crc_data_present)  # 4 bytes

    return bio.getvalue()


def encode_id3v2_3_frame(
    frame_id: str,
    frame_data: bytes,
    flag_is_tag_alter_preservation: bool = False,
    flag_is_file_alter_preservation: bool = False,
    flag_is_read_only: bool = False,
    flag_is_compression: bool = False,
    flag_is_encryption: bool = False,
    flag_is_grouping_identity: bool = False,
) -> bytes:
    bio = BytesIO()

    frame_id_bytes = frame_id.encode(encoding="ascii")
    if len(frame_id_bytes) != 4:
        raise Exception(f"Invalid Frame ID ({frame_id}). Size {len(frame_id)} != 4")

    bio.write(frame_id_bytes)
    bio.write(len(frame_data).to_bytes(4, byteorder="big"))

    flag1 = 0b0000_0000
    if flag_is_tag_alter_preservation:
        flag1 |= 0b1000_0000

    if flag_is_file_alter_preservation:
        flag1 |= 0b0100_0000

    if flag_is_read_only:
        flag1 |= 0b0010_0000

    bio.write(flag1.to_bytes(1, byteorder="big"))

    flag2 = 0b0000_0000
    if flag_is_compression:
        flag2 |= 0b1000_0000

    if flag_is_encryption:
        flag2 |= 0b0100_0000

    if flag_is_grouping_identity:
        flag2 |= 0b0010_0000

    bio.write(flag2.to_bytes(1, byteorder="big"))

    bio.write(frame_data)

    return bio.getvalue()


def encode_id3v2_3_text_information_frame_data(
    text_encoding: TextEncodingDescription,
    information: str,
) -> bytes:
    bio = BytesIO()

    if text_encoding == "ISO-8859-1":
        text_encoding_python = "latin-1"
        text_encoding_byte = 0
    elif text_encoding == "Unicode":
        text_encoding_python = "utf-16be"  # UTF-16 Big Endian with BOM
        text_encoding_byte = 1
    else:
        raise Exception(
            f"Unsupported text encoding ({text_encoding}). "
            "Use ISO-8859-1 (latin-1) or Unicode (utf-16be)."
        )

    information_bytes = information.encode(encoding=text_encoding_python)

    bio.write(text_encoding_byte.to_bytes(1, byteorder="big"))
    bio.write(information_bytes)

    return bio.getvalue()


@dataclass
class DecodeId3v2_3TextInformationFrameResult:
    information: str


def decode_id3v2_3_text_information_frame_data(
    data: bytes,
) -> DecodeId3v2_3TextInformationFrameResult:
    text_encoding_byte = data[0]

    if text_encoding_byte == 0:
        text_encoding_python = "latin-1"
    elif text_encoding_byte == 1:
        text_encoding_python = "utf-16"  # UTF-16 with BOM
    else:
        raise Exception(
            f"Unsupported text encoding byte ({text_encoding_byte}). "
            "Only 0 (ISO-8859-1, latin-1) or 1 (Unicode, utf-16) is allowed."
        )

    information = data[1:].decode(encoding=text_encoding_python).strip()  # remove BOM

    return DecodeId3v2_3TextInformationFrameResult(
        information=information,
    )


def encode_id3v2_3_comment_frame_data(
    text_encoding: TextEncodingDescription,
    language: str,  # ISO 639-2
    content_description: str,
    actual_comment: str,
) -> bytes:
    bio = BytesIO()

    if text_encoding == "ISO-8859-1":
        text_encoding_python = "latin-1"
        text_encoding_byte = 0
        text_termination_bytes = b"\x00"
    elif text_encoding == "Unicode":
        text_encoding_python = "utf-16be"  # UTF-16 Big Endian with BOM
        text_encoding_byte = 1
        text_termination_bytes = b"\x00\x00"
    else:
        raise Exception(
            f"Unsupported text encoding ({text_encoding}). "
            "Use ISO-8859-1 (latin-1) or Unicode (utf-16be)."
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

    content_description_bytes = content_description.encode(
        encoding=text_encoding_python
    )
    actual_comment_bytes = actual_comment.encode(encoding=text_encoding_python)

    bio.write(text_encoding_byte.to_bytes(1, byteorder="big"))
    bio.write(language_bytes)
    bio.write(content_description_bytes)
    bio.write(text_termination_bytes)  # NULL termination of content description
    bio.write(actual_comment_bytes)

    return bio.getvalue()


@dataclass
class DecodeId3v2_3CommentFrameResult:
    language: str  # ISO 639-2
    content_description: str
    actual_comment: str


def decode_id3v2_3_comment_frame_data(data: bytes) -> DecodeId3v2_3CommentFrameResult:
    text_encoding_byte = data[0]

    if text_encoding_byte == 0:
        text_encoding_python = "latin-1"
        text_termination_bytes = b"\x00"
    elif text_encoding_byte == 1:
        text_encoding_python = "utf-16be"  # UTF-16 Big Endian with BOM
        text_termination_bytes = b"\x00\x00"
    else:
        raise Exception(
            f"Unsupported text encoding byte ({text_encoding_byte}). "
            "Only 0 (ISO-8859-1, latin-1) or 1 (Unicode, utf-16be) is allowed."
        )

    language = decode_padded_str(data[1:4], encoding="ascii")

    content_descirption_bytes, actual_comment_bytes = data[4:].split(
        text_termination_bytes, maxsplit=2
    )
    content_descirption = content_descirption_bytes.decode(
        encoding=text_encoding_python
    )
    actual_comment = actual_comment_bytes.decode(encoding=text_encoding_python)

    return DecodeId3v2_3CommentFrameResult(
        language=language,
        content_description=content_descirption,
        actual_comment=actual_comment,
    )


def encode_id3v2_3(
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
) -> bytes:
    if track_number < 0:
        raise Exception(f"Invalid Track Number: {track_number}")
    if total_track_number is not None and total_track_number < 0:
        raise Exception(f"Invalid Total Track Number: {total_track_number}")

    frames_bio = BytesIO()

    # TT2 frame
    frames_bio.write(
        encode_id3v2_3_frame(
            frame_id="TIT2",
            frame_data=encode_id3v2_3_text_information_frame_data(
                text_encoding=text_encoding,
                information=title,
            ),
        ),
    )
    frames_bio.write(
        encode_id3v2_3_frame(
            frame_id="TPE1",
            frame_data=encode_id3v2_3_text_information_frame_data(
                text_encoding=text_encoding,
                information=artist,
            ),
        ),
    )
    frames_bio.write(
        encode_id3v2_3_frame(
            frame_id="TALB",
            frame_data=encode_id3v2_3_text_information_frame_data(
                text_encoding=text_encoding,
                information=album,
            ),
        ),
    )
    frames_bio.write(
        encode_id3v2_3_frame(
            frame_id="TYER",
            frame_data=encode_id3v2_3_text_information_frame_data(
                text_encoding=text_encoding,
                information=year,
            ),
        ),
    )
    frames_bio.write(
        encode_id3v2_3_frame(
            frame_id="COMM",
            frame_data=encode_id3v2_3_comment_frame_data(
                text_encoding=text_encoding,
                language="eng",  # English
                content_description="Comment",
                actual_comment=comment,
            ),
        ),
    )
    frames_bio.write(
        encode_id3v2_3_frame(
            frame_id="TRCK",
            frame_data=encode_id3v2_3_text_information_frame_data(
                text_encoding=text_encoding,
                information=f"{track_number}/{total_track_number}"
                if total_track_number is not None
                else str(track_number),
            ),
        ),
    )

    frames_bytes = frames_bio.getvalue()

    extended_header_bytes = encode_id3v2_3_extended_header(
        crc_data_present=None,
        size_of_padding=0,
    )

    # header
    size = len(extended_header_bytes) + len(frames_bytes)

    bio = BytesIO()
    bio.write(
        encode_id3v2_3_header(
            size=size,
            flag_is_unsynchronisation=flag_is_unsynchronisation,
            flag_is_extended_header=flag_is_extended_header,
            flag_is_experimental_indicator=flag_is_experimental_indicator,
        )
    )
    bio.write(extended_header_bytes)
    bio.write(frames_bytes)

    return bio.getvalue()


@dataclass
class DecodeId3v2_3Result:
    title: Optional[str]
    artist: Optional[str]
    album: Optional[str]
    year: Optional[str]
    comment: Optional[str]
    track_number: Optional[int]
    total_track_number: Optional[int]
    flag_is_unsynchronisation: bool
    flag_is_extended_header: bool
    flag_is_experimental_indicator: bool


def decode_id3v2_3(data: bytes) -> DecodeId3v2_3Result:
    bio = BytesIO(data)
    identifier = bio.read(3)
    if identifier != b"ID3":
        raise Exception("ID3v2_3: Invalid identifier")

    major_version = int.from_bytes(bio.read(1), byteorder="big")
    revision_number = int.from_bytes(bio.read(1), byteorder="big")
    if major_version != 3 or revision_number != 0:
        raise Exception("ID3v2_3: Invalid version")

    flag = int.from_bytes(bio.read(1), byteorder="big")
    flag_is_unsynchronisation = (flag & 0b1000_0000) == 0b1000_0000
    flag_is_extended_header = (flag & 0b0100_0000) == 0b0100_0000
    flag_is_experimental_indicator = (flag & 0b0010_0000) == 0b0010_0000

    size_left = decode_id3v2_3_size(data=bio.read(4))
    if size_left == 0:
        raise Exception("ID3v2_3: Invalid size")

    # crc_data: Optional[bytes] = None
    if flag_is_extended_header:
        extended_header_size = int.from_bytes(bio.read(4), byteorder="big")
        extended_flag1 = int.from_bytes(bio.read(1), byteorder="big")
        int.from_bytes(bio.read(1), byteorder="big")  # extended_flag2
        int.from_bytes(bio.read(4), byteorder="big")  # size_of_padding
        extended_flag_is_crc_data_present = (
            extended_flag1 & 0b1000_0000
        ) == 0b1000_0000

        size_left -= 4 + extended_header_size

        if extended_flag_is_crc_data_present:
            bio.read(4)  # crc_data

    title: Optional[str] = None
    artist: Optional[str] = None
    album: Optional[str] = None
    year: Optional[str] = None
    comment: Optional[str] = None
    track_number: Optional[int] = None
    total_track_number: Optional[int] = None

    while size_left > 0:
        frame_id = bio.read(4).decode("ascii")
        frame_size = int.from_bytes(bio.read(4), byteorder="big")
        int.from_bytes(bio.read(1), byteorder="big")  # frame_flag1
        int.from_bytes(bio.read(1), byteorder="big")  # frame_flag2
        frame_data = bio.read(frame_size)

        if frame_id[0] == "T":
            text_information_frame = decode_id3v2_3_text_information_frame_data(
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
                value = text_information_frame.information.split("/", maxsplit=2)
                track_number = int(value[0])
                if len(value) == 2:
                    total_track_number = int(value[1])
            else:
                # unsupported frame
                pass
        elif frame_id == "COMM":
            comment_frame = decode_id3v2_3_comment_frame_data(data=frame_data)
            comment = comment_frame.actual_comment
        else:
            # unsupported frame
            pass

        size_left -= 10 + frame_size

    # TODO: CRC-32 validation

    return DecodeId3v2_3Result(
        title=title,
        artist=artist,
        album=album,
        year=year,
        comment=comment,
        track_number=track_number,
        total_track_number=total_track_number,
        flag_is_unsynchronisation=flag_is_unsynchronisation,
        flag_is_extended_header=flag_is_extended_header,
        flag_is_experimental_indicator=flag_is_experimental_indicator,
    )
