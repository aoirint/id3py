from typing import Literal, get_args

Id3Version = Literal[
    "ID3v1",
    "ID3v1.1",
    "ID3v2.2",
    "ID3v2.3",
    "ID3v2.4",
]

available_id3_versions: tuple[Id3Version, ...] = get_args(Id3Version)


def detect_id3_version(data: bytes) -> Id3Version:
    if len(data) < 128:
        raise Exception("Data is too short. No ID3 tag detected.")

    id3v1_footer = data[-128:]
    if id3v1_footer[:3] == b"TAG":
        if id3v1_footer[125:126] == b"\x00" and id3v1_footer[126:127] != b"\x00":
            return "ID3v1.1"
        return "ID3v1"

    id3v2_identifier = data[:3]
    if id3v2_identifier == b"ID3":
        id3v2_major_version = int.from_bytes(data[3:4], byteorder="big")
        if id3v2_major_version == 2:
            return "ID3v2.2"
        elif id3v2_major_version == 3:
            return "ID3v2.4"
        elif id3v2_major_version == 4:
            return "ID3v2.4"

    raise Exception("No ID3 tag detected.")
