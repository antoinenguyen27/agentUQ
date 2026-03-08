"""Code statement helpers."""

from __future__ import annotations


def split_code_statements(text: str) -> list[tuple[str, int, int]]:
    segments: list[tuple[str, int, int]] = []
    cursor = 0
    for line in text.splitlines(keepends=True):
        start = cursor
        cursor += len(line)
        stripped = line.strip()
        if not stripped:
            continue
        segments.append((stripped, start, cursor))
    return segments

