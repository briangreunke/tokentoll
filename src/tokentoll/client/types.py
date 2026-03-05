from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Challenge:
    challenge_id: str
    context: str
    questions: list[dict[str, str]]
    expires_at: str


@dataclass
class VerificationResult:
    success: bool
    token: str | None
    score: float | None
    error: str | None
