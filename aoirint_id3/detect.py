from typing import List, Literal, get_args

DetectedId3Version = Literal[
    "ID3v1",
    "ID3v1.1",
    "ID3v2.2",
    "ID3v2.3",
    "ID3v2.4",
]

available_id3_versions: tuple[DetectedId3Version, ...] = get_args(DetectedId3Version)


def detect_id3_versions(data: bytes) -> List[DetectedId3Version]:
    if len(data) < 128:
        return []

    detected_versions: List[DetectedId3Version] = []

    id3v1_footer = data[-128:]
    if id3v1_footer[:3] == b"TAG":
        if id3v1_footer[125:126] == b"\x00" and id3v1_footer[126:127] != b"\x00":
            detected_versions.append("ID3v1.1")
        else:
            detected_versions.append("ID3v1")

    id3v2_identifier = data[:3]
    if id3v2_identifier == b"ID3":
        id3v2_major_version = int.from_bytes(data[3:4], byteorder="big")
        if id3v2_major_version == 2:
            detected_versions.append("ID3v2.2")
        elif id3v2_major_version == 3:
            detected_versions.append("ID3v2.3")
        elif id3v2_major_version == 4:
            detected_versions.append("ID3v2.4")

    return detected_versions
