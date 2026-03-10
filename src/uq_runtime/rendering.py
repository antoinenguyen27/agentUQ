"""Human-readable rendering helpers for UQ results."""

from __future__ import annotations

from typing import Literal

from uq_runtime.schemas.results import Action, Event, SegmentResult, UQResult

Verbosity = Literal["compact", "summary", "debug"]
ThresholdDisplay = Literal["none", "triggered", "all"]


def _fmt(value: float | None) -> str:
    if value is None:
        return "n/a"
    if value == float("inf"):
        return "inf"
    return f"{value:.3f}"


def _preview(text: str, width: int = 72) -> str:
    collapsed = " ".join((text or "").split())
    if not collapsed:
        return "<empty>"
    if len(collapsed) <= width:
        return collapsed
    return f"{collapsed[: width - 3]}..."


def _capability_summary(result: UQResult) -> str:
    level = result.capability_level.value
    report = result.capability_report
    notes: list[str] = []
    if level == "selected_only" and not report.topk_logprobs:
        notes.append("top-k unavailable; entropy/rank diagnostics degraded")
    if level == "none":
        notes.append("no usable token logprobs")
    if report.degraded_reason:
        notes.append(report.degraded_reason)
    if not notes:
        return level
    return f"{level} ({'; '.join(notes)})"


def _action_rank(action: Action) -> int:
    order = {
        Action.CONTINUE: 0,
        Action.CONTINUE_WITH_ANNOTATION: 1,
        Action.REGENERATE_SEGMENT: 2,
        Action.RETRY_STEP: 3,
        Action.RETRY_STEP_WITH_CONSTRAINTS: 4,
        Action.DRY_RUN_VERIFY: 5,
        Action.ASK_USER_CONFIRMATION: 6,
        Action.BLOCK_EXECUTION: 7,
        Action.ESCALATE_TO_HUMAN: 8,
        Action.EMIT_WEBHOOK: 9,
        Action.CUSTOM: 10,
    }
    return order[action]


def _top_risk_segments(result: UQResult) -> list[SegmentResult]:
    if not result.segments:
        return []
    max_rank = max(_action_rank(segment.recommended_action) for segment in result.segments)
    risky = [segment for segment in result.segments if _action_rank(segment.recommended_action) == max_rank]
    return sorted(risky, key=lambda segment: (_action_rank(segment.recommended_action), len(segment.events), segment.metrics.max_surprise), reverse=True)


def _risk_driver_label(result: UQResult) -> str:
    drivers = [segment for segment in _top_risk_segments(result) if segment.recommended_action == result.action]
    if not drivers:
        return "none"
    if all(segment.priority in {"informational", "low_priority"} for segment in drivers):
        return "informational_only"
    return "action_bearing"


def _risk_basis(result: UQResult) -> str:
    drivers = [segment for segment in _top_risk_segments(result) if segment.recommended_action == result.action]
    if not drivers:
        return "none"
    return ", ".join(f"{segment.id}:{segment.kind}" for segment in drivers)


def _event_detail(_segment: SegmentResult, event: Event, _result: UQResult) -> str | None:
    details = event.details or {}
    if event.type == "LOW_MARGIN_CLUSTER":
        return (
            f"low_margin_run_max={details.get('low_margin_run_max')} >= min_run={details.get('min_run')}; "
            f"low_margin_rate={_fmt(details.get('low_margin_rate'))} threshold={_fmt(details.get('threshold'))}"
        )
    if event.type == "HIGH_ENTROPY_CLUSTER":
        return (
            f"high_entropy_run_max={details.get('high_entropy_run_max')} >= min_run={details.get('min_run')}; "
            f"high_entropy_rate={_fmt(details.get('high_entropy_rate'))} threshold={_fmt(details.get('threshold'))}"
        )
    if event.type == "LOW_PROB_SPIKE":
        return f"max_surprise={_fmt(details.get('max_surprise'))} >= spike_surprise={_fmt(details.get('threshold'))}"
    if event.type == "TAIL_RISK_HEAVY":
        return f"tail_surprise_mean={_fmt(details.get('tail_surprise_mean'))} >= tail_surprise={_fmt(details.get('threshold'))}"
    if event.type == "OFF_TOP1_BURST":
        if details.get("trigger") == "off_top1_run":
            return f"off_top1_run_max={details.get('off_top1_run_max')} >= min_run={details.get('min_run')}"
        return f"off_top1_rate={_fmt(details.get('off_top1_rate'))} >= off_top1_rate={_fmt(details.get('threshold'))}"
    if event.type == "ACTION_HEAD_UNCERTAIN":
        reasons: list[str] = []
        triggers = details.get("trigger", [])
        if "mean_margin_log" in triggers:
            reasons.append(
                f"mean_margin_log={_fmt(details.get('mean_margin_log'))} < low_margin_log={_fmt(details.get('low_margin_threshold'))}"
            )
        if "avg_surprise" in triggers:
            reasons.append(
                f"avg_surprise={_fmt(details.get('avg_surprise'))} > action_head_surprise={_fmt(details.get('action_head_surprise'))}"
            )
        return " and ".join(reasons) if reasons else None
    if event.type == "ARGUMENT_VALUE_UNCERTAIN":
        reasons = []
        triggers = details.get("trigger", [])
        if "avg_surprise" in triggers:
            reasons.append(
                f"avg_surprise={_fmt(details.get('avg_surprise'))} >= action_head_surprise={_fmt(details.get('action_head_surprise'))}"
            )
        if "max_surprise" in triggers:
            reasons.append(
                f"max_surprise={_fmt(details.get('max_surprise'))} >= spike_surprise={_fmt(details.get('spike_surprise'))}"
            )
        return " and ".join(reasons) if reasons else None
    return None


