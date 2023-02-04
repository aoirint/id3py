# aoirint_id3py

**This library is under construction and before alpha stage. API will be changed without notice. There are many bugs and unimplemented features.**

Python Library to parse audio ID3 tag specified by [ID3.org](https://id3.org).

## Environment

- Windows 10, Ubuntu 20.04
- Python 3.9, 3.10, 3.11


## Implementation

- ID3v1
- ID3v1.1
- ID3v2.2


## Implemented ID3v2.2 Frames

- TT2: Song title
- TP1: Artist name
- TAL: Album name
- TYE: Year
- TRK: Track number and Total track number
- COM: Comment


## Poetry reference

### Lock Python version with pyenv

```shell
env PYTHON_CONFIGURE_OPTS="--enable-shared" pyenv install 3.9.x
pyenv local 3.9.x

poetry env remove python
poetry env use python
```

### Install dependencies

```shell
poetry install
```

### Add a package
```
poetry add 'mypackage'
poetry add --group test 'mypackage'
poetry add --group build 'mypackage'
```

### Dump requirements.txt

```shell
poetry export --without-hashes -o requirements.txt
poetry export --without-hashes --with test -o requirements-test.txt
poetry export --without-hashes --with build -o requirements-build.txt
```

### Run pytest

```shell
poetry run pytest tests/
```

## Reference

- <https://web.archive.org/web/20210816205319/https://id3.org/id3v2-00>
- <https://ja.wikipedia.org/w/index.php?title=ID3%E3%82%BF%E3%82%B0&oldid=89477951>
- <https://www.loc.gov/standards/iso639-2/php/code_list.php>
