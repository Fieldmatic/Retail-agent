.PHONY: setup start check format

setup:
	uv sync
	test -f .env || cp .env.example .env

start:
	uv run python -m app.cli

check:
	uv run ruff check .

format:
	uv run ruff check . --fix
	uv run ruff format .