def _interesting_segments(result: UQResult) -> list[SegmentResult]:
    interesting = [
        segment
        for segment in result.segments
        if segment.events or segment.recommended_action != Action.CONTINUE
    ]
    if interesting:
        return interesting
    for segment in result.segments:
        if segment.kind == "final_answer_text":
            return [segment]
    return result.segments[:1]


def _global_events(result: UQResult) -> list[Event]:
    return [event for event in result.events if event.segment_id is None]


def _debug_metric_summary(segment: SegmentResult) -> str:
    metrics = segment.metrics
    values = [
        ("score", segment.primary_score),
        ("tokens", metrics.token_count),
        ("nll", metrics.nll),
        ("avg_surprise", metrics.avg_surprise),
        ("max_surprise", metrics.max_surprise),
        ("p95_surprise", metrics.p95_surprise),
        ("tail_surprise_mean", metrics.tail_surprise_mean),
        ("mean_margin_log", metrics.mean_margin_log),
        ("min_margin_log", metrics.min_margin_log),
        ("low_margin_rate", metrics.low_margin_rate),
        ("low_margin_run_max", metrics.low_margin_run_max),
        ("mean_entropy_hat", metrics.mean_entropy_hat),
        ("max_entropy_hat", metrics.max_entropy_hat),
        ("high_entropy_rate", metrics.high_entropy_rate),
        ("high_entropy_run_max", metrics.high_entropy_run_max),
        ("off_top1_rate", metrics.off_top1_rate),
        ("off_topk_rate", metrics.off_topk_rate),
        ("off_top1_run_max", metrics.off_top1_run_max),
        ("any_off_topk", metrics.any_off_topk),
    ]
    rendered: list[str] = []
    for name, value in values:
        if value is None:
            continue
        if isinstance(value, bool):
            rendered.append(f"{name}={str(value).lower()}")
        elif isinstance(value, int):
            rendered.append(f"{name}={value}")
        else:
            rendered.append(f"{name}={_fmt(float(value))}")
    return " ".join(rendered)


def _threshold_summary(segment: SegmentResult, result: UQResult) -> str | None:
    thresholds = result.resolved_thresholds
    if thresholds is None:
        return None
    priority = segment.priority
    return (
        " ".join(
            [
                f"low_margin_log={_fmt(thresholds.low_margin_log[priority])}",
                f"entropy={_fmt(thresholds.entropy[priority])}",
                f"spike_surprise={_fmt(thresholds.spike_surprise[priority])}",
                f"tail_surprise={_fmt(thresholds.tail_surprise[priority])}",
                f"off_top1_rate={_fmt(thresholds.off_top1_rate[priority])}",
                f"action_head_surprise={_fmt(thresholds.action_head_surprise[priority])}",
                f"min_run={thresholds.min_run}",
            ]
        )
    )


