"""Semantic segmentation for action-bearing spans."""

from __future__ import annotations

import re
import shlex
from dataclasses import dataclass, field
from typing import Any

from uq_runtime.schemas.config import SegmentationConfig
from uq_runtime.schemas.records import GenerationRecord, StructuredBlock
from uq_runtime.utils.code_spans import split_code_statements
from uq_runtime.utils.json_spans import parse_json_leaves
from uq_runtime.utils.sql_parser import is_sql_continuation, is_sql_statement, sql_statement_head, split_sql_clauses


PRIORITY_BY_KIND = {
    "tool_name": "critical_action",
    "browser_action": "critical_action",
    "browser_selector": "critical_action",
    "url": "critical_action",
    "identifier": "critical_action",
    "path": "critical_action",
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
FENCED_CODE_PATTERN = re.compile(r"```([^\n`]*)\n(.*?)```", re.DOTALL)
INLINE_CODE_PATTERN = re.compile(r"(?<!`)`([^`\n]+)`(?!`)")
URL_PATTERN = re.compile(r"https?://[^\s\"')]+")
PATH_PATTERN = re.compile(r"(?:\.\.?/|/|~/)[^\s]+")
CALL_PATTERN = re.compile(r"^[A-Za-z_][\w.]*\([^)]*\)\s*;?$")
ASSIGNMENT_PATTERN = re.compile(r"^[A-Za-z_][\w.\[\]]*\s*=\s*[^=].+")
PY_DEF_PATTERN = re.compile(r"^(?:async\s+def|def)\s+[A-Za-z_][\w]*\s*\(.*\)\s*:\s*$")
PY_CLASS_PATTERN = re.compile(r"^class\s+[A-Za-z_][\w]*(?:\s*\(.*\))?\s*:\s*$")
JS_FUNCTION_PATTERN = re.compile(r"^(?:async\s+)?function\s+[A-Za-z_][\w]*\s*\(.*\)\s*\{?\s*$")
IMPORT_PATTERN = re.compile(r"^(?:import\s+[\w.*{}, ]+|from\s+[\w.]+\s+import\s+[\w.*{}, ]+)\s*$")
DECLARATIVE_PATTERN = re.compile(r"^(?:const|let|var|interface|enum|type)\s+\S+")
CONTROL_FLOW_PATTERN = re.compile(r"^(?:if|elif|else|for|while|try|except|with)\b.*(?:[:{]|\)\s*\{)\s*$")
PROMPT_PATTERN = re.compile(r"^\$\s+")
BROWSER_CALL_PATTERN = re.compile(r"^\s*([A-Za-z_][\w]*)\((.*)\)\s*$", re.DOTALL)
NAMED_BROWSER_ARG_PATTERN = re.compile(r"^\s*([A-Za-z_][\w]*)\s*=\s*(['\"])(.*)\2\s*$", re.DOTALL)
QUOTED_VALUE_PATTERN = re.compile(r"^\s*(['\"])(.*)\1\s*$", re.DOTALL)
TOKEN_VALUE_PATTERN = re.compile(r"^[A-Za-z][A-Za-z0-9._-]*$")

COMMON_SHELL_COMMANDS = {
    "bash",
    "cat",
    "cd",
    "chmod",
    "cp",
    "curl",
    "echo",
    "find",
    "git",
    "grep",
    "ls",
    "mkdir",
    "mv",
    "npm",
    "pip",
    "python",
    "python3",
    "rg",
    "rm",
    "sed",
    "sh",
    "touch",
    "zsh",
}
BROWSER_VERBS = {"click", "type", "navigate"}
BROWSER_ARG_KEYS = {
    "click": {"selector", "target", "id"},
    "type": {"selector", "target", "id", "text"},
    "navigate": {"url", "href", "src"},
}
SNIPPET_LABEL_WORDS = {
    "action",
    "browser",
    "call",
    "cmd",
    "code",
    "command",
    "example",
    "json",
    "path",
    "payload",
    "query",
    "response",
    "run",
    "selector",
    "shell",
    "snippet",
    "sql",
    "url",
}
SHELL_LABEL_WORDS = {"cmd", "command", "run", "shell"}


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


@dataclass
class LiteralCandidate:
    text: str
    char_span: tuple[int, int]
    cover_span: tuple[int, int]
    evidence: str
    allow_shell: bool = False
    hint: str | None = None


@dataclass
class BrowserArgument:
    key: str | None
    value: str
    kind: str
    value_span: tuple[int, int]


@dataclass
class BrowserInvocation:
    command: str
    command_span: tuple[int, int]
    arguments: list[BrowserArgument]


@dataclass
class ShellToken:
    kind: str
    text: str
    span: tuple[int, int]
    role: str


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


def _fenced_kind(language: str) -> str | None:
    lang = language.strip().lower()
    if lang == "sql":
        return "sql"
    if lang == "json":
        return "json"
    if lang in {"bash", "sh", "zsh", "shell"}:
        return "shell"
    if lang:
        return "code"
    return None


def _is_path(value: str) -> bool:
    return bool(PATH_PATTERN.fullmatch(value))


def _is_identifier(value: str) -> bool:
    return bool(re.fullmatch(r"[A-Za-z_][\w./:-]*", value))


def _balanced_delimiters(text: str) -> bool:
    pairs = {"(": ")", "[": "]", "{": "}"}
    closing = {value: key for key, value in pairs.items()}
    stack: list[str] = []
    quote: str | None = None
    index = 0
    while index < len(text):
        char = text[index]
        if quote is not None:
            if char == "\\":
                index += 2
                continue
            if char == quote:
                quote = None
            index += 1
            continue
        if char in {"'", '"'}:
            quote = char
            index += 1
            continue
        if char in pairs:
            stack.append(char)
        elif char in closing:
            if not stack or stack[-1] != closing[char]:
                return False
            stack.pop()
        index += 1
    return quote is None and not stack


def _looks_like_code_line(text: str) -> bool:
    stripped = text.strip()
    if not stripped or stripped.startswith(("-", "*")):
        return False
    if ASSIGNMENT_PATTERN.match(stripped):
        return True
    if CALL_PATTERN.match(stripped):
        return True
    if PY_DEF_PATTERN.match(stripped) or PY_CLASS_PATTERN.match(stripped):
        return True
    if JS_FUNCTION_PATTERN.match(stripped) or IMPORT_PATTERN.match(stripped) or DECLARATIVE_PATTERN.match(stripped):
        return True
    if CONTROL_FLOW_PATTERN.match(stripped):
        return True
    if "=>" in stripped and _balanced_delimiters(stripped):
        return True
    if stripped.endswith(("{", "}")) and _balanced_delimiters(stripped):
        return True
    if stripped.endswith(";") and _balanced_delimiters(stripped):
        return bool(re.search(r"[=()[\]{}.]|return\b|await\b|new\b", stripped))
    return False


def _split_browser_arguments(text: str) -> list[tuple[str, int, int]]:
    items: list[tuple[str, int, int]] = []
    start = 0
    quote: str | None = None
    index = 0
    while index < len(text):
        char = text[index]
        if quote is not None:
            if char == "\\":
                index += 2
                continue
            if char == quote:
                quote = None
            index += 1
            continue
        if char in {"'", '"'}:
            quote = char
            index += 1
            continue
        if char == ",":
            item = text[start:index].strip()
            if item:
                item_start = start + len(text[start:index]) - len(text[start:index].lstrip())
                item_end = index - len(text[start:index]) + len(text[start:index].rstrip())
                items.append((item, item_start, item_end))
            start = index + 1
        index += 1
    tail = text[start:]
    item = tail.strip()
    if item:
        item_start = start + len(tail) - len(tail.lstrip())
        item_end = len(text) - len(tail) + len(tail.rstrip())
        items.append((item, item_start, item_end))
    return items


def _browser_value_kind(command: str, key: str | None, value: str) -> str:
    if key in {"selector", "target", "id"}:
        return "browser_selector"
    if key in {"url", "href", "src"} or URL_PATTERN.fullmatch(value):
        return "url"
    if _is_path(value):
        return "path"
    if key is None and command == "click":
        return "browser_selector"
    return "browser_text_value"


def _parse_browser_invocation(text: str) -> BrowserInvocation | None:
    match = BROWSER_CALL_PATTERN.match(text.strip())
    if match is None:
        return None
    command = match.group(1)
    if command not in BROWSER_VERBS:
        return None
    args_text = match.group(2)
    if not args_text.strip():
        return None
    arguments: list[BrowserArgument] = []
    items = _split_browser_arguments(args_text)
    if len(items) == 1 and command in {"click", "type"}:
        item_text, item_start, _item_end = items[0]
        value_match = QUOTED_VALUE_PATTERN.match(item_text)
        if value_match is not None:
            value = value_match.group(2)
            value_span = (match.start(2) + item_start + value_match.start(2), match.start(2) + item_start + value_match.end(2))
            arguments.append(BrowserArgument(key=None, value=value, kind=_browser_value_kind(command, None, value), value_span=value_span))
            return BrowserInvocation(command=command, command_span=match.span(1), arguments=arguments)
    for item_text, item_start, _item_end in items:
        arg_match = NAMED_BROWSER_ARG_PATTERN.match(item_text)
        if arg_match is None:
            return None
        key = arg_match.group(1)
        if key not in BROWSER_ARG_KEYS[command]:
            return None
        value = arg_match.group(3)
        value_span = (match.start(2) + item_start + arg_match.start(3), match.start(2) + item_start + arg_match.end(3))
        arguments.append(BrowserArgument(key=key, value=value, kind=_browser_value_kind(command, key, value), value_span=value_span))
    if not arguments:
        return None
    return BrowserInvocation(command=command, command_span=match.span(1), arguments=arguments)


def _shell_token_spans(line: str) -> list[tuple[str, tuple[int, int]]]:
    spans: list[tuple[str, tuple[int, int]]] = []
    cursor = 0
    length = len(line)
    while cursor < length:
        while cursor < length and line[cursor].isspace():
            cursor += 1
        if cursor >= length:
            break
        start = cursor
        in_quote: str | None = None
        while cursor < length:
            char = line[cursor]
            if in_quote:
                if char == in_quote:
                    in_quote = None
                cursor += 1
                continue
            if char in {"'", '"'}:
                in_quote = char
                cursor += 1
                continue
            if char.isspace():
                break
            cursor += 1
        spans.append((line[start:cursor], (start, cursor)))
    return spans


def _parse_shell_command(text: str, allow_prompt: bool) -> list[ShellToken] | None:
    working = text.strip()
    offset = len(text) - len(working)
    if PROMPT_PATTERN.match(working):
        if not allow_prompt:
            return None
        prompt_match = PROMPT_PATTERN.match(working)
        assert prompt_match is not None
        offset += prompt_match.end()
        working = working[prompt_match.end() :]
    try:
        shlex.split(working)
    except ValueError:
        return None
    relative_tokens = _shell_token_spans(working)
    if len(relative_tokens) < 2:
        return None
    head_token = relative_tokens[0][0].strip("\"'")
    if head_token not in COMMON_SHELL_COMMANDS and not _is_path(head_token):
        return None
    saw_marker = False
    plain_before_marker = 0
    expects_flag_value = False
    emitted: list[ShellToken] = []
    command_span = (offset + relative_tokens[0][1][0], offset + relative_tokens[0][1][1])
    emitted.append(ShellToken(kind="path" if _is_path(head_token) else "identifier", text=head_token, span=command_span, role="command"))
    for token, token_span in relative_tokens[1:]:
        absolute_span = (offset + token_span[0], offset + token_span[1])
        stripped = token.strip("\"'")
        if not stripped:
            return None
        if stripped[-1] in ".!?":
            return None
        if token.startswith("-"):
            saw_marker = True
            expects_flag_value = True
            emitted.append(ShellToken(kind="shell_flag", text=stripped, span=absolute_span, role="flag"))
            continue
        if URL_PATTERN.fullmatch(stripped):
            saw_marker = True
            expects_flag_value = False
            emitted.append(ShellToken(kind="url", text=stripped, span=absolute_span, role="value"))
            continue
        if _is_path(stripped):
            saw_marker = True
            expects_flag_value = False
            emitted.append(ShellToken(kind="path", text=stripped, span=absolute_span, role="value"))
            continue
        if expects_flag_value:
            expects_flag_value = False
            emitted.append(ShellToken(kind="shell_value", text=stripped, span=absolute_span, role="value"))
            continue
        if not saw_marker:
            plain_before_marker += 1
            if plain_before_marker > 1:
                return None
            emitted.append(ShellToken(kind="shell_value", text=stripped, span=absolute_span, role="value"))
            continue
        if stripped.isupper() or any(char.isdigit() for char in stripped) or any(char in stripped for char in "/.:_=-"):
            emitted.append(ShellToken(kind="shell_value", text=stripped, span=absolute_span, role="value"))
            continue
        return None
    if not saw_marker:
        return None
    return emitted


def _strip_decorators(text: str) -> tuple[str, int]:
    offset = 0
    length = len(text)
    while offset < length and text[offset].isspace():
        offset += 1
    while offset < length:
        if text.startswith("> ", offset):
            offset += 2
            while offset < length and text[offset].isspace():
                offset += 1
            continue
        if offset + 1 < length and text[offset] in "-*+" and text[offset + 1].isspace():
            offset += 2
            while offset < length and text[offset].isspace():
                offset += 1
            continue
        break
    return text[offset:], offset


def _last_label_word(prefix: str) -> str | None:
    words = re.findall(r"[A-Za-z]+", prefix)
    if not words:
        return None
    return words[-1].lower()


def _is_snippet_intro_prefix(prefix: str) -> bool:
    normalized = " ".join(prefix.strip().split())
    if not normalized or len(normalized) > 40:
        return False
    if any(char in normalized for char in ".!?;`"):
        return False
    if len(normalized.split()) > 5:
        return False
    last_word = _last_label_word(normalized)
    return last_word in SNIPPET_LABEL_WORDS


def _is_shell_intro_prefix(prefix: str) -> bool:
    last_word = _last_label_word(prefix)
    return last_word in SHELL_LABEL_WORDS


def _whole_line_candidate(line_text: str, line_start: int, line_end: int) -> LiteralCandidate | None:
    bare_line = line_text.rstrip("\r\n")
    content, offset = _strip_decorators(bare_line)
    if not content.strip():
        return None
    stripped_text, stripped_span = _strip_span(content, (line_start + offset, line_start + len(bare_line)))
    return LiteralCandidate(
        text=stripped_text,
        char_span=stripped_span,
        cover_span=stripped_span,
        evidence="standalone_line",
        allow_shell=bool(PROMPT_PATTERN.match(stripped_text)),
    )


def _tail_candidate(line_text: str, line_start: int, line_end: int) -> LiteralCandidate | None:
    bare_line = line_text.rstrip("\r\n")
    content, offset = _strip_decorators(bare_line)
    colon_index = content.find(":")
    if colon_index <= 0:
        return None
    prefix = content[:colon_index]
    if not _is_snippet_intro_prefix(prefix):
        return None
    tail = content[colon_index + 1 :]
    stripped_text, stripped_span = _strip_span(tail, (line_start + offset + colon_index + 1, line_start + len(bare_line)))
    if not stripped_text:
        return None
    return LiteralCandidate(
        text=stripped_text,
        char_span=stripped_span,
        cover_span=stripped_span,
        evidence="snippet_tail",
        allow_shell=_is_shell_intro_prefix(prefix),
    )


def _literal_parent(
    candidate: LiteralCandidate,
    metadata: dict[str, Any],
    config: SegmentationConfig,
) -> ParentBlock | None:
    if not candidate.text.strip():
        return None
    combined_metadata = {**metadata, "segment_source": "heuristic", "evidence": candidate.evidence}
    order = ["json", "sql", "browser", "shell", "code"]
    if candidate.hint in order:
        order.remove(candidate.hint)
        order.insert(0, candidate.hint)
    for kind in order:
        if kind == "json" and config.enable_json_leaf_segmentation and _looks_like_json(candidate.text):
            return ParentBlock(kind="json", char_span=candidate.char_span, text=candidate.text, source="heuristic", metadata=combined_metadata)
        if kind == "sql" and config.enable_sql_segmentation and is_sql_statement(candidate.text):
            return ParentBlock(kind="sql", char_span=candidate.char_span, text=candidate.text, source="heuristic", metadata=combined_metadata)
        if kind == "browser" and config.enable_browser_dsl_segmentation and _parse_browser_invocation(candidate.text):
            return ParentBlock(kind="browser", char_span=candidate.char_span, text=candidate.text, source="heuristic", metadata=combined_metadata)
        if kind == "shell" and config.enable_code_segmentation and candidate.allow_shell and _parse_shell_command(candidate.text, allow_prompt=True):
            return ParentBlock(kind="shell", char_span=candidate.char_span, text=candidate.text, source="heuristic", metadata=combined_metadata)
        if kind == "code" and config.enable_code_segmentation and _looks_like_code_line(candidate.text):
            return ParentBlock(kind="code", char_span=candidate.char_span, text=candidate.text, source="heuristic", metadata=combined_metadata)
    return None


def _inline_code_candidates(text: str, span: tuple[int, int]) -> list[LiteralCandidate]:
    candidates: list[LiteralCandidate] = []
    for match in INLINE_CODE_PATTERN.finditer(text):
        inner_span = (span[0] + match.start(1), span[0] + match.end(1))
        candidates.append(
            LiteralCandidate(
                text=match.group(1),
                char_span=inner_span,
                cover_span=(span[0] + match.start(), span[0] + match.end()),
                evidence="inline_code",
                allow_shell=True,
            )
        )
    return candidates


def _sql_candidate_from_lines(lines: list[tuple[str, int, int]], index: int) -> tuple[ParentBlock | None, int]:
    line_text, line_start, line_end = lines[index]
    for start_candidate in (_tail_candidate(line_text, line_start, line_end), _whole_line_candidate(line_text, line_start, line_end)):
        if start_candidate is None:
            continue
        if sql_statement_head(start_candidate.text) is None:
            continue
        parts = [start_candidate.text]
        end = start_candidate.char_span[1]
        consumed = 1
        cursor = index + 1
        while cursor < len(lines):
            next_text, next_start, next_end = lines[cursor]
            stripped_text, stripped_span = _strip_span(next_text, (next_start, next_end))
            if not stripped_text or not is_sql_continuation(stripped_text):
                break
            parts.append(stripped_text)
            end = stripped_span[1]
            consumed += 1
            cursor += 1
        combined = "\n".join(parts)
        if not is_sql_statement(combined):
            continue
        return (
            ParentBlock(
                kind="sql",
                char_span=(start_candidate.char_span[0], end),
                text=combined,
                source="heuristic",
                metadata={"segment_source": "heuristic", "evidence": start_candidate.evidence},
            ),
            consumed,
        )
    return None, 0


def _line_candidates(text: str, base_start: int, config: SegmentationConfig) -> list[ParentBlock]:
    lines = _split_lines(text, base_start)
    if not lines:
        return []
    candidates: list[ParentBlock] = []
    index = 0
    while index < len(lines):
        if config.enable_sql_segmentation:
            sql_parent, consumed = _sql_candidate_from_lines(lines, index)
            if sql_parent is not None:
                candidates.append(sql_parent)
                index += consumed
                continue
        line_text, line_start, line_end = lines[index]
        for candidate in (_tail_candidate(line_text, line_start, line_end), _whole_line_candidate(line_text, line_start, line_end)):
            if candidate is None:
                continue
            parent = _literal_parent(candidate, {}, config)
            if parent is not None:
                candidates.append(parent)
                break
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
        if node.kind == "shell":
            self.segment_shell_node(node)
            return
        if node.kind == "code":
            self.segment_code_node(node)
            return
        if node.kind == "react_action_input":
            self.segment_react_action_input(node)
            return
        if node.kind == "react_action":
            self.process_text_region(node.text, node.char_span, fallback_kind="unknown_text", allow_react=False, metadata=node.metadata)
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
                    inner_span = (span[0] + match.start(2), span[0] + match.end(2))
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
                        language = match.group(1)
                        candidate = LiteralCandidate(
                            text=inner_text,
                            char_span=inner_span,
                            cover_span=inner_span,
                            evidence="fenced_code",
                            allow_shell=True,
                            hint=_fenced_kind(language),
                        )
                        parent = _literal_parent(candidate, {**metadata, "language": language.strip().lower()}, self.config)
                        if parent is not None:
                            self.process_node(parent)
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
        inline_code = _inline_code_candidates(text, span)
        if inline_code:
            cursor = span[0]
            for candidate in inline_code:
                if cursor < candidate.cover_span[0]:
                    self.process_text_region(
                        self.raw_text[cursor : candidate.cover_span[0]],
                        (cursor, candidate.cover_span[0]),
                        fallback_kind=fallback_kind,
                        allow_react=False,
                        metadata=metadata,
                    )
                parent = _literal_parent(candidate, metadata, self.config)
                if parent is not None:
                    self.process_node(parent)
                cursor = candidate.cover_span[1]
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
                self.process_node(
                    ParentBlock(
                        kind=candidate.kind,
                        char_span=candidate.char_span,
                        text=candidate.text,
                        source="heuristic",
                        metadata={**metadata, **candidate.metadata},
                    )
                )
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
        invocation = _parse_browser_invocation(node.text)
        if invocation is None:
            self.append_segment("unknown_text", node.text, node.char_span, dict(node.metadata))
            return
        command_span = (node.char_span[0] + invocation.command_span[0], node.char_span[0] + invocation.command_span[1])
        self.append_segment("browser_action", invocation.command, command_span, dict(node.metadata))
        for argument in invocation.arguments:
            value_span = (node.char_span[0] + argument.value_span[0], node.char_span[0] + argument.value_span[1])
            argument_metadata = dict(node.metadata)
            if argument.key is not None:
                argument_metadata["argument"] = argument.key
            self.append_segment(argument.kind, argument.value, value_span, argument_metadata)

    def segment_sql_node(self, node: ParentBlock) -> None:
        clauses = split_sql_clauses(node.text)
        if not clauses:
            self.append_segment("unknown_text", node.text, node.char_span, dict(node.metadata))
            return
        for clause_name, clause_text, start, end in clauses:
            self.append_segment("sql_clause", clause_text, (node.char_span[0] + start, node.char_span[0] + end), {**node.metadata, "clause": clause_name})

    def segment_code_node(self, node: ParentBlock) -> None:
        emitted = False
        for line, start, end in split_code_statements(node.text):
            self.append_segment("code_statement", line, (node.char_span[0] + start, node.char_span[0] + end), dict(node.metadata))
            emitted = True
        if not emitted:
            self.append_segment("unknown_text", node.text, node.char_span, dict(node.metadata))

    def segment_shell_node(self, node: ParentBlock) -> None:
        tokens = _parse_shell_command(node.text, allow_prompt=True)
        if tokens is None:
            self.append_segment("unknown_text", node.text, node.char_span, dict(node.metadata))
            return
        for token in tokens:
            self.append_segment(token.kind, token.text, (node.char_span[0] + token.span[0], node.char_span[0] + token.span[1]), {**node.metadata, "shell_role": token.role})

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
