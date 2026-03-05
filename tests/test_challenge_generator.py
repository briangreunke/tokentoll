from __future__ import annotations

import random
import string

from tokentoll.challenges.generator import generate_challenge
from tokentoll.challenges.puzzles import AVAILABLE_PUZZLES


def test_generate_challenge_deterministic_for_seed() -> None:
    challenge = generate_challenge(seed="deterministic-seed", num_questions=5, puzzle_type="logic_grid")
    repeat = generate_challenge(seed="deterministic-seed", num_questions=5, puzzle_type="logic_grid")

    assert challenge == repeat


def test_generate_challenge_random_seed() -> None:
    challenge = generate_challenge(seed=None, num_questions=5, puzzle_type="logic_grid")

    assert challenge.seed
    assert len(challenge.seed) == 32
    assert all(char in string.hexdigits for char in challenge.seed)


def test_generate_challenge_random_type_selection() -> None:
    seed = "type-seed"
    rng = random.Random(seed)
    expected_type = rng.choice(list(AVAILABLE_PUZZLES))

    challenge = generate_challenge(seed=seed, num_questions=5, puzzle_type=None)

    assert challenge.puzzle_type == expected_type


def test_generate_challenge_question_count_and_tokens() -> None:
    challenge = generate_challenge(seed="token-seed", num_questions=7, puzzle_type="rule_system")

    assert len(challenge.questions) == 7
    word_count = len(challenge.context.split())
    assert challenge.estimated_tokens == int(word_count * 1.3)
    assert 3000 <= challenge.estimated_tokens <= 5000
    assert all("Answer" in question.text for question in challenge.questions)
