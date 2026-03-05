from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Question:
    id: str
    text: str
    expected_answer: str
    answer_format: str


@dataclass(frozen=True)
class GeneratedChallenge:
    seed: str
    puzzle_type: str
    context: str
    questions: list[Question]
    estimated_tokens: int
