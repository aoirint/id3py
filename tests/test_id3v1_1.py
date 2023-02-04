from aoirint_id3 import DecodeId3v1_1Result, decode_id3v1_1, encode_id3v1_1


def encode_decode_id3v1_1(
    title: str,
    artist: str,
    album: str,
    year: str,
    comment: str,
    track_number: int,
    genre_number: int,
    encoding: str,
) -> DecodeId3v1_1Result:
    return decode_id3v1_1(
        data=encode_id3v1_1(
            title=title,
            artist=artist,
            album=album,
            year=year,
            comment=comment,
            track_number=track_number,
            genre_number=genre_number,
            encoding=encoding,
        ),
        encoding=encoding,
    )


def assert_encode_decode_id3v1_1(
    title: str,
    artist: str,
    album: str,
    year: str,
    comment: str,
    track_number: int,
    genre_number: int,
    encoding: str,
) -> None:
    tag = encode_decode_id3v1_1(
        title=title,
        artist=artist,
        album=album,
        year=year,
        comment=comment,
        track_number=track_number,
        genre_number=genre_number,
        encoding=encoding,
    )
    assert tag.title == title
    assert tag.artist == artist
    assert tag.album == album
    assert tag.year == year
    assert tag.comment == comment
    assert tag.track_number == track_number
    assert tag.genre_number == genre_number


def test_id3v1_1() -> None:
    assert_encode_decode_id3v1_1(
        title="Title",
        artist="Artist Name",
        album="Album Name",
        year="2023",
        comment="Comment",
        track_number=1,
        genre_number=12,  # Others
        encoding="ascii",
    )
