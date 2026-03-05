from __future__ import annotations

import random
from typing import cast

from tokentoll.challenges.normalization import normalize_answer
from tokentoll.challenges.puzzles.base import estimate_tokens, pad_context
from tokentoll.challenges.puzzles.base import PuzzleGenerator
from tokentoll.challenges.types import GeneratedChallenge, Question


class ConstraintSatisfactionPuzzle(PuzzleGenerator):
    @property
    def puzzle_type(self) -> str:
        return "constraint_satisfaction"

    def generate(self, rng: random.Random, num_questions: int) -> GeneratedChallenge:
        if not 5 <= num_questions <= 10:
            raise ValueError("num_questions must be between 5 and 10")

        tasks = ["TaskA", "TaskB", "TaskC", "TaskD", "TaskE", "TaskF"]
        rooms = ["Orion", "Pegasus", "Lyra"]
        slots = ["1", "2", "3"]

        rng.shuffle(tasks)
        rng.shuffle(rooms)
        rng.shuffle(slots)

        pairs = [(room, slot) for room in rooms for slot in slots]
        rng.shuffle(pairs)

        assignments: dict[str, dict[str, str]] = {}
        assigned_pairs = pairs[: len(tasks)]
        for task, (room, slot) in zip(tasks, assigned_pairs, strict=True):
            assignments[task] = {"room": room, "slot": slot}

        lines: list[str] = [
            "Six tasks must be scheduled into rooms and time slots.",
            "Each task occupies exactly one room and one slot.",
            "Constraints:",
        ]
        for task, details in assignments.items():
            lines.append(f"Constraint: {task} is in Room {details['room']}.")
            lines.append(f"Constraint: {task} is scheduled at Slot {details['slot']}.")

        lines.append("Assignments:")
        for task, details in assignments.items():
            lines.append(
                f"Assignment: {task} -> {details['room']} at Slot {details['slot']}"
            )

        context = "\n".join(lines)

        question_pool: list[tuple[str, object]] = []
        for task in tasks:
            question_pool.append(("room", task))
            question_pool.append(("slot", task))
        for room, slot in assigned_pairs[:3]:
            question_pool.append(("task_at", (room, slot)))
        for room in rooms:
            question_pool.append(("tasks_in_room", room))

        unassigned = pairs[len(tasks) :]
        if unassigned:
            room, slot = unassigned[0]
        else:
            room, slot = pairs[-1]
        question_pool.append(("exists", (room, slot)))

        chosen = rng.sample(question_pool, k=num_questions)
        questions: list[Question] = []
        for index, (kind, value) in enumerate(chosen, start=1):
            if kind == "room":
                task = str(value)
                answer = assignments[task]["room"]
                text = f"Which room is {task} in? Answer with a single word."
                answer_format = "single_word"
            elif kind == "slot":
                task = str(value)
                answer = assignments[task]["slot"]
                text = f"At which slot is {task} scheduled? Answer with an integer."
                answer_format = "integer"
            elif kind == "task_at":
                room_value, slot_value = cast(tuple[str, str], value)
                task = next(
                    task
                    for task, details in assignments.items()
                    if details["room"] == room_value and details["slot"] == slot_value
                )
                answer = task
                text = (
                    f"Which task is in {room_value} at Slot {slot_value}? "
                    "Answer with a single word."
                )
                answer_format = "single_word"
            elif kind == "tasks_in_room":
                room_value = str(value)
                tasks_in_room = sorted(
                    task
                    for task, details in assignments.items()
                    if details["room"] == room_value
                )
                answer = ", ".join(tasks_in_room)
                text = (
                    f"List the tasks in {room_value} "
                    "(comma-separated, alphabetically sorted)."
                )
                answer_format = "comma_separated_list"
            else:
                room_value, slot_value = cast(tuple[str, str], value)
                exists = any(
                    details["room"] == room_value and details["slot"] == slot_value
                    for details in assignments.values()
                )
                answer = "true" if exists else "false"
                text = (
                    f"Is any task in {room_value} at Slot {slot_value}? "
                    "Answer with true/false."
                )
                answer_format = "boolean"

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
