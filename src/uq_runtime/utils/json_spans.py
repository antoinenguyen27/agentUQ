"""Helpers for locating JSON leaves."""

from __future__ import annotations

import json
from typing import Any


def iter_json_leaves(value: Any, prefix: str = "$") -> list[tuple[str, str]]:
    leaves: list[tuple[str, str]] = []
    if isinstance(value, dict):
        for key, child in value.items():
            leaves.extend(iter_json_leaves(child, f"{prefix}.{key}"))
        return leaves
    if isinstance(value, list):
        for index, child in enumerate(value):
            leaves.extend(iter_json_leaves(child, f"{prefix}[{index}]"))
        return leaves
    rendered = json.dumps(value) if not isinstance(value, str) else value
    leaves.append((prefix, rendered.strip('"')))
    return leaves


def parse_json_leaves(text: str) -> list[tuple[str, str]]:
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        return []
    return iter_json_leaves(parsed)

