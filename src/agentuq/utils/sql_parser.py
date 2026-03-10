"""Lightweight SQL statement recognition and clause splitting."""

from __future__ import annotations

import re


CLAUSE_PATTERN = re.compile(
    r"\b(SELECT|FROM|WHERE|JOIN|ORDER BY|GROUP BY|LIMIT|UPDATE|DELETE|INSERT INTO|VALUES|SET)\b",
    re.IGNORECASE,
)
STATEMENT_HEAD_PATTERN = re.compile(r"^\s*(SELECT|UPDATE|DELETE|INSERT\s+INTO)\b", re.IGNORECASE)
CONTINUATION_HEAD_PATTERN = re.compile(r"^\s*(FROM|WHERE|JOIN|ORDER\s+BY|GROUP\s+BY|LIMIT|SET|VALUES)\b", re.IGNORECASE)
NON_WHITESPACE_PATTERN = re.compile(r"\S")
IDENTIFIER_PATTERN = re.compile(r"[A-Za-z_][\w$]*")
QUALIFIED_IDENTIFIER_PATTERN = re.compile(r"[A-Za-z_][\w$]*(?:\.[A-Za-z_][\w$]*)*")
ALIASED_IDENTIFIER_PATTERN = re.compile(r"[A-Za-z_][\w$]*(?:\.[A-Za-z_][\w$]*)*\s+AS\s+[A-Za-z_][\w$]*", re.IGNORECASE)
SHORT_ALIAS_PATTERN = re.compile(r"[A-Za-z_][\w$]*(?:\.[A-Za-z_][\w$]*)*\s+[A-Za-z_][\w$]{0,3}")


def _mask_literals_and_comments(text: str) -> str:
    chars = list(text)
    index = 0
    length = len(chars)
    while index < length:
        if text.startswith("--", index):
            chars[index] = " "
            if index + 1 < length:
                chars[index + 1] = " "
            index += 2
            while index < length and text[index] not in "\r\n":
                chars[index] = " "
                index += 1
            continue
        if text.startswith("/*", index):
            chars[index] = " "
            if index + 1 < length:
                chars[index + 1] = " "
            index += 2
            while index < length and not text.startswith("*/", index):
                chars[index] = " "
                index += 1
            if index < length:
                chars[index] = " "
            if index + 1 < length:
                chars[index + 1] = " "
            index += 2
            continue
        if text[index] in {"'", '"'}:
            quote = text[index]
            chars[index] = " "
            index += 1
            while index < length:
                chars[index] = " "
                if text[index] == quote:
                    index += 1
                    if quote == "'" and index < length and text[index] == quote:
                        chars[index] = " "
                        index += 1
                        continue
                    break
                index += 1
            continue
        index += 1
    return "".join(chars)


def _clause_text(body: str, start: int, end: int) -> str:
    return body[start:end].strip()


def split_sql_clauses(text: str) -> list[tuple[str, str, int, int]]:
    masked = _mask_literals_and_comments(text)
    matches = list(CLAUSE_PATTERN.finditer(masked))
    if not matches:
        return []
    clauses: list[tuple[str, str, int, int]] = []
    for index, match in enumerate(matches):
        start = match.start()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        clause_name = match.group(1).upper()
        clause_text = _clause_text(text, start, end)
        if clause_text:
            clauses.append((clause_name, clause_text, start, end))
    return clauses


def sql_statement_head(text: str) -> str | None:
    masked = _mask_literals_and_comments(text)
    match = STATEMENT_HEAD_PATTERN.match(masked)
    if match is None:
        return None
    return re.sub(r"\s+", " ", match.group(1).upper())


def is_sql_continuation(text: str) -> bool:
    masked = _mask_literals_and_comments(text)
    return bool(CONTINUATION_HEAD_PATTERN.match(masked))


def _has_body(clause_text: str, keyword: str) -> bool:
    body = clause_text[len(keyword) :].strip()
    return bool(body)


def _has_non_comment_content(text: str) -> bool:
    masked = _mask_literals_and_comments(text)
    return NON_WHITESPACE_PATTERN.search(masked) is not None


def _projection_is_valid(clause_text: str) -> bool:
    body = " ".join(clause_text[len("SELECT") :].split())
    if not body:
        return False
    if body == "*":
        return True
    if body.upper().startswith("DISTINCT "):
        body = body[9:].strip()
    if not body:
        return False
    if any(char in body for char in ",().`\"[]"):
        return True
    if QUALIFIED_IDENTIFIER_PATTERN.fullmatch(body):
        return True
    if ALIASED_IDENTIFIER_PATTERN.fullmatch(body):
        return True
    if re.fullmatch(r"\d+(?:\.\d+)?", body):
        return True
    return False


def _table_ref_is_valid(body: str) -> bool:
    normalized = " ".join(body.split())
    if not normalized:
        return False
    normalized = normalized.rstrip(";")
    if "(" in normalized:
        normalized = normalized.split("(", 1)[0].strip()
    if not normalized:
        return False
    if QUALIFIED_IDENTIFIER_PATTERN.fullmatch(normalized):
        return True
    if ALIASED_IDENTIFIER_PATTERN.fullmatch(normalized):
        return True
    if SHORT_ALIAS_PATTERN.fullmatch(normalized):
        return True
    return False


def is_sql_statement(text: str) -> bool:
    clauses = split_sql_clauses(text.strip())
    if not clauses:
        return False
    statement_type = clauses[0][0]
    clause_map = {name: clause for name, clause, _start, _end in clauses}

    if statement_type == "SELECT":
        if "FROM" not in clause_map:
            return False
        return _projection_is_valid(clause_map["SELECT"]) and _table_ref_is_valid(clause_map["FROM"][len("FROM") :])
    if statement_type == "UPDATE":
        if "SET" not in clause_map:
            return False
        return _table_ref_is_valid(clause_map["UPDATE"][len("UPDATE") :]) and _has_body(clause_map["SET"], "SET")
    if statement_type == "DELETE":
        if len(clauses) < 2 or clauses[1][0] != "FROM":
            return False
        return _table_ref_is_valid(clauses[1][1][len("FROM") :])
    if statement_type == "INSERT INTO":
        if not _table_ref_is_valid(clauses[0][1][len("INSERT INTO") :]):
            return False
        if "VALUES" in clause_map:
            return _has_non_comment_content(clause_map["VALUES"][len("VALUES") :])
        if any(name == "SELECT" for name, _clause, _start, _end in clauses[1:]):
            return True
        return False
    return False
