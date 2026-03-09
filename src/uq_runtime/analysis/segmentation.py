"""Semantic segmentation for action-bearing spans."""

from __future__ import annotations

import re
from dataclasses import dataclass

from uq_runtime.schemas.config import SegmentationConfig
from uq_runtime.schemas.records import GenerationRecord, StructuredBlock
from uq_runtime.utils.code_spans import split_code_statements
from uq_runtime.utils.json_spans import parse_json_leaves
from uq_runtime.utils.react_parser import split_react_blocks
from uq_runtime.utils.sql_parser import split_sql_clauses


PRIORITY_BY_KIND = {
    "tool_name": "critical_action",
    "browser_action": "critical_action",
    "browser_selector": "critical_action",
    "url": "critical_action",
    "identifier": "critical_action",
    "sql_clause": "critical_action",
    "shell_flag": "critical_action",
    "shell_value": "critical_action",
    "tool_arguments_raw": "important_action",
    "tool_argument_leaf": "important_action",
    "json_leaf": "important_action",
    "browser_text_value": "important_action",
    "code_statement": "important_action",
    "final_answer_text": "informational",
    "reasoning_text": "low_priority",
    "unknown_text": "informational",
}


@dataclass
class SegmentSpec:
    id: str
    kind: str
    priority: str
    text: str
    char_span: tuple[int, int]
    token_span: tuple[int, int]
    metadata: dict


def _token_char_spans(tokens: list[str]) -> list[tuple[int, int]]:
    spans: list[tuple[int, int]] = []
    cursor = 0
    for token in tokens:
        start = cursor
        cursor += len(token)
        spans.append((start, cursor))
    return spans


def _token_span_from_chars(token_char_spans: list[tuple[int, int]], char_span: tuple[int, int]) -> tuple[int, int]:
    start_char, end_char = char_span
    start_token = 0
    end_token = len(token_char_spans)
    for index, (token_start, token_end) in enumerate(token_char_spans):
        if token_end > start_char:
            start_token = index
            break
    for index in range(start_token, len(token_char_spans)):
        token_start, token_end = token_char_spans[index]
        if token_start >= end_char:
            end_token = index
            break
    return start_token, max(start_token + 1, end_token)


def _append_segment(segments: list[SegmentSpec], counter: int, kind: str, text: str, char_span: tuple[int, int], token_char_spans: list[tuple[int, int]], metadata: dict | None = None) -> int:
    if not text.strip():
        return counter
    segments.append(
        SegmentSpec(
            id=f"seg-{counter}",
            kind=kind,
            priority=PRIORITY_BY_KIND.get(kind, "informational"),
            text=text,
            char_span=char_span,
            token_span=_token_span_from_chars(token_char_spans, char_span),
            metadata=metadata or {},
        )
    )
    return counter + 1


def _find_occurrence(haystack: str, needle: str, start: int = 0) -> tuple[int, int] | None:
    index = haystack.find(needle, start)
    if index < 0:
        return None
    return index, index + len(needle)


def _coerce_span(value: object) -> tuple[int, int] | None:
    if isinstance(value, (list, tuple)) and len(value) == 2 and all(isinstance(part, int) for part in value):
        return int(value[0]), int(value[1])
    return None


def _tool_block_spans(block: StructuredBlock) -> tuple[tuple[int, int] | None, tuple[int, int] | None]:
    metadata = block.metadata or {}
    name_span = _coerce_span(metadata.get("name_char_span"))
    arguments_span = _coerce_span(metadata.get("arguments_char_span"))
    if name_span or arguments_span:
        return name_span, arguments_span
    if not metadata.get("token_grounded") or block.char_start is None or not block.text:
        return None, None
    block_offset = block.char_start
    if name_span is None and block.name:
        name_match = _find_occurrence(block.text, block.name)
        if name_match is not None:
            name_span = (block_offset + name_match[0], block_offset + name_match[1])
    if arguments_span is None and block.arguments:
        arguments_match = _find_occurrence(block.text, block.arguments)
        if arguments_match is not None:
            arguments_span = (block_offset + arguments_match[0], block_offset + arguments_match[1])
    return name_span, arguments_span


def _segment_json(block: StructuredBlock, raw_text: str, token_char_spans: list[tuple[int, int]], counter: int, segments: list[SegmentSpec]) -> int:
    if block.text is None:
        return counter
    origin = block.char_start or 0
    search_cursor = origin
    for jsonpath, value in parse_json_leaves(block.text):
        span = _find_occurrence(raw_text, value, search_cursor)
        if span is None:
            continue
        search_cursor = span[1]
        counter = _append_segment(segments, counter, "json_leaf", value, span, token_char_spans, {"jsonpath": jsonpath})
    return counter


