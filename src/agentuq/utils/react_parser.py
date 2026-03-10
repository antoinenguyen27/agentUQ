"""Small ReAct parser."""

from __future__ import annotations

import re


REACT_PREFIXES = (
    "Thought:",
    "Action:",
    "Action Input:",
    "Observation:",
    "Final Answer:",
)


def split_react_blocks(text: str) -> list[tuple[str, str, int, int]]:
    pattern = re.compile(r"^(Thought:|Action:|Action Input:|Observation:|Final Answer:)\s*", re.MULTILINE | re.IGNORECASE)
    matches = list(pattern.finditer(text))
    if not matches:
        return []
    blocks: list[tuple[str, str, int, int]] = []
    for index, match in enumerate(matches):
        start = match.start()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        label = match.group(1).rstrip(":").strip().lower().replace(" ", "_")
        blocks.append((label, text[start:end].strip(), start, end))
    return blocks
