from . import detect, id3v1, id3v1_1, id3v2_2, utils
from .detect import DetectedId3Version, detect_id3_versions
from .id3v1 import DecodeId3v1Result, decode_id3v1, encode_id3v1
from .id3v1_1 import DecodeId3v1_1Result, decode_id3v1_1, encode_id3v1_1
from .id3v2_2 import DecodeId3v2_2Result, decode_id3v2_2, encode_id3v2_2

__all__ = [
    "id3v1",
    "id3v1_1",
    "id3v2_2",
    "detect",
    "utils",
    "encode_id3v1",
    "decode_id3v1",
    "DecodeId3v1Result",
    "encode_id3v1_1",
    "decode_id3v1_1",
    "DecodeId3v1_1Result",
    "encode_id3v2_2",
    "decode_id3v2_2",
    "DecodeId3v2_2Result",
    "DetectedId3Version",
    "detect_id3_versions",
]