def _render_summary(lines: list[str], result: UQResult, verbosity: Verbosity) -> None:
    top_risk = _top_risk_segments(result)
    lines.append("Summary")
    lines.append(f"  mode: {result.mode}")
    if result.diagnostics.mode_reason:
        lines.append(f"  reason: {result.diagnostics.mode_reason}")
    lines.append(f"  aggregate_primary_score: {_fmt(result.primary_score)} {result.primary_score_type.value}")
    lines.append("  score_note: aggregate over full emitted path; compare segments for operational risk")
    lines.append(f"  action: {result.action.value}")
    if top_risk:
        lines.append(f"  top_risk: {top_risk[0].kind} [{top_risk[0].priority}] -> {top_risk[0].recommended_action.value}")
    lines.append(f"  action_driver: {_risk_driver_label(result)}")
    lines.append(f"  risk_basis: {_risk_basis(result)}")
    if result.decision is not None:
        lines.append(f"  rationale: {result.decision.rationale}")
    lines.append(f"  capability: {_capability_summary(result)}")
    if verbosity == "debug":
        report = result.capability_report
        lines.append(
            "  capability_details: "
            f"selected_token_logprobs={str(report.selected_token_logprobs).lower()} "
            f"topk_logprobs={str(report.topk_logprobs).lower()} "
            f"topk_k={report.topk_k if report.topk_k is not None else 'n/a'} "
            f"structured_blocks={str(report.structured_blocks).lower()} "
            f"function_call_structure={str(report.function_call_structure).lower()}"
        )
        lines.append(f"  tokens: {result.diagnostics.token_count}")
    if result.diagnostics.warnings:
        lines.append(f"  warnings: {'; '.join(result.diagnostics.warnings)}")


def _render_global_events(lines: list[str], result: UQResult) -> None:
    global_events = _global_events(result)
    if not global_events:
        return
    lines.append("")
    lines.append("Events")
    for event in global_events:
        lines.append(f"  - {event.type} [{event.severity.value}]: {event.message}")


def _render_compact_segments(lines: list[str], result: UQResult) -> None:
    if result.action == Action.CONTINUE and not result.diagnostics.warnings and not result.events:
        return
    segments = _interesting_segments(result)
    if not segments:
        return
    lines.append("")
    lines.append("Highlights")
    for segment in _top_risk_segments(result) or segments:
        event_types = ", ".join(event.type for event in segment.events) or "none"
        lines.append(
            f"  {segment.kind} [{segment.priority}] -> {segment.recommended_action.value} "
            f"(events: {event_types})"
        )


def _render_segments(lines: list[str], result: UQResult, verbosity: Verbosity, show_thresholds: ThresholdDisplay) -> None:
    segments = result.segments if verbosity == "debug" else _interesting_segments(result)
    if not segments:
        return
    lines.append("")
    lines.append("Segments")
    for segment in segments:
        lines.append(f"  {segment.kind} [{segment.priority}] -> {segment.recommended_action.value}")
        lines.append(f"    text: {_preview(segment.text)}")
        if verbosity == "debug":
            lines.append(f"    metrics: {_debug_metric_summary(segment)}")
        else:
            lines.append(
                "    metrics: "
                f"score={_fmt(segment.primary_score)} "
                f"avg_surprise={_fmt(segment.metrics.avg_surprise)} "
                f"max_surprise={_fmt(segment.metrics.max_surprise)} "
                f"mean_entropy={_fmt(segment.metrics.mean_entropy_hat)}"
            )
        if verbosity == "debug" and show_thresholds == "all":
            threshold_summary = _threshold_summary(segment, result)
            if threshold_summary is not None:
                lines.append(f"    thresholds: {threshold_summary}")
        if segment.events:
            lines.append("    events:")
            for event in segment.events:
                detail = _event_detail(segment, event, result) if show_thresholds != "none" else None
                suffix = f" ({detail})" if detail is not None and show_thresholds in {"triggered", "all"} else ""
                lines.append(f"      - {event.type} [{event.severity.value}]: {event.message}{suffix}")
        else:
            lines.append("    events: none")


def render_result(
    result: UQResult,
    verbosity: Verbosity = "summary",
    show_thresholds: ThresholdDisplay = "triggered",
) -> str:
    if verbosity not in {"compact", "summary", "debug"}:
        raise ValueError(f"Unsupported verbosity: {verbosity}")
    if show_thresholds not in {"none", "triggered", "all"}:
        raise ValueError(f"Unsupported show_thresholds: {show_thresholds}")

    lines: list[str] = []
    _render_summary(lines, result, verbosity)
    _render_global_events(lines, result)
    if verbosity == "compact":
        _render_compact_segments(lines, result)
    else:
        _render_segments(lines, result, verbosity, show_thresholds)
    return "\n".join(lines)
