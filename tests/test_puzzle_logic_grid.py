from __future__ import annotations

import random
import re

from tokentoll.challenges.normalization import normalize_answer
from tokentoll.challenges.puzzles.logic_grid import LogicGridPuzzle


def _parse_assignments(context: str) -> dict[str, dict[str, str]]:
    pattern = re.compile(r"Assignment: (\w+) -> (\w+), (\w+)")
    assignments: dict[str, dict[str, str]] = {}
    for match in pattern.finditer(context):
        person, language, city = match.groups()
        assignments[person] = {"language": language, "city": city}
    return assignments


def test_logic_grid_deterministic_and_answers() -> None:
    seed = "logic-seed-1"
    rng = random.Random(seed)
    puzzle = LogicGridPuzzle(seed=seed)
    challenge = puzzle.generate(rng, num_questions=7)

    repeat_rng = random.Random(seed)
    repeat_puzzle = LogicGridPuzzle(seed=seed)
    repeat_challenge = repeat_puzzle.generate(repeat_rng, num_questions=7)

    assert challenge == repeat_challenge
    assert challenge.seed == seed
    assert challenge.puzzle_type == "logic_grid"
    assert len(challenge.questions) == 7
    assert [q.id for q in challenge.questions] == [f"q{index}" for index in range(1, 8)]

    assignments = _parse_assignments(challenge.context)
    assert assignments

    for question in challenge.questions:
        assert "Answer" in question.text
        assert normalize_answer(question.expected_answer, question.answer_format) == question.expected_answer
        if "Which language does" in question.text:
            person = question.text.split("Which language does ", 1)[1].split(" use", 1)[0]
            expected = assignments[person]["language"].lower()
            assert question.expected_answer == expected
        elif "Who works in" in question.text:
            city = question.text.split("Who works in ", 1)[1].split("?", 1)[0]
            match = [
                person
                for person, details in assignments.items()
                if details["city"].lower() == city.lower()
            ]
            assert len(match) == 1
            assert question.expected_answer == match[0].lower()
        elif "Which city does" in question.text:
            person = question.text.split("Which city does ", 1)[1].split(" work", 1)[0]
            expected = assignments[person]["city"].lower()
            assert question.expected_answer == expected
        else:
            raise AssertionError(f"Unhandled question text: {question.text}")


def test_logic_grid_different_seeds_vary() -> None:
    seed_a = "logic-seed-a"
    seed_b = "logic-seed-b"
    challenge_a = LogicGridPuzzle(seed=seed_a).generate(random.Random(seed_a), num_questions=5)
    challenge_b = LogicGridPuzzle(seed=seed_b).generate(random.Random(seed_b), num_questions=5)

    assert challenge_a.context != challenge_b.context
