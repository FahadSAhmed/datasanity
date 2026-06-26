.PHONY: install test build clean

install:
	python -m pip install -e ".[dev]"

test:
	pytest

build:
	python -m pip install --upgrade build
	python -m build

clean:
	rm -rf build dist *.egg-info src/*.egg-info .pytest_cache
