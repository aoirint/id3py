# License: CC0-1.0

from pathlib import Path
from typing import Optional

from aoirint_id3 import (
    decode_id3v1,
    decode_id3v1_1,
    decode_id3v2_2,
    decode_id3v2_3,
    decode_id3v2_4,
    detect_id3_versions,
)


def main():
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("input_file", type=Path)
    parser.add_argument("--artwork_output_file", type=Path)
    args = parser.parse_args()

    input_file: Path = args.input_file
    artwork_output_file: Optional[Path] = args.artwork_output_file
    audio_bytes = input_file.read_bytes()

    id3_versions = detect_id3_versions(audio_bytes)
    print(f"ID3 versions: {id3_versions}")

    if "ID3v2.4" in id3_versions:
        print(f"Decoded as ID3v2.4")
        tag = decode_id3v2_4(audio_bytes)
    elif "ID3v2.3" in id3_versions:
        print(f"Decoded as ID3v2.3")
        tag = decode_id3v2_3(audio_bytes)
    elif "ID3v2.2" in id3_versions:
        print(f"Decoded as ID3v2.2")
        tag = decode_id3v2_2(audio_bytes)
    elif "ID3v1.1" in id3_versions:
        print(f"Decoded as ID3v1.1")
        tag = decode_id3v1_1(audio_bytes, encoding="latin1")
    elif "ID3v1" in id3_versions:
        print(f"Decoded as ID3v1")
        tag = decode_id3v1(audio_bytes, encoding="latin1")
    else:
        raise Exception("Unsupported audio bytes")

    print(f"{tag.title} - {tag.artist}")
    if artwork_output_file is not None and hasattr(tag, "attached_picture") and tag.attached_picture is not None:
        print(f"Saving artwork ({tag.attached_picture.mime_type}) to {artwork_output_file}")
        artwork_output_file.write_bytes(tag.attached_picture.picture_data)


if __name__ == "__main__":
    main()
