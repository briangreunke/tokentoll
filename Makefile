.PHONY: dev test lint migrate

dev:
	uv run uvicorn tokentoll.main:app --reload

test:
	uv run pytest

lint:
	uv run ruff check .

migrate:
	uv run alembic upgrade head