def _segment_tool_arguments(block: StructuredBlock, raw_text: str, token_char_spans: list[tuple[int, int]], counter: int, segments: list[SegmentSpec]) -> int:
    name_span, arguments_span = _tool_block_spans(block)
    if block.name and name_span is not None:
        counter = _append_segment(segments, counter, "tool_name", block.name, name_span, token_char_spans, {"tool_name": block.name})
    if block.arguments and arguments_span is not None:
        counter = _append_segment(segments, counter, "tool_arguments_raw", block.arguments, arguments_span, token_char_spans)
        search_cursor = 0
        for jsonpath, value in parse_json_leaves(block.arguments):
            relative_span = _find_occurrence(block.arguments, value, search_cursor)
            if relative_span is None:
                continue
            search_cursor = relative_span[1]
            span = (arguments_span[0] + relative_span[0], arguments_span[0] + relative_span[1])
            counter = _append_segment(segments, counter, "tool_argument_leaf", value, span, token_char_spans, {"jsonpath": jsonpath, "tool_name": block.name})
    return counter


def segment_record(record: GenerationRecord, config: SegmentationConfig) -> list[SegmentSpec]:
    raw_text = record.raw_text or "".join(record.selected_tokens)
    token_char_spans = _token_char_spans(record.selected_tokens)
    segments: list[SegmentSpec] = []
    counter = 1

    if record.structured_blocks:
        for block in record.structured_blocks:
            if block.type in {"function_call", "tool_call"}:
                counter = _segment_tool_arguments(block, raw_text, token_char_spans, counter, segments)
            elif block.type in {"json", "structured_output"} and config.enable_json_leaf_segmentation:
                counter = _segment_json(block, raw_text, token_char_spans, counter, segments)
            elif block.type == "output_text" and block.text:
                kind = "final_answer_text" if block.metadata.get("role") == "final" else "unknown_text"
                span = (block.char_start or 0, block.char_end or (block.char_start or 0) + len(block.text))
                counter = _append_segment(segments, counter, kind, block.text, span, token_char_spans, block.metadata)

    if config.enable_react_segmentation:
        for label, text, start, end in split_react_blocks(raw_text):
            kind = {
                "thought": "reasoning_text",
                "action": "browser_action",
                "action_input": "tool_arguments_raw",
                "observation": "unknown_text",
                "final_answer": "final_answer_text",
            }.get(label, "unknown_text")
            counter = _append_segment(segments, counter, kind, text, (start, end), token_char_spans, {"react_label": label})

    if config.enable_browser_dsl_segmentation:
        for match in re.finditer(r"([a-zA-Z_][\w]*)\((.*?)\)", raw_text):
            command = match.group(1)
            args = match.group(2)
            counter = _append_segment(segments, counter, "browser_action", command, (match.start(1), match.end(1)), token_char_spans)
            for arg_match in re.finditer(r"([a-zA-Z_][\w]*)\s*=\s*\"([^\"]+)\"", args):
                key, value = arg_match.group(1), arg_match.group(2)
                offset = match.start(2)
                value_span = (offset + arg_match.start(2), offset + arg_match.end(2))
                kind = "browser_selector" if key in {"selector", "target", "id"} else "browser_text_value"
                counter = _append_segment(segments, counter, kind, value, value_span, token_char_spans, {"argument": key})

    if config.enable_sql_segmentation:
        for clause_name, clause_text, start, end in split_sql_clauses(raw_text):
            counter = _append_segment(segments, counter, "sql_clause", clause_text, (start, end), token_char_spans, {"clause": clause_name})

    if config.enable_code_segmentation:
        for line, start, end in split_code_statements(raw_text):
            counter = _append_segment(segments, counter, "code_statement", line, (start, end), token_char_spans)

    if not segments:
        if config.fallback_line_split and raw_text.strip():
            cursor = 0
            for line in raw_text.splitlines(keepends=True):
                start = cursor
                cursor += len(line)
                counter = _append_segment(segments, counter, "unknown_text", line.strip(), (start, cursor), token_char_spans)
        elif raw_text.strip():
            counter = _append_segment(segments, counter, "unknown_text", raw_text, (0, len(raw_text)), token_char_spans)
    return segments
