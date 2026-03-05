from __future__ import annotations

import pytest

from tokentoll.challenges.normalization import normalize_answer


def test_normalize_single_word() -> None:
    assert normalize_answer("  Hello ", "single_word") == "hello"


def test_normalize_comma_separated_list() -> None:
    value = "Banana, apple,  Cherry ,,  date"
    assert normalize_answer(value, "comma_separated_list") == "apple, banana, cherry, date"


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (" 007 ", "7"),
        ("-3", "-3"),
        ("0", "0"),
    ],
)
def test_normalize_integer(value: str, expected: str) -> None:
    assert normalize_answer(value, "integer") == expected


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("TRUE", "true"),
        (" false ", "false"),
        ("Yes", "true"),
        ("no", "false"),
        ("1", "true"),
        ("0", "false"),
    ],
)
def test_normalize_boolean(value: str, expected: str) -> None:
    assert normalize_answer(value, "boolean") == expected


def test_normalize_unknown_format_raises() -> None:
    with pytest.raises(ValueError, match="Unknown answer format"):
        normalize_answer("value", "mystery")
