from __future__ import annotations

import random
import secrets

from tokentoll.challenges.puzzles import AVAILABLE_PUZZLES
from tokentoll.challenges.types import GeneratedChallenge


def generate_challenge(
    seed: str | None = None,
    num_questions: int = 7,
    puzzle_type: str | None = None,
) -> GeneratedChallenge:
    if seed is None:
        seed = secrets.token_hex(16)

    rng = random.Random(seed)
    if puzzle_type is None:
        puzzle_type = rng.choice(list(AVAILABLE_PUZZLES))

    if puzzle_type not in AVAILABLE_PUZZLES:
        raise ValueError(f"Unknown puzzle type: {puzzle_type}")

    puzzle_class = AVAILABLE_PUZZLES[puzzle_type]
    puzzle = puzzle_class(seed=seed)
    return puzzle.generate(rng, num_questions=num_questions)
