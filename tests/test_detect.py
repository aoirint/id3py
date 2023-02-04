from aoirint_id3 import (
    detect_id3_versions,
    encode_id3v1,
    encode_id3v1_1,
    encode_id3v2_2,
)


def test_detect_id3_version_id3v1() -> None:
    assert "ID3v1" in detect_id3_versions(
        data=encode_id3v1(
            title="Title",
            artist="Artist Name",
            album="Album Name",
            year="2023",
            comment="Comment",
            genre_number=12,  # Others
            encoding="ascii",
        )
    )


def test_detect_id3_version_id3v1_1() -> None:
    assert "ID3v1.1" in detect_id3_versions(
        data=encode_id3v1_1(
            title="Title",
            artist="Artist Name",
            album="Album Name",
            year="2023",
            comment="Comment",
            track_number=1,
            genre_number=12,  # Others
            encoding="ascii",
        )
    )


def test_detect_id3_version_id3v2_2() -> None:
    assert "ID3v2.2" in detect_id3_versions(
        data=encode_id3v2_2(
            title="Title",
            artist="Artist Name",
            album="Album Name",
            year="2023",
            comment="Comment",
            track_number=1,
            total_track_number=10,
            text_encoding="Unicode",
        )
    )
