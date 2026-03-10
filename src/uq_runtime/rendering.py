"""Human-readable rendering helpers for UQ results."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from uq_runtime.schemas.results import Action, Event, SegmentResult, UQResult

Verbosity = Literal["compact", "summary", "debug"]
ThresholdDisplay = Literal["none", "triggered", "all"]

SEGMENT_LABELS = {
    "tool_name": "tool name",
    "browser_action": "browser action",
    "browser_selector": "browser selector",
    "url": "URL",
    "identifier": "identifier",
    "path": "path",
    "sql_clause": "SQL clause",
    "shell_flag": "shell flag",
    "shell_value": "shell value",
    "tool_arguments_raw": "tool arguments",
    "tool_argument_leaf": "tool argument value",
    "json_leaf": "JSON value",
    "browser_text_value": "browser text value",
    "code_statement": "code statement",
    "final_answer_text": "final answer",
    "reasoning_text": "reasoning text",
    "unknown_text": "plain text",
}

EVENT_SUBTITLES = {
    "LOW_MARGIN_CLUSTER": "candidate separation stays weak across a token run",
    "HIGH_ENTROPY_CLUSTER": "token distribution stays diffuse across a token run",
    "LOW_PROB_SPIKE": "one token or field is highly improbable",
    "TAIL_RISK_HEAVY": "multiple unusually improbable tokens accumulate in this span",
    "OFF_TOP1_BURST": "realized path repeatedly diverges from local top-1",
    "OFF_TOPK_TOKEN": "emitted token falls outside returned top-k candidates",
    "ACTION_HEAD_UNCERTAIN": "action choice looks unstable",
    "ARGUMENT_VALUE_UNCERTAIN": "argument value looks brittle",
    "SCHEMA_INVALID": "structured output failed validation",
    "TEMPERATURE_MISMATCH": "canonical scoring had to downgrade to realized mode",
    "MISSING_TOPK": "top-k diagnostics unavailable",
    "MISSING_LOGPROBS": "token logprobs unavailable",
}

ACTION_LABELS = {
    Action.CONTINUE: "Continue",
    Action.CONTINUE_WITH_ANNOTATION: "Continue with annotation",
    Action.REGENERATE_SEGMENT: "Regenerate segment",
    Action.RETRY_STEP: "Retry step",
    Action.RETRY_STEP_WITH_CONSTRAINTS: "Retry step with constraints",
    Action.DRY_RUN_VERIFY: "Dry-run verify",
    Action.ASK_USER_CONFIRMATION: "Ask user confirmation",
    Action.BLOCK_EXECUTION: "Block execution",
    Action.ESCALATE_TO_HUMAN: "Escalate to human",
    Action.EMIT_WEBHOOK: "Emit webhook",
    Action.CUSTOM: "Custom action",
}

SEVERITY_LABELS = {
    "info": "info",
    "warn": "warn",
    "high": "high",
    "critical": "critical",
}


@dataclass
class DisplayEvent:
    code: str
    subtitle: str
    severity: str
    message: str
    detail: str | None = None


@dataclass
class DisplaySegment:
    id: str
    kind: str
    label: str
    priority: str
    recommended_action: str
    text_preview: str
    metrics_summary: str
    metrics_groups: list[tuple[str, str]]
    thresholds: str | None
    events: list[DisplayEvent]


@dataclass
class DisplayModel:
    headline: list[tuple[str, str]]
    capability_gaps: list[str]
    risk_summary: list[tuple[str, str]]
    technical_details: list[tuple[str, str]]
    global_events: list[DisplayEvent]
    highlight_segments: list[DisplaySegment]
    segments: list[DisplaySegment]
    quiet: bool


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


def _friendly_segment_label(kind: str) -> str:
    return SEGMENT_LABELS.get(kind, kind.replace("_", " "))


def _friendly_event_subtitle(event_type: str) -> str:
    return EVENT_SUBTITLES.get(event_type, event_type.replace("_", " ").lower())


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
    return sorted(
        risky,
        key=lambda segment: (_action_rank(segment.recommended_action), len(segment.events), segment.metrics.max_surprise),
        reverse=True,
    )


def _risk_driver_label(result: UQResult) -> str:
    drivers = [segment for segment in _top_risk_segments(result) if segment.recommended_action == result.action]
    if not drivers:
        return "none"
    if all(segment.priority in {"informational", "low_priority"} for segment in drivers):
        return "informational prose only"
    return "action-bearing segment(s)"


def _risk_drivers(result: UQResult) -> str:
    drivers = [segment for segment in _top_risk_segments(result) if segment.recommended_action == result.action]
    if not drivers:
        return "none"
    return ", ".join(f"{_friendly_segment_label(segment.kind)} ({segment.id})" for segment in drivers)


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
        reasons: list[str] = []
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
        segment for segment in result.segments if segment.events or segment.recommended_action != Action.CONTINUE
    ]
    if interesting:
        return interesting
    for segment in result.segments:
        if segment.kind == "final_answer_text":
            return [segment]
    return result.segments[:1]


def _global_events(result: UQResult) -> list[Event]:
    return [event for event in result.events if event.segment_id is None]


def _threshold_summary(segment: SegmentResult, result: UQResult) -> str | None:
    thresholds = result.resolved_thresholds
    if thresholds is None:
        return None
    priority = segment.priority
    return " ".join(
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


def _grouped_metrics(segment: SegmentResult) -> list[tuple[str, str]]:
    metrics = segment.metrics
    groups = [
        (
            "surprise",
            " ".join(
                [
                    f"score={_fmt(segment.primary_score)}",
                    f"nll={_fmt(metrics.nll)}",
                    f"avg={_fmt(metrics.avg_surprise)}",
                    f"p95={_fmt(metrics.p95_surprise)}",
                    f"max={_fmt(metrics.max_surprise)}",
                    f"tail={_fmt(metrics.tail_surprise_mean)}",
                ]
            ),
        ),
        (
            "margin",
            " ".join(
                [
                    f"mean={_fmt(metrics.mean_margin_log)}",
                    f"min={_fmt(metrics.min_margin_log)}",
                    f"low_margin_rate={_fmt(metrics.low_margin_rate)}",
                    f"low_margin_run_max={metrics.low_margin_run_max if metrics.low_margin_run_max is not None else 'n/a'}",
                ]
            ),
        ),
        (
            "entropy",
            " ".join(
                [
                    f"mean={_fmt(metrics.mean_entropy_hat)}",
                    f"max={_fmt(metrics.max_entropy_hat)}",
                    f"high_entropy_rate={_fmt(metrics.high_entropy_rate)}",
                    f"high_entropy_run_max={metrics.high_entropy_run_max if metrics.high_entropy_run_max is not None else 'n/a'}",
                ]
            ),
        ),
        (
            "rank",
            " ".join(
                [
                    f"off_top1_rate={_fmt(metrics.off_top1_rate)}",
                    f"off_topk_rate={_fmt(metrics.off_topk_rate)}",
                    f"off_top1_run_max={metrics.off_top1_run_max if metrics.off_top1_run_max is not None else 'n/a'}",
                    f"any_off_topk={str(metrics.any_off_topk).lower()}",
                ]
            ),
        ),
    ]
    return groups


def _summary_metrics(segment: SegmentResult) -> str:
    return " ".join(
        [
            f"score={_fmt(segment.primary_score)}",
            f"avg_surprise={_fmt(segment.metrics.avg_surprise)}",
            f"max_surprise={_fmt(segment.metrics.max_surprise)}",
            f"mean_entropy={_fmt(segment.metrics.mean_entropy_hat)}",
        ]
    )


def _display_event(segment: SegmentResult, event: Event, result: UQResult, show_thresholds: ThresholdDisplay) -> DisplayEvent:
    detail = _event_detail(segment, event, result) if show_thresholds != "none" else None
    return DisplayEvent(
        code=event.type,
        subtitle=_friendly_event_subtitle(event.type),
        severity=SEVERITY_LABELS[event.severity.value],
        message=event.message,
        detail=detail if show_thresholds in {"triggered", "all"} else None,
    )


def _display_segment(segment: SegmentResult, result: UQResult, show_thresholds: ThresholdDisplay) -> DisplaySegment:
    return DisplaySegment(
        id=segment.id,
        kind=segment.kind,
        label=_friendly_segment_label(segment.kind),
        priority=segment.priority,
        recommended_action=ACTION_LABELS[segment.recommended_action],
        text_preview=_preview(segment.text),
        metrics_summary=_summary_metrics(segment),
        metrics_groups=_grouped_metrics(segment),
        thresholds=_threshold_summary(segment, result),
        events=[_display_event(segment, event, result, show_thresholds) for event in segment.events],
    )


def build_display_model(
    result: UQResult,
    verbosity: Verbosity = "summary",
    show_thresholds: ThresholdDisplay = "triggered",
) -> DisplayModel:
    if verbosity not in {"compact", "summary", "debug"}:
        raise ValueError(f"Unsupported verbosity: {verbosity}")
    if show_thresholds not in {"none", "triggered", "all"}:
        raise ValueError(f"Unsupported show_thresholds: {show_thresholds}")

    top_risk = _top_risk_segments(result)
    headline = [
        ("recommended_action", ACTION_LABELS[result.action]),
        ("rationale", result.decision.rationale if result.decision is not None else "No decision rationale available."),
        ("mode", result.mode),
        ("whole_response_score", f"{_fmt(result.primary_score)} {result.primary_score_type.value}"),
        ("whole_response_score_note", "Summarizes the full emitted path; it does not determine the recommended action by itself."),
        ("capability", result.capability_level.value),
    ]
    capability_gaps: list[str] = []
    if result.capability_level.value == "selected_only":
        capability_gaps.append("Selected-token logprobs are available, but top-k diagnostics are unavailable.")
    if result.capability_level.value == "none":
        capability_gaps.append("No usable token logprobs were returned.")
    if result.capability_report.degraded_reason:
        capability_gaps.append(result.capability_report.degraded_reason)
    capability_gaps.extend(result.diagnostics.warnings)

    global_display_events = [
        DisplayEvent(
            code=event.type,
            subtitle=_friendly_event_subtitle(event.type),
            severity=SEVERITY_LABELS[event.severity.value],
            message=event.message,
            detail=None,
        )
        for event in _global_events(result)
    ]
    for event in global_display_events:
        capability_gaps.append(f"{event.code}: {event.subtitle}. {event.message}")

    risk_summary = [
        (
            "decision_driving_segment",
            (
                f"{_friendly_segment_label(top_risk[0].kind)} [{top_risk[0].priority}] -> "
                f"{ACTION_LABELS[top_risk[0].recommended_action]}"
            )
            if top_risk
            else "none"
        ),
        ("decision_driver_type", _risk_driver_label(result)),
        ("decision_driving_segments", _risk_drivers(result)),
        ("decision_note", "The recommended action comes from the segment events and policy mapping in this section."),
    ]

    technical_details: list[tuple[str, str]] = []
    if verbosity == "debug":
        report = result.capability_report
        technical_details.extend(
            [
                (
                    "capability_details",
                    " ".join(
                        [
                            f"selected_token_logprobs={str(report.selected_token_logprobs).lower()}",
                            f"topk_logprobs={str(report.topk_logprobs).lower()}",
                            f"topk_k={report.topk_k if report.topk_k is not None else 'n/a'}",
                            f"structured_blocks={str(report.structured_blocks).lower()}",
                            f"function_call_structure={str(report.function_call_structure).lower()}",
                        ]
                    ),
                ),
                ("tokens", str(result.diagnostics.token_count)),
            ]
        )

    quiet = result.action == Action.CONTINUE and not capability_gaps and not result.events
    highlight_segments = [_display_segment(segment, result, show_thresholds) for segment in (_top_risk_segments(result) or _interesting_segments(result))]
    segments_source = result.segments if verbosity == "debug" else _interesting_segments(result)
    segments = [_display_segment(segment, result, show_thresholds) for segment in segments_source]

    return DisplayModel(
        headline=headline,
        capability_gaps=capability_gaps,
        risk_summary=risk_summary,
        technical_details=technical_details,
        global_events=global_display_events,
        highlight_segments=highlight_segments,
        segments=segments,
        quiet=quiet,
    )


def _append_key_values(lines: list[str], title: str, items: list[tuple[str, str]]) -> None:
    if not items:
        return
    lines.append(title)
    for key, value in items:
        lines.append(f"  {key}: {value}")


def _append_capability_gaps(lines: list[str], model: DisplayModel) -> None:
    if not model.capability_gaps:
        return
    lines.append("")
    lines.append("Capability Gaps")
    for entry in model.capability_gaps:
        lines.append(f"  - {entry}")


def _append_segments(lines: list[str], model: DisplayModel, verbosity: Verbosity, show_thresholds: ThresholdDisplay) -> None:
    if not model.segments:
        return
    lines.append("")
    lines.append("Segments")
    for segment in model.segments:
        lines.append(f"  {segment.label} [{segment.priority}] -> {segment.recommended_action}")
        if verbosity == "debug":
            lines.append(f"    debug_kind: {segment.kind} id={segment.id}")
        lines.append(f"    text: {segment.text_preview}")
        if verbosity == "debug":
            for group_name, values in segment.metrics_groups:
                lines.append(f"    {group_name}: {values}")
        else:
            lines.append(f"    metrics: {segment.metrics_summary}")
        if verbosity == "debug" and show_thresholds == "all" and segment.thresholds is not None:
            lines.append(f"    thresholds: {segment.thresholds}")
        if segment.events:
            lines.append("    events:")
            for event in segment.events:
                friendly = f"{event.subtitle} [{event.severity}]"
                raw = f"code={event.code}" if verbosity == "debug" else event.code
                detail = f" ({event.detail})" if event.detail is not None else ""
                lines.append(f"      - {friendly}; {raw}: {event.message}{detail}")
        else:
            lines.append("    events: none")


def render_result(
    result: UQResult,
    verbosity: Verbosity = "summary",
    show_thresholds: ThresholdDisplay = "triggered",
) -> str:
    model = build_display_model(result, verbosity=verbosity, show_thresholds=show_thresholds)
    lines: list[str] = []
    _append_key_values(lines, "Summary", model.headline)
    _append_capability_gaps(lines, model)
    if verbosity != "compact":
        lines.append("")
        _append_key_values(lines, "Risk Summary", model.risk_summary)
    elif not model.quiet and model.highlight_segments:
        lines.append("")
        lines.append("Highlights")
        for segment in model.highlight_segments:
            event_types = ", ".join(event.code for event in segment.events) or "none"
            lines.append(
                f"  {segment.label} [{segment.priority}] -> {segment.recommended_action} "
                f"(events: {event_types})"
            )
    if verbosity == "debug" and model.technical_details:
        lines.append("")
        _append_key_values(lines, "Technical Details", model.technical_details)
    if verbosity != "compact":
        _append_segments(lines, model, verbosity, show_thresholds)
    return "\n".join(lines)


def _require_rich() -> dict[str, Any]:
    try:
        from rich.console import Console, Group
        from rich.panel import Panel
        from rich.table import Table
        from rich.text import Text
    except ImportError as exc:
        raise RuntimeError("Rich rendering requires the optional dependency `rich`. Install it with `pip install agentuq[rich]`.") from exc
    return {
        "Console": Console,
        "Group": Group,
        "Panel": Panel,
        "Table": Table,
        "Text": Text,
    }


def render_result_rich(
    result: UQResult,
    verbosity: Verbosity = "summary",
    show_thresholds: ThresholdDisplay = "triggered",
) -> Any:
    rich_mod = _require_rich()
    Group = rich_mod["Group"]
    Panel = rich_mod["Panel"]
    Table = rich_mod["Table"]
    Text = rich_mod["Text"]

    model = build_display_model(result, verbosity=verbosity, show_thresholds=show_thresholds)
    blocks: list[Any] = []

    headline = Table.grid(padding=(0, 2))
    headline.expand = True
    headline.add_column(style="bold cyan", ratio=1)
    headline.add_column(ratio=4)
    for key, value in model.headline:
        headline.add_row(key.replace("_", " "), value)
    blocks.append(Panel(headline, title="Summary", border_style="cyan"))

    if model.capability_gaps:
        gaps = Table.grid(padding=(0, 1))
        gaps.add_column()
        for entry in model.capability_gaps:
            gaps.add_row(f"- {entry}")
        blocks.append(Panel(gaps, title="Capability Gaps", border_style="yellow"))

    if verbosity != "compact":
        risk = Table.grid(padding=(0, 2))
        risk.add_column(style="bold magenta", ratio=1)
        risk.add_column(ratio=4)
        for key, value in model.risk_summary:
            risk.add_row(key.replace("_", " "), value)
        blocks.append(Panel(risk, title="Risk Summary", border_style="magenta"))

    if verbosity == "compact" and not model.quiet and model.highlight_segments:
        highlights = Table(show_header=True, header_style="bold")
        highlights.add_column("Segment")
        highlights.add_column("Priority")
        highlights.add_column("Action")
        highlights.add_column("Events")
        for segment in model.highlight_segments:
            highlights.add_row(
                segment.label,
                segment.priority,
                segment.recommended_action,
                ", ".join(event.code for event in segment.events) or "none",
            )
        blocks.append(Panel(highlights, title="Highlights", border_style="green"))

    if verbosity == "debug" and model.technical_details:
        technical = Table.grid(padding=(0, 2))
        technical.add_column(style="bold white", ratio=1)
        technical.add_column(ratio=4)
        for key, value in model.technical_details:
            technical.add_row(key.replace("_", " "), value)
        blocks.append(Panel(technical, title="Technical Details", border_style="white"))

    if verbosity != "compact" and model.segments:
        segment_blocks: list[Any] = []
        for segment in model.segments:
            segment_table = Table.grid(padding=(0, 2))
            segment_table.add_column(style="bold green", ratio=1)
            segment_table.add_column(ratio=5)
            segment_table.add_row("label", f"{segment.label} [{segment.priority}]")
            segment_table.add_row("action", segment.recommended_action)
            if verbosity == "debug":
                segment_table.add_row("debug", f"{segment.kind} id={segment.id}")
            segment_table.add_row("text", segment.text_preview)
            if verbosity == "debug":
                for group_name, values in segment.metrics_groups:
                    segment_table.add_row(group_name, values)
            else:
                segment_table.add_row("metrics", segment.metrics_summary)
            if verbosity == "debug" and show_thresholds == "all" and segment.thresholds is not None:
                segment_table.add_row("thresholds", segment.thresholds)
            if segment.events:
                for index, event in enumerate(segment.events, start=1):
                    event_text = Text()
                    event_text.append(f"{event.subtitle} [{event.severity}] ", style="bold")
                    event_text.append(f"code={event.code}: {event.message}")
                    if event.detail is not None:
                        event_text.append(f" ({event.detail})", style="dim")
                    segment_table.add_row(f"event {index}", event_text)
            else:
                segment_table.add_row("events", "none")
            segment_blocks.append(Panel(segment_table, title=segment.label, border_style="blue"))
        blocks.append(Panel(Group(*segment_blocks), title="Segments", border_style="blue"))

    return Group(*blocks)


def print_result_rich(
    result: UQResult,
    console: Any | None = None,
    verbosity: Verbosity = "summary",
    show_thresholds: ThresholdDisplay = "triggered",
) -> None:
    rich_mod = _require_rich()
    Console = rich_mod["Console"]
    target = console or Console()
    target.print(render_result_rich(result, verbosity=verbosity, show_thresholds=show_thresholds))
