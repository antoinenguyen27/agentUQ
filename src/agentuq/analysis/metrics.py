"""Shared metric computations for token logprob diagnostics."""

from __future__ import annotations

import math
from statistics import mean

from agentuq.schemas.records import TopToken


def surprises(logprobs: list[float]) -> list[float]:
    return [-value for value in logprobs]


def percentile(values: list[float], p: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, int(round((p / 100.0) * (len(ordered) - 1)))))
    return ordered[index]


def tail_mean(values: list[float], fraction: float = 0.1) -> float:
    if not values:
        return 0.0
    count = max(1, int(math.ceil(len(values) * fraction)))
    ordered = sorted(values, reverse=True)
    return mean(ordered[:count])


def max_run(flags: list[bool]) -> int:
    best = 0
    current = 0
    for flag in flags:
        if flag:
            current += 1
            best = max(best, current)
        else:
            current = 0
    return best


def truncated_entropy(top_tokens: list[TopToken], emitted_token: str | None = None, emitted_logprob: float | None = None) -> float | None:
    candidates = list(top_tokens)
    if emitted_token is not None and emitted_logprob is not None and all(item.token != emitted_token for item in candidates):
        candidates.append(TopToken(token=emitted_token, logprob=emitted_logprob))
    if not candidates:
        return None
    max_logprob = max(token.logprob for token in candidates)
    weights = [math.exp(token.logprob - max_logprob) for token in candidates]
    total = sum(weights)
    if total <= 0:
        return None
    probs = [weight / total for weight in weights]
    return -sum(prob * math.log(prob) for prob in probs if prob > 0)


def margin_log(top_tokens: list[TopToken]) -> float | None:
    if len(top_tokens) < 2:
        return None
    ordered = sorted(top_tokens, key=lambda item: item.logprob, reverse=True)
    return ordered[0].logprob - ordered[1].logprob


def emitted_rank(top_tokens: list[TopToken], emitted_token: str) -> tuple[int | None, bool]:
    if not top_tokens:
        return None, False
    ordered = sorted(top_tokens, key=lambda item: item.logprob, reverse=True)
    for index, item in enumerate(ordered, start=1):
        if item.token == emitted_token:
            return index, False
    return len(ordered) + 1, True

