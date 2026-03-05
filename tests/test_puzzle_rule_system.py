from __future__ import annotations

import random
import re
from typing import TypedDict

from tokentoll.challenges.normalization import normalize_answer
from tokentoll.challenges.puzzles.rule_system import RuleSystemPuzzle


class _Rule(TypedDict):
    var: str
    threshold: int
    updates: list[tuple[str, int]]


def _parse_initial_state(context: str) -> dict[str, int]:
    match = re.search(r"Initial State: red=(\d+), blue=(\d+), green=(\d+)", context)
    if not match:
        raise AssertionError("Missing initial state")
    red, blue, green = match.groups()
    return {"red": int(red), "blue": int(blue), "green": int(green)}


def _parse_steps(context: str) -> int:
    match = re.search(r"Steps: (\d+)", context)
    if not match:
        raise AssertionError("Missing steps")
    return int(match.group(1))


def _parse_rules(context: str) -> list[_Rule]:
    rule_pattern = re.compile(
        r"Rule \d+: if (red|blue|green) >= (\d+) then ([a-z0-9,+=\-; ]+)"
    )
    rules: list[_Rule] = []
    for match in rule_pattern.finditer(context):
        var, threshold, updates_blob = match.groups()
        updates: list[tuple[str, int]] = []
        for part in updates_blob.split(";"):
            part = part.strip()
            if not part:
                continue
            update_match = re.match(r"(red|blue|green) (\+=|-=) (\d+)", part)
            if not update_match:
                raise AssertionError(f"Malformed update: {part}")
            target, op, value = update_match.groups()
            delta = int(value) if op == "+=" else -int(value)
            updates.append((target, delta))
        rules.append({"var": var, "threshold": int(threshold), "updates": updates})
    if not rules:
        raise AssertionError("Missing rules")
    return rules


def _simulate(context: str) -> dict[str, int]:
    state = _parse_initial_state(context)
    rules = _parse_rules(context)
    steps = _parse_steps(context)

    for _ in range(steps):
        applied = False
        for rule in rules:
            var = rule["var"]
            threshold = rule["threshold"]
            if state[var] >= threshold:
                for target, delta in rule["updates"]:
                    state[target] += delta
                applied = True
                break
        if not applied:
            break
    return state


def test_rule_system_deterministic_and_answers() -> None:
    seed = "rule-seed-1"
    rng = random.Random(seed)
    puzzle = RuleSystemPuzzle(seed=seed)
    challenge = puzzle.generate(rng, num_questions=5)

    repeat_challenge = RuleSystemPuzzle(seed=seed).generate(random.Random(seed), num_questions=5)
    assert challenge == repeat_challenge
    assert challenge.seed == seed
    assert challenge.puzzle_type == "rule_system"
    assert len(challenge.questions) == 5

    final_state = _simulate(challenge.context)
    steps = _parse_steps(challenge.context)

    for question in challenge.questions:
        assert "Answer" in question.text
        assert normalize_answer(question.expected_answer, question.answer_format) == question.expected_answer
        if "how many red tokens remain" in question.text:
            assert question.expected_answer == str(final_state["red"])
        elif "how many total tokens" in question.text:
            total = sum(final_state.values())
            assert question.expected_answer == str(total)
        elif "what is the value of green" in question.text:
            assert question.expected_answer == str(final_state["green"])
        elif "is blue greater than green" in question.text:
            expected = "true" if final_state["blue"] > final_state["green"] else "false"
            assert question.expected_answer == expected
        elif "list colors with at least" in question.text:
            threshold = int(question.text.split("at least ", 1)[1].split(" tokens", 1)[0])
            colors = sorted(
                color
                for color, value in final_state.items()
                if value >= threshold
            )
            expected = ", ".join(colors)
            assert question.expected_answer == expected
        elif f"After {steps} steps" in question.text:
            raise AssertionError(f"Unhandled question text: {question.text}")
        else:
            raise AssertionError(f"Unhandled question text: {question.text}")


def test_rule_system_different_seeds_vary() -> None:
    seed_a = "rule-seed-a"
    seed_b = "rule-seed-b"
    challenge_a = RuleSystemPuzzle(seed=seed_a).generate(random.Random(seed_a), num_questions=5)
    challenge_b = RuleSystemPuzzle(seed=seed_b).generate(random.Random(seed_b), num_questions=5)

    assert challenge_a.context != challenge_b.context
