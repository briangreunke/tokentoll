from __future__ import annotations

import random

from tokentoll.challenges.normalization import normalize_answer
from tokentoll.challenges.puzzles.base import estimate_tokens, pad_context
from tokentoll.challenges.puzzles.base import PuzzleGenerator
from tokentoll.challenges.types import GeneratedChallenge, Question


class LogicGridPuzzle(PuzzleGenerator):
    @property
    def puzzle_type(self) -> str:
        return "logic_grid"

    def generate(self, rng: random.Random, num_questions: int) -> GeneratedChallenge:
        if not 5 <= num_questions <= 10:
            raise ValueError("num_questions must be between 5 and 10")

        people = ["Alice", "Bruno", "Carmen", "Diego", "Elena"]
        languages = ["Python", "Ruby", "Go", "Java", "Rust"]
        cities = ["Oslo", "Lima", "Delhi", "Reno", "Kyoto"]

        rng.shuffle(people)
        rng.shuffle(languages)
        rng.shuffle(cities)

        assignments = {
            person: {"language": languages[index], "city": cities[index]}
            for index, person in enumerate(people)
        }

        lines: list[str] = [
            "Five analysts each use a different language and work in a different city.",
            "Use the clues to match each person with their language and city.",
            "Clues:",
        ]
        for person, details in assignments.items():
            lines.append(f"Clue: {person} works in {details['city']}.")
            lines.append(f"Clue: The {details['language']} developer is {person}.")

        lines.append("Assignments:")
        for person, details in assignments.items():
            lines.append(
                f"Assignment: {person} -> {details['language']}, {details['city']}"
            )

        context = "\n".join(lines)

        question_pool: list[tuple[str, str]] = []
        for person in people:
            question_pool.append(("language", person))
            question_pool.append(("city", person))
        for city in cities:
            question_pool.append(("person_by_city", city))

        chosen = rng.sample(question_pool, k=num_questions)
        questions: list[Question] = []
        for index, (kind, value) in enumerate(chosen, start=1):
            if kind == "language":
                answer = assignments[value]["language"]
                text = f"Which language does {value} use? Answer with a single word."
                answer_format = "single_word"
            elif kind == "city":
                answer = assignments[value]["city"]
                text = f"Which city does {value} work in? Answer with a single word."
                answer_format = "single_word"
            else:
                person = next(
                    person
                    for person, details in assignments.items()
                    if details["city"] == value
                )
                answer = person
                text = f"Who works in {value}? Answer with a single word."
                answer_format = "single_word"

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
