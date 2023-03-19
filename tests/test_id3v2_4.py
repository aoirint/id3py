from typing import Optional

from aoirint_id3 import DecodeId3v2_4Result, decode_id3v2_4, encode_id3v2_4
from aoirint_id3.id3v2_4 import (
    TextEncodingDescription,
    decode_id3v2_4_synchsafe_integer,
    encode_id3v2_4_synchsafe_integer,
)


def test_id3v2_4_size() -> None:
    def encode_decode_id3v2_4_synchsafe_integer(value: int, length: int) -> int:
        return decode_id3v2_4_synchsafe_integer(
            encoded=encode_id3v2_4_synchsafe_integer(value=value, length=length),
            length=length,
        )

    assert encode_decode_id3v2_4_synchsafe_integer(value=1024, length=4) == 1024
    assert encode_decode_id3v2_4_synchsafe_integer(
        value=2 ** (28 - 1), length=4
    ) == 2 ** (
        28 - 1
    )  # max 28 bit int
    assert encode_decode_id3v2_4_synchsafe_integer(
        value=2 ** (29 - 1), length=4
    ) != 2 ** (29 - 1)
    assert (
        encode_decode_id3v2_4_synchsafe_integer(
            value=0b00001111_11111111_11111111_11111111, length=4
        )
        == 0b00001111_11111111_11111111_11111111
    )
    assert (
        encode_decode_id3v2_4_synchsafe_integer(
            value=0b00011111_11111111_11111111_11111111, length=4
        )
        != 0b00011111_11111111_11111111_11111111
    )


def test_id3v2_4() -> None:
    def encode_decode_id3v2_4(
        title: str,
        artist: str,
        album: str,
        year: str,
        comment: str,
        track_number: int,
        total_track_number: Optional[int],
        text_encoding: TextEncodingDescription,
    ) -> DecodeId3v2_4Result:
        return decode_id3v2_4(
            data=encode_id3v2_4(
                title=title,
                artist=artist,
                album=album,
                year=year,
                comment=comment,
                track_number=track_number,
                total_track_number=total_track_number,
                text_encoding=text_encoding,
            ),
        )

    def assert_encode_decode_id3v2_4(
        title: str,
        artist: str,
        album: str,
        year: str,
        comment: str,
        track_number: int,
        total_track_number: Optional[int],
        text_encoding: TextEncodingDescription,
    ) -> None:
        tag = encode_decode_id3v2_4(
            title=title,
            artist=artist,
            album=album,
            year=year,
            comment=comment,
            track_number=track_number,
            total_track_number=total_track_number,
            text_encoding=text_encoding,
        )
        assert tag.title == title
        assert tag.artist == artist
        assert tag.album == album
        assert tag.year == year
        assert tag.comment == comment
        assert tag.track_number == track_number

    assert_encode_decode_id3v2_4(
        title="Title",
        artist="Artist Name",
        album="Album Name",
        year="2023",
        comment="Comment",
        track_number=1,
        total_track_number=10,
        text_encoding="ISO-8859-1",
    )

    assert_encode_decode_id3v2_4(
        title="Title",
        artist="Artist Name",
        album="Album Name",
        year="2023",
        comment="Comment",
        track_number=1,
        total_track_number=10,
        text_encoding="UTF-16",
    )

    assert_encode_decode_id3v2_4(
        title="Title",
        artist="Artist Name",
        album="Album Name",
        year="2023",
        comment="Comment",
        track_number=1,
        total_track_number=10,
        text_encoding="UTF-16BE",
    )

    assert_encode_decode_id3v2_4(
        title="Title",
        artist="Artist Name",
        album="Album Name",
        year="2023",
        comment="Comment",
        track_number=1,
        total_track_number=10,
        text_encoding="UTF-8",
    )
