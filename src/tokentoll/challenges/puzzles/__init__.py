from __future__ import annotations

from tokentoll.challenges.puzzles.base import PuzzleGenerator
from tokentoll.challenges.puzzles.constraint_satisfaction import ConstraintSatisfactionPuzzle
from tokentoll.challenges.puzzles.logic_grid import LogicGridPuzzle
from tokentoll.challenges.puzzles.rule_system import RuleSystemPuzzle

AVAILABLE_PUZZLES: dict[str, type[PuzzleGenerator]] = {
    "logic_grid": LogicGridPuzzle,
    "constraint_satisfaction": ConstraintSatisfactionPuzzle,
    "rule_system": RuleSystemPuzzle,
}

__all__ = ["AVAILABLE_PUZZLES", "ConstraintSatisfactionPuzzle", "LogicGridPuzzle", "RuleSystemPuzzle"]
