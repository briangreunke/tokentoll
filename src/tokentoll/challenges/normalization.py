from __future__ import annotations


def normalize_answer(answer: str, format: str) -> str:
    normalized = answer.strip().lower()

    if format == "single_word":
        return normalized
    if format == "comma_separated_list":
        items = [item.strip().lower() for item in normalized.split(",") if item.strip()]
        items.sort()
        return ", ".join(items)
    if format == "integer":
        return str(int(normalized))
    if format == "boolean":
        truthy = {"true", "t", "yes", "y", "1"}
        falsy = {"false", "f", "no", "n", "0"}
        if normalized in truthy:
            return "true"
        if normalized in falsy:
            return "false"
        raise ValueError("Unknown boolean value")

    raise ValueError(f"Unknown answer format: {format}")
