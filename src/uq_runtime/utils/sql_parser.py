"""Lightweight SQL clause splitting."""

from __future__ import annotations

import re


CLAUSE_PATTERN = re.compile(
    r"\b(SELECT|FROM|WHERE|JOIN|ORDER BY|GROUP BY|LIMIT|UPDATE|DELETE|INSERT INTO|VALUES|SET)\b",
    re.IGNORECASE,
)


def split_sql_clauses(text: str) -> list[tuple[str, str, int, int]]:
    matches = list(CLAUSE_PATTERN.finditer(text))
    if not matches:
        return []
    clauses: list[tuple[str, str, int, int]] = []
    for index, match in enumerate(matches):
        start = match.start()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        clause_name = match.group(1).upper()
        clauses.append((clause_name, text[start:end].strip(), start, end))
    return clauses

