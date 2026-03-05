from __future__ import annotations

from abc import ABC, abstractmethod
import math
import random

from tokentoll.challenges.types import GeneratedChallenge


class PuzzleGenerator(ABC):
    def __init__(self, seed: str) -> None:
        self._seed = seed

    @property
    def seed(self) -> str:
        return self._seed

    @property
    @abstractmethod
    def puzzle_type(self) -> str:
        raise NotImplementedError

    @abstractmethod
    def generate(self, rng: random.Random, num_questions: int) -> GeneratedChallenge:
        raise NotImplementedError


def estimate_tokens(text: str) -> int:
    word_count = len(text.split())
    return int(word_count * 1.3)


def pad_context(context: str, target_tokens: int, rng: random.Random) -> str:
    target_words = math.ceil(target_tokens / 1.3)
    current_words = len(context.split())
    if current_words >= target_words:
        return context

    needed = target_words - current_words
    filler_words = _generate_filler_words(needed, rng)
    filler_text = " ".join(filler_words)
    return f"{context}\n\nAdditional Notes:\n{filler_text}"


def _generate_filler_words(count: int, rng: random.Random) -> list[str]:
    base_words = [
        "alpha",
        "beta",
        "gamma",
        "delta",
        "epsilon",
        "zeta",
        "eta",
        "theta",
        "iota",
        "kappa",
        "lambda",
        "mu",
        "nu",
        "xi",
        "omicron",
        "pi",
        "rho",
        "sigma",
        "tau",
        "upsilon",
        "phi",
        "chi",
        "psi",
        "omega",
    ]
    return [rng.choice(base_words) for _ in range(count)]
