from __future__ import annotations

import random
from typing import cast

from tokentoll.challenges.normalization import normalize_answer
from tokentoll.challenges.puzzles.base import estimate_tokens, pad_context
from tokentoll.challenges.puzzles.base import PuzzleGenerator
from tokentoll.challenges.types import GeneratedChallenge, Question


class RuleSystemPuzzle(PuzzleGenerator):
    @property
    def puzzle_type(self) -> str:
        return "rule_system"

    def generate(self, rng: random.Random, num_questions: int) -> GeneratedChallenge:
        if not 5 <= num_questions <= 10:
            raise ValueError("num_questions must be between 5 and 10")

        state = {
            "red": rng.randint(4, 7),
            "blue": rng.randint(1, 4),
            "green": rng.randint(0, 3),
        }

        rules = [
            ("red", 2, [("red", -2), ("blue", 1)]),
            ("blue", 3, [("blue", -3), ("green", 1)]),
            ("green", 2, [("green", -2), ("red", 1)]),
        ]

        steps = rng.randint(5, 7)
        final_state = self._simulate(state, rules, steps)

        lines = [
            "You maintain counts of red, blue, and green tokens.",
            (
                "Initial State: red={red}, blue={blue}, green={green}".format(
                    **state
                )
            ),
            "Rules (apply in order each step; if a rule applies, stop for that step):",
            "Rule 1: if red >= 2 then red -= 2; blue += 1",
            "Rule 2: if blue >= 3 then blue -= 3; green += 1",
            "Rule 3: if green >= 2 then green -= 2; red += 1",
            f"Steps: {steps}",
        ]

        context = "\n".join(lines)

        question_pool: list[tuple[str, object]] = [
            ("count", "red"),
            ("count", "blue"),
            ("count", "green"),
            ("total", None),
            ("compare", ("red", "blue")),
            ("compare", ("red", "green")),
            ("compare", ("blue", "green")),
            ("threshold", 1),
            ("threshold", 2),
            ("threshold", 3),
            ("min", None),
            ("max", None),
        ]
        chosen = rng.sample(question_pool, k=num_questions)

        questions: list[Question] = []
        for index, (kind, value) in enumerate(chosen, start=1):
            if kind == "count":
                color = cast(str, value)
                answer = str(final_state[color])
                text = (
                    f"After {steps} steps, how many {color} tokens remain? "
                    "Answer with an integer."
                )
                answer_format = "integer"
            elif kind == "total":
                answer = str(sum(final_state.values()))
                text = (
                    f"After {steps} steps, how many total tokens are there? "
                    "Answer with an integer."
                )
                answer_format = "integer"
            elif kind == "compare":
                left, right = cast(tuple[str, str], value)
                answer = "true" if final_state[left] > final_state[right] else "false"
                text = (
                    f"After {steps} steps, is {left} greater than {right}? "
                    "Answer with true/false."
                )
                answer_format = "boolean"
            elif kind == "min":
                min_value = min(final_state.values())
                eligible = sorted(
                    color for color, count in final_state.items() if count == min_value
                )
                answer = ", ".join(eligible)
                text = (
                    f"After {steps} steps, which colors have the minimum count? "
                    "Answer with a comma-separated list, alphabetically sorted."
                )
                answer_format = "comma_separated_list"
            elif kind == "max":
                max_value = max(final_state.values())
                eligible = sorted(
                    color for color, count in final_state.items() if count == max_value
                )
                answer = ", ".join(eligible)
                text = (
                    f"After {steps} steps, which colors have the maximum count? "
                    "Answer with a comma-separated list, alphabetically sorted."
                )
                answer_format = "comma_separated_list"
            else:
                threshold_value = cast(int, value)
                eligible = sorted(
                    color for color, count in final_state.items() if count >= threshold_value
                )
                answer = ", ".join(eligible)
                text = (
                    f"After {steps} steps, list colors with at least {threshold_value} "
                    "tokens. Answer with a comma-separated list, alphabetically sorted."
                )
                answer_format = "comma_separated_list"

            normalized = normalize_answer(answer, answer_format)
            questions.append(
                Question(
                    id=f"q{index}",
                    text=text,
                    expected_answer=normalized,
                    answer_format=answer_format,
                )
            )

        context = pad_context(context, target_tokens=3600, rng=rng)
        estimated_tokens = estimate_tokens(context)

        return GeneratedChallenge(
            seed=self.seed,
            puzzle_type=self.puzzle_type,
            context=context,
            questions=questions,
            estimated_tokens=estimated_tokens,
        )

    def _simulate(
        self,
        state: dict[str, int],
        rules: list[tuple[str, int, list[tuple[str, int]]]],
        steps: int,
    ) -> dict[str, int]:
        current = state.copy()
        for _ in range(steps):
            applied = False
            for var, threshold, updates in rules:
                if current[var] >= threshold:
                    for target, delta in updates:
                        current[target] += delta
                    applied = True
                    break
            if not applied:
                break
        return current
