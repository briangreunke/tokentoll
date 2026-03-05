from __future__ import annotations

import asyncio

import click

from tokentoll.database import SessionLocal
from tokentoll.services.cleanup_service import (
    cleanup_expired_challenges,
    cleanup_stats,
)


async def _run_cleanup(older_than_hours: int) -> int:
    async with SessionLocal() as db:
        return await cleanup_expired_challenges(db, older_than_hours)


async def _run_stats() -> dict[str, int]:
    async with SessionLocal() as db:
        return await cleanup_stats(db)


@click.group()
def cli() -> None:
    """TokenToll maintenance commands."""


@cli.command()
@click.option("--older-than-hours", default=24, show_default=True, type=int)
def cleanup(older_than_hours: int) -> None:
    """Clean up expired challenges and nonces."""
    deleted = asyncio.run(_run_cleanup(older_than_hours))
    click.echo(f"Deleted {deleted} expired challenges")


@cli.command()
def stats() -> None:
    """Show challenge statistics."""
    data = asyncio.run(_run_stats())
    click.echo("Challenge stats:")
    for key in ("total", "expired", "solved", "active"):
        click.echo(f"{key}: {data[key]}")


if __name__ == "__main__":
    cli()
