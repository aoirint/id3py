# aoirint_id3py

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
