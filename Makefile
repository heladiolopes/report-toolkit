.PHONY: test build

test:
	PYTHONPATH=src python -m unittest discover -s tests -v

build:
	python -m build
