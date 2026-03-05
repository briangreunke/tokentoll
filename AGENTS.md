# TokenToll Agent Guide

## Project Structure
- `src/tokentoll/` — Application package
- `tests/` — Pytest suite
- `alembic/` — Database migrations
- `pyproject.toml` — Dependencies and tooling

## Common Commands
- Run tests: `uv run pytest`
- Run server: `uv run uvicorn tokentoll.main:app`
- Lint: `uv run ruff check .`
- Migrations: `uv run alembic upgrade head`

## Naming Conventions
- Use `snake_case` for variables and functions
- Use `PascalCase` for classes
- Provide type hints for all public functions

## Error Handling
- Raise `HTTPException` with a structured detail dict
  ```python
  raise HTTPException(status_code=400, detail={"error": "invalid_input"})
  ```

## Import Conventions
- Standard library imports first
- Third-party imports second
- Local application imports last
