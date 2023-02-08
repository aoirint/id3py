def safe_ljust(data: bytes, length: int) -> bytes:
    ret = data.ljust(length, b"\x00")
    if len(ret) > length:
        raise Exception("Overflow")
    return ret


def decode_padded_str(data: bytes, encoding: str) -> str:
    unpadded_data = data.split(b"\x00", maxsplit=1)
    return unpadded_data[0].decode(encoding=encoding)
