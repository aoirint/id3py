from . import id3v1, id3v1_1, id3v2_2, utils
from .id3v1 import DecodeId3v1Result, decode_id3v1, encode_id3v1
from .id3v1_1 import DecodeId3v1_1Result, decode_id3v1_1, encode_id3v1_1

__all__ = [
    "id3v1",
    "id3v1_1",
    "id3v2_2",
    "utils",
    "encode_id3v1",
    "decode_id3v1",
    "DecodeId3v1Result",
    "encode_id3v1_1",
    "decode_id3v1_1",
    "DecodeId3v1_1Result",
]
