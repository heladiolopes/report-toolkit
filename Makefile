.PHONY: lint format test build

lint:
	uv run ruff check src/

format:
	uv run ruff format src/

test:
	uv run pytest

build:
	uv build

