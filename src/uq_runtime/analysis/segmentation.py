"""Semantic segmentation for action-bearing spans."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from uq_runtime.schemas.config import SegmentationConfig
from uq_runtime.schemas.records import GenerationRecord, StructuredBlock
from uq_runtime.utils.code_spans import split_code_statements
from uq_runtime.utils.json_spans import parse_json_leaves
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

REACT_PATTERN = re.compile(r"^(Thought:|Action:|Action Input:|Observation:|Final Answer:)\s*", re.MULTILINE | re.IGNORECASE)
BROWSER_LINE_PATTERN = re.compile(r"^\s*(?:Action:\s*)?([a-zA-Z_][\w]*)\((.*)\)\s*$", re.DOTALL)
FENCED_CODE_PATTERN = re.compile(r"```[^\n`]*\n(.*?)```", re.DOTALL)
CODE_KEYWORD_PATTERN = re.compile(
    r"^(?:"
    r"def |class |return\b|if\b|elif\b|else:|for\b|while\b|try:|except\b|with\b|import\b|from\b|"
    r"const |let |var |function\b|async\b|await\b|public\b|private\b|protected\b|"
    r"package\b|interface\b|enum\b|type\b"
    r")"
)
ASSIGNMENT_PATTERN = re.compile(r"^[A-Za-z_][\w.\[\]]*\s*=\s*[^=].+")
CALL_PATTERN = re.compile(r"^[A-Za-z_][\w.]*\([^)]*\)\s*;?$")


@dataclass
class SegmentSpec:
    id: str
    kind: str
    priority: str
    text: str
    char_span: tuple[int, int]
    token_span: tuple[int, int]
    metadata: dict


@dataclass
class ParentBlock:
    kind: str
    char_span: tuple[int, int]
    text: str
    source: str
    metadata: dict[str, Any]
    emit_kind: str | None = None
    block: StructuredBlock | None = None
    children: list["ParentBlock"] = field(default_factory=list)


@dataclass
class ReactBlock:
    label: str
    text: str
    char_span: tuple[int, int]
    content_span: tuple[int, int]


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
    for index, (_token_start, token_end) in enumerate(token_char_spans):
        if token_end > start_char:
            start_token = index
            break
    for index in range(start_token, len(token_char_spans)):
        token_start, _token_end = token_char_spans[index]
        if token_start >= end_char:
            end_token = index
            break
    return start_token, max(start_token + 1, end_token)


def _range_contains(parent: tuple[int, int], child: tuple[int, int]) -> bool:
    return parent[0] <= child[0] and parent[1] >= child[1]


def _range_overlaps(left: tuple[int, int], right: tuple[int, int]) -> bool:
    return left[0] < right[1] and right[0] < left[1]


def _coerce_span(value: object) -> tuple[int, int] | None:
    if isinstance(value, (list, tuple)) and len(value) == 2 and all(isinstance(part, int) for part in value):
        return int(value[0]), int(value[1])
    return None


def _find_occurrence(haystack: str, needle: str, start: int = 0) -> tuple[int, int] | None:
    index = haystack.find(needle, start)
    if index < 0:
        return None
    return index, index + len(needle)


def _block_span(block: StructuredBlock, raw_text: str, occurrence_counters: dict[str, int]) -> tuple[int, int] | None:
    if block.char_start is not None:
        end = block.char_end if block.char_end is not None else block.char_start + len(block.text or "")
        span = (block.char_start, end)
        if span[0] < span[1]:
            return span
        return None
    if not block.text or not raw_text:
        return None
    occurrence_index = occurrence_counters.get(block.text, 0)
    search_start = 0
    found: tuple[int, int] | None = None
    for _ in range(occurrence_index + 1):
        found = _find_occurrence(raw_text, block.text, search_start)
        if found is None:
            return None
        search_start = found[0] + 1
    occurrence_counters[block.text] = occurrence_index + 1
    return found


def _explicit_parent(block: StructuredBlock, raw_text: str, occurrence_counters: dict[str, int]) -> ParentBlock | None:
    span = _block_span(block, raw_text, occurrence_counters)
    if span is None:
        return None
    text = raw_text[span[0] : span[1]] if raw_text else (block.text or "")
    metadata = dict(block.metadata or {})
    metadata["segment_source"] = "structured_block"
    if block.type in {"function_call", "tool_call"}:
        return ParentBlock(kind="tool_call", char_span=span, text=text, source="structured_block", metadata=metadata, block=block)
    if block.type in {"json", "structured_output"}:
        return ParentBlock(kind="json", char_span=span, text=text, source="structured_block", metadata=metadata, block=block)
    if block.type == "output_text":
        emit_kind = "final_answer_text" if metadata.get("role") == "final" else "unknown_text"
        return ParentBlock(kind="text", char_span=span, text=text, source="structured_block", metadata=metadata, emit_kind=emit_kind, block=block)
    return ParentBlock(kind="text", char_span=span, text=text, source="structured_block", metadata=metadata, emit_kind="unknown_text", block=block)


def _insert_explicit_child(parent: ParentBlock, child: ParentBlock) -> None:
    for existing in parent.children:
        if _range_contains(existing.char_span, child.char_span):
            _insert_explicit_child(existing, child)
            return
        if _range_overlaps(existing.char_span, child.char_span) and not _range_contains(child.char_span, existing.char_span):
            return
    reparented: list[ParentBlock] = []
    remaining: list[ParentBlock] = []
    for existing in parent.children:
        if _range_contains(child.char_span, existing.char_span):
            reparented.append(existing)
        else:
            remaining.append(existing)
    child.children.extend(sorted(reparented, key=lambda item: (item.char_span[0], -(item.char_span[1] - item.char_span[0]))))
    remaining.append(child)
    remaining.sort(key=lambda item: (item.char_span[0], -(item.char_span[1] - item.char_span[0])))
    parent.children = remaining


def _react_blocks(text: str, base_start: int) -> list[ReactBlock]:
    matches = list(REACT_PATTERN.finditer(text))
    if not matches:
        return []
    blocks: list[ReactBlock] = []
    for index, match in enumerate(matches):
        start = match.start()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        label = match.group(1).rstrip(":").strip().lower().replace(" ", "_")
        block_text = text[start:end]
        blocks.append(
            ReactBlock(
                label=label,
                text=block_text,
                char_span=(base_start + start, base_start + end),
                content_span=(base_start + match.end(), base_start + end),
            )
        )
    return blocks


def _split_lines(text: str, base_start: int) -> list[tuple[str, int, int]]:
    lines: list[tuple[str, int, int]] = []
    cursor = 0
    for line in text.splitlines(keepends=True):
        start = base_start + cursor
        cursor += len(line)
        lines.append((line, start, base_start + cursor))
    if text and not text.endswith(("\n", "\r")) and (not lines or lines[-1][2] != base_start + len(text)):
        tail_start = base_start + cursor
        lines.append((text[cursor:], tail_start, base_start + len(text)))
    return lines


def _strip_span(text: str, span: tuple[int, int]) -> tuple[str, tuple[int, int]]:
    start = 0
    end = len(text)
    while start < end and text[start].isspace():
        start += 1
    while end > start and text[end - 1].isspace():
        end -= 1
    return text[start:end], (span[0] + start, span[0] + end)


def _looks_like_json(text: str) -> bool:
    stripped = text.strip()
    if not stripped or stripped[0] not in "{[" or stripped[-1] not in "}]":
        return False
    return bool(parse_json_leaves(stripped))


def _looks_like_sql(text: str) -> bool:
    stripped = text.strip()
    if not stripped:
        return False
    clauses = split_sql_clauses(stripped)
    if not clauses:
        return False
    first_clause = clauses[0][0]
    if first_clause not in {"SELECT", "UPDATE", "DELETE", "INSERT INTO"}:
        return False
    return clauses[0][2] == 0


def _looks_like_code_line(text: str) -> bool:
    stripped = text.strip()
    if not stripped or stripped.startswith(("-", "*")):
        return False
    if CODE_KEYWORD_PATTERN.match(stripped):
        return True
    if ASSIGNMENT_PATTERN.match(stripped):
        return True
    if stripped.endswith((";", "{", "}")):
        return True
    if "=>" in stripped:
        return True
    if CALL_PATTERN.match(stripped):
        return True
    return False


def _line_parent(kind: str, text: str, start: int, end: int, evidence: str) -> ParentBlock:
    return ParentBlock(
        kind=kind,
        char_span=(start, end),
        text=text,
        source="heuristic",
        metadata={"segment_source": "heuristic", "evidence": evidence},
    )


def _line_candidates(text: str, base_start: int, config: SegmentationConfig) -> list[ParentBlock]:
    lines = _split_lines(text, base_start)
    if not lines:
        return []
    candidates: list[ParentBlock] = []
    index = 0
    while index < len(lines):
        line_text, line_start, line_end = lines[index]
        stripped = line_text.strip()
        if not stripped:
            index += 1
            continue
        if config.enable_json_leaf_segmentation and _looks_like_json(stripped):
            trimmed_text, trimmed_span = _strip_span(line_text, (line_start, line_end))
            candidates.append(_line_parent("json", trimmed_text, trimmed_span[0], trimmed_span[1], "json_line"))
            index += 1
            continue
        if config.enable_browser_dsl_segmentation and BROWSER_LINE_PATTERN.match(stripped):
            trimmed_text, trimmed_span = _strip_span(line_text, (line_start, line_end))
            candidates.append(_line_parent("browser", trimmed_text, trimmed_span[0], trimmed_span[1], "browser_line"))
            index += 1
            continue
        if config.enable_sql_segmentation and _looks_like_sql(stripped):
            start = line_start
            end = line_end
            parts = [line_text]
            index += 1
            while index < len(lines):
                next_line_text, _next_start, next_end = lines[index]
                next_stripped = next_line_text.strip()
                if not next_stripped or not _looks_like_sql(next_stripped):
                    break
                parts.append(next_line_text)
                end = next_end
                index += 1
            combined_text, combined_span = _strip_span("".join(parts), (start, end))
            candidates.append(_line_parent("sql", combined_text, combined_span[0], combined_span[1], "sql_line"))
            continue
        if config.enable_code_segmentation and _looks_like_code_line(stripped):
            start = line_start
            end = line_end
            parts = [line_text]
            index += 1
            while index < len(lines):
                next_line_text, _next_start, next_end = lines[index]
                next_stripped = next_line_text.strip()
                if not next_stripped or not _looks_like_code_line(next_stripped):
                    break
                parts.append(next_line_text)
                end = next_end
                index += 1
            combined_text, combined_span = _strip_span("".join(parts), (start, end))
            candidates.append(_line_parent("code", combined_text, combined_span[0], combined_span[1], "code_line"))
            continue
        index += 1
    return candidates


class _SegmentationPlanner:
    def __init__(self, raw_text: str, token_char_spans: list[tuple[int, int]], config: SegmentationConfig) -> None:
        self.raw_text = raw_text
        self.token_char_spans = token_char_spans
        self.config = config
        self.segments: list[SegmentSpec] = []
        self.counter = 1

    def append_segment(self, kind: str, text: str, char_span: tuple[int, int], metadata: dict[str, Any] | None = None) -> None:
        if not text.strip():
            return
        self.segments.append(
            SegmentSpec(
                id=f"seg-{self.counter}",
                kind=kind,
                priority=PRIORITY_BY_KIND.get(kind, "informational"),
                text=text,
                char_span=char_span,
                token_span=_token_span_from_chars(self.token_char_spans, char_span),
                metadata=metadata or {},
            )
        )
        self.counter += 1

    def process(self, root: ParentBlock) -> list[SegmentSpec]:
        self.process_node(root)
        if not self.segments and self.raw_text.strip():
            self.emit_fallback("unknown_text", self.raw_text, (0, len(self.raw_text)), {"segment_source": "fallback"})
        self.segments.sort(key=lambda segment: (segment.char_span[0], -(segment.char_span[1] - segment.char_span[0]), segment.id))
        return self.segments

    def process_node(self, node: ParentBlock) -> None:
        if node.kind == "root":
            self.process_child_gaps(node, fallback_kind="unknown_text", allow_react=True)
            return
        if node.kind == "tool_call":
            self.segment_tool_node(node)
            return
        if node.kind == "json":
            self.segment_json_node(node)
            return
        if node.kind == "browser":
            self.segment_browser_node(node)
            return
        if node.kind == "sql":
            self.segment_sql_node(node)
            return
        if node.kind == "code":
            self.segment_code_node(node)
            return
        if node.kind == "react_action_input":
            self.segment_react_action_input(node)
            return
        if node.kind == "react_action":
            before = len(self.segments)
            self.process_text_region(node.text, node.char_span, fallback_kind=None, allow_react=False, metadata=node.metadata)
            if len(self.segments) == before:
                self.append_segment("browser_action", node.text.strip(), node.char_span, dict(node.metadata))
            return
        if node.emit_kind is not None:
            self.append_segment(node.emit_kind, node.text, node.char_span, dict(node.metadata))
        fallback_kind = None if node.emit_kind is not None else "unknown_text"
        self.process_child_gaps(node, fallback_kind=fallback_kind, allow_react="react_label" not in node.metadata)

    def process_child_gaps(self, node: ParentBlock, fallback_kind: str | None, allow_react: bool) -> None:
        cursor = node.char_span[0]
        for child in sorted(node.children, key=lambda item: (item.char_span[0], -(item.char_span[1] - item.char_span[0]))):
            if cursor < child.char_span[0]:
                self.process_text_region(
                    self.raw_text[cursor : child.char_span[0]],
                    (cursor, child.char_span[0]),
                    fallback_kind=fallback_kind,
                    allow_react=allow_react,
                    metadata=dict(node.metadata),
                )
            self.process_node(child)
            cursor = max(cursor, child.char_span[1])
        if cursor < node.char_span[1]:
            self.process_text_region(
                self.raw_text[cursor : node.char_span[1]],
                (cursor, node.char_span[1]),
                fallback_kind=fallback_kind,
                allow_react=allow_react,
                metadata=dict(node.metadata),
            )

    def process_text_region(
        self,
        text: str,
        span: tuple[int, int],
        fallback_kind: str | None,
        allow_react: bool,
        metadata: dict[str, Any],
    ) -> None:
        if not text.strip():
            return
        if allow_react and self.config.enable_react_segmentation:
            react_blocks = _react_blocks(text, span[0])
            if react_blocks:
                cursor = span[0]
                for block in react_blocks:
                    if cursor < block.char_span[0]:
                        self.process_text_region(
                            self.raw_text[cursor : block.char_span[0]],
                            (cursor, block.char_span[0]),
                            fallback_kind=fallback_kind,
                            allow_react=False,
                            metadata=metadata,
                        )
                    self.process_node(self.react_parent(block, metadata))
                    cursor = block.char_span[1]
                if cursor < span[1]:
                    self.process_text_region(
                        self.raw_text[cursor : span[1]],
                        (cursor, span[1]),
                        fallback_kind=fallback_kind,
                        allow_react=False,
                        metadata=metadata,
                    )
                return
        if self.config.enable_json_leaf_segmentation and _looks_like_json(text):
            stripped_text, stripped_span = _strip_span(text, span)
            self.process_node(
                ParentBlock(
                    kind="json",
                    char_span=stripped_span,
                    text=stripped_text,
                    source="heuristic",
                    metadata={**metadata, "segment_source": "heuristic", "evidence": "json_parser"},
                )
            )
            return
        if self.config.enable_code_segmentation:
            fenced_blocks = list(FENCED_CODE_PATTERN.finditer(text))
            if fenced_blocks:
                cursor = span[0]
                for match in fenced_blocks:
                    fenced_span = (span[0] + match.start(), span[0] + match.end())
                    inner_span = (span[0] + match.start(1), span[0] + match.end(1))
                    if cursor < fenced_span[0]:
                        self.process_text_region(
                            self.raw_text[cursor : fenced_span[0]],
                            (cursor, fenced_span[0]),
                            fallback_kind=fallback_kind,
                            allow_react=False,
                            metadata=metadata,
                        )
                    inner_text = self.raw_text[inner_span[0] : inner_span[1]]
                    if inner_text.strip():
                        self.process_node(
                            ParentBlock(
                                kind="code",
                                char_span=inner_span,
                                text=inner_text,
                                source="heuristic",
                                metadata={**metadata, "segment_source": "heuristic", "evidence": "fenced_code"},
                            )
                        )
                    cursor = fenced_span[1]
                if cursor < span[1]:
                    self.process_text_region(
                        self.raw_text[cursor : span[1]],
                        (cursor, span[1]),
                        fallback_kind=fallback_kind,
                        allow_react=False,
                        metadata=metadata,
                    )
                return
        candidates = _line_candidates(text, span[0], self.config)
        if candidates:
            cursor = span[0]
            for candidate in candidates:
                if cursor < candidate.char_span[0]:
                    self.process_text_region(
                        self.raw_text[cursor : candidate.char_span[0]],
                        (cursor, candidate.char_span[0]),
                        fallback_kind=fallback_kind,
                        allow_react=False,
                        metadata=metadata,
                    )
                self.process_node(candidate)
                cursor = candidate.char_span[1]
            if cursor < span[1]:
                self.process_text_region(
                    self.raw_text[cursor : span[1]],
                    (cursor, span[1]),
                    fallback_kind=fallback_kind,
                    allow_react=False,
                    metadata=metadata,
                )
            return
        if fallback_kind is not None:
            self.emit_fallback(fallback_kind, text, span, {**metadata, "segment_source": metadata.get("segment_source", "fallback")})

    def emit_fallback(self, kind: str, text: str, span: tuple[int, int], metadata: dict[str, Any]) -> None:
        if self.config.fallback_line_split:
            cursor = span[0]
            for line in text.splitlines(keepends=True):
                line_start = cursor
                cursor += len(line)
                stripped = line.strip()
                if not stripped:
                    continue
                self.append_segment(kind, stripped, (line_start, cursor), dict(metadata))
            if cursor < span[1]:
                stripped = self.raw_text[cursor : span[1]].strip()
                if stripped:
                    self.append_segment(kind, stripped, (cursor, span[1]), dict(metadata))
            return
        self.append_segment(kind, text, span, dict(metadata))

    def react_parent(self, block: ReactBlock, metadata: dict[str, Any]) -> ParentBlock:
        block_metadata = {**metadata, "segment_source": "heuristic", "react_label": block.label}
        if block.label == "thought":
            return ParentBlock(kind="text", char_span=block.char_span, text=block.text, source="heuristic", metadata=block_metadata, emit_kind="reasoning_text")
        if block.label == "observation":
            return ParentBlock(kind="text", char_span=block.char_span, text=block.text, source="heuristic", metadata=block_metadata, emit_kind="unknown_text")
        if block.label == "final_answer":
            return ParentBlock(kind="text", char_span=block.char_span, text=block.text, source="heuristic", metadata=block_metadata, emit_kind="final_answer_text")
        if block.label == "action_input":
            block_metadata["content_char_span"] = block.content_span
            return ParentBlock(kind="react_action_input", char_span=block.char_span, text=block.text, source="heuristic", metadata=block_metadata, emit_kind="tool_arguments_raw")
        return ParentBlock(kind="react_action", char_span=block.char_span, text=block.text, source="heuristic", metadata=block_metadata)

    def segment_json_node(self, node: ParentBlock) -> None:
        search_cursor = 0
        emitted = False
        for jsonpath, value in parse_json_leaves(node.text):
            relative_span = _find_occurrence(node.text, value, search_cursor)
            if relative_span is None:
                continue
            search_cursor = relative_span[1]
            span = (node.char_span[0] + relative_span[0], node.char_span[0] + relative_span[1])
            self.append_segment("json_leaf", value, span, {**node.metadata, "jsonpath": jsonpath})
            emitted = True
        if not emitted:
            self.append_segment("unknown_text", node.text, node.char_span, dict(node.metadata))

    def segment_tool_node(self, node: ParentBlock) -> None:
        block = node.block
        if block is None:
            return
        metadata = dict(node.metadata)
        name_span, arguments_span = self.tool_block_spans(block)
        if block.name and name_span is not None:
            self.append_segment("tool_name", block.name, name_span, {**metadata, "tool_name": block.name})
        if block.arguments and arguments_span is not None:
            self.append_segment("tool_arguments_raw", block.arguments, arguments_span, metadata)
            search_cursor = 0
            for jsonpath, value in parse_json_leaves(block.arguments):
                relative_span = _find_occurrence(block.arguments, value, search_cursor)
                if relative_span is None:
                    continue
                search_cursor = relative_span[1]
                span = (arguments_span[0] + relative_span[0], arguments_span[0] + relative_span[1])
                self.append_segment("tool_argument_leaf", value, span, {**metadata, "jsonpath": jsonpath, "tool_name": block.name})

    def tool_block_spans(self, block: StructuredBlock) -> tuple[tuple[int, int] | None, tuple[int, int] | None]:
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

    def segment_browser_node(self, node: ParentBlock) -> None:
        match = BROWSER_LINE_PATTERN.match(node.text.strip())
        if match is None:
            return
        command = match.group(1)
        args = match.group(2)
        command_start = node.text.find(command)
        if command_start < 0:
            return
        command_span = (node.char_span[0] + command_start, node.char_span[0] + command_start + len(command))
        self.append_segment("browser_action", command, command_span, dict(node.metadata))
        args_offset = node.text.find(args, command_start)
        if args_offset < 0:
            return
        for arg_match in re.finditer(r"([a-zA-Z_][\w]*)\s*=\s*\"([^\"]+)\"", args):
            key = arg_match.group(1)
            value = arg_match.group(2)
            value_span = (
                node.char_span[0] + args_offset + arg_match.start(2),
                node.char_span[0] + args_offset + arg_match.end(2),
            )
            kind = "browser_selector" if key in {"selector", "target", "id"} else "browser_text_value"
            self.append_segment(kind, value, value_span, {**node.metadata, "argument": key})

    def segment_sql_node(self, node: ParentBlock) -> None:
        for clause_name, clause_text, start, end in split_sql_clauses(node.text):
            self.append_segment("sql_clause", clause_text, (node.char_span[0] + start, node.char_span[0] + end), {**node.metadata, "clause": clause_name})

    def segment_code_node(self, node: ParentBlock) -> None:
        for line, start, end in split_code_statements(node.text):
            self.append_segment("code_statement", line, (node.char_span[0] + start, node.char_span[0] + end), dict(node.metadata))

    def segment_react_action_input(self, node: ParentBlock) -> None:
        self.append_segment("tool_arguments_raw", node.text, node.char_span, dict(node.metadata))
        if not self.config.enable_json_leaf_segmentation:
            return
        content_span = _coerce_span(node.metadata.get("content_char_span"))
        if content_span is None:
            return
        content_text = self.raw_text[content_span[0] : content_span[1]]
        stripped_text, stripped_span = _strip_span(content_text, content_span)
        if not _looks_like_json(stripped_text):
            return
        search_cursor = 0
        for jsonpath, value in parse_json_leaves(stripped_text):
            relative_span = _find_occurrence(stripped_text, value, search_cursor)
            if relative_span is None:
                continue
            search_cursor = relative_span[1]
            span = (stripped_span[0] + relative_span[0], stripped_span[0] + relative_span[1])
            self.append_segment("json_leaf", value, span, {**node.metadata, "jsonpath": jsonpath})


def segment_record(record: GenerationRecord, config: SegmentationConfig) -> list[SegmentSpec]:
    raw_text = record.raw_text or "".join(record.selected_tokens)
    token_char_spans = _token_char_spans(record.selected_tokens)
    root = ParentBlock(kind="root", char_span=(0, len(raw_text)), text=raw_text, source="raw_text", metadata={})
    occurrence_counters: dict[str, int] = {}
    explicit_blocks = []
    for block in record.structured_blocks:
        parent = _explicit_parent(block, raw_text, occurrence_counters)
        if parent is not None:
            explicit_blocks.append(parent)
    explicit_blocks.sort(key=lambda item: (item.char_span[0], -(item.char_span[1] - item.char_span[0])))
    for parent in explicit_blocks:
        _insert_explicit_child(root, parent)
    return _SegmentationPlanner(raw_text, token_char_spans, config).process(root)
