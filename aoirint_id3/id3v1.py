from dataclasses import dataclass
from io import BytesIO

from .utils import decode_padded_str, safe_ljust


def encode_id3v1(
    title: str,
    artist: str,
    album: str,
    year: str,
    comment: str,
    genre_number: int,
    encoding: str,
) -> bytes:
    if genre_number < 0 or genre_number > 255:
        raise Exception(f"Invalid Genre Number: {genre_number}")

    bio = BytesIO()
    bio.write(b"TAG")  # 3 bytes
    bio.write(safe_ljust(title.encode(encoding=encoding), 30))
    bio.write(safe_ljust(artist.encode(encoding=encoding), 30))
    bio.write(safe_ljust(album.encode(encoding=encoding), 30))
    bio.write(safe_ljust(year.encode(encoding=encoding), 4))
    bio.write(safe_ljust(comment.encode(encoding=encoding), 30))
    bio.write(genre_number.to_bytes(1, byteorder="big"))  # 1 byte

    ret = bio.getvalue()
    assert len(ret) == 128  # 128 bytes

    return ret


@dataclass
class DecodeId3v1Result:
    title: str
    artist: str
    album: str
    year: str
    comment: str
    genre_number: int


def decode_id3v1(data: bytes, encoding: str) -> DecodeId3v1Result:
    if len(data) < 128:
        raise Exception(f"ID3v1: Invalid data length ({len(data)} < 128).")

    data = data[-128:]

    bio = BytesIO(data)
    identifier = bio.read(3)
    if identifier != b"TAG":
        raise Exception("ID3v1: Invalid identifier")

    title = decode_padded_str(bio.read(30), encoding=encoding)
    artist = decode_padded_str(bio.read(30), encoding=encoding)
    album = decode_padded_str(bio.read(30), encoding=encoding)
    year = decode_padded_str(bio.read(4), encoding=encoding)
    comment = decode_padded_str(bio.read(30), encoding=encoding)
    genre_number = int.from_bytes(bio.read(1), byteorder="big")

    return DecodeId3v1Result(
        title=title,
        artist=artist,
        album=album,
        year=year,
        comment=comment,
        genre_number=genre_number,
    )
