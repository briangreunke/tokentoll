from __future__ import annotations

import random
import re

from tokentoll.challenges.normalization import normalize_answer
from tokentoll.challenges.puzzles.constraint_satisfaction import ConstraintSatisfactionPuzzle


def _parse_assignments(context: str) -> dict[str, dict[str, str]]:
    pattern = re.compile(r"Assignment: (\w+) -> (\w+) at Slot (\d+)")
    assignments: dict[str, dict[str, str]] = {}
    for match in pattern.finditer(context):
        task, room, slot = match.groups()
        assignments[task] = {"room": room, "slot": slot}
    return assignments


def test_constraint_satisfaction_deterministic_and_answers() -> None:
    seed = "constraint-seed-1"
    rng = random.Random(seed)
    puzzle = ConstraintSatisfactionPuzzle(seed=seed)
    challenge = puzzle.generate(rng, num_questions=6)

    repeat_rng = random.Random(seed)
    repeat_challenge = ConstraintSatisfactionPuzzle(seed=seed).generate(repeat_rng, num_questions=6)

    assert challenge == repeat_challenge
    assert challenge.seed == seed
    assert challenge.puzzle_type == "constraint_satisfaction"
    assert len(challenge.questions) == 6

    assignments = _parse_assignments(challenge.context)
    assert assignments

    for question in challenge.questions:
        assert "Answer" in question.text
        assert normalize_answer(question.expected_answer, question.answer_format) == question.expected_answer
        if "Which room is" in question.text:
            task = question.text.split("Which room is ", 1)[1].split(" in", 1)[0]
            expected = assignments[task]["room"].lower()
            assert question.expected_answer == expected
        elif "At which slot is" in question.text:
            task = question.text.split("At which slot is ", 1)[1].split(" scheduled", 1)[0]
            expected = assignments[task]["slot"]
            assert question.expected_answer == expected
        elif "Which task is in" in question.text:
            tail = question.text.split("Which task is in ", 1)[1]
            room = tail.split(" at Slot ", 1)[0]
            slot = tail.split(" at Slot ", 1)[1].split("?", 1)[0]
            match = [
                task
                for task, details in assignments.items()
                if details["room"].lower() == room.lower() and details["slot"] == slot
            ]
            assert len(match) == 1
            assert question.expected_answer == match[0].lower()
        elif "List the tasks in" in question.text:
            room = question.text.split("List the tasks in ", 1)[1].split(" (", 1)[0]
            tasks = sorted(
                task.lower()
                for task, details in assignments.items()
                if details["room"].lower() == room.lower()
            )
            expected = ", ".join(tasks)
            assert question.expected_answer == expected
        elif "Is any task in" in question.text:
            tail = question.text.split("Is any task in ", 1)[1]
            room = tail.split(" at Slot ", 1)[0]
            slot = tail.split(" at Slot ", 1)[1].split("?", 1)[0]
            has_task = any(
                details["room"].lower() == room.lower() and details["slot"] == slot
                for details in assignments.values()
            )
            expected = "true" if has_task else "false"
            assert question.expected_answer == expected
        else:
            raise AssertionError(f"Unhandled question text: {question.text}")


def test_constraint_satisfaction_different_seeds_vary() -> None:
    seed_a = "constraint-seed-a"
    seed_b = "constraint-seed-b"
    challenge_a = ConstraintSatisfactionPuzzle(seed=seed_a).generate(
        random.Random(seed_a),
        num_questions=5,
    )
    challenge_b = ConstraintSatisfactionPuzzle(seed=seed_b).generate(
        random.Random(seed_b),
        num_questions=5,
    )

    assert challenge_a.context != challenge_b.context
