"""Event engine."""

from __future__ import annotations

from agentuq.schemas.config import ThresholdConfig
from agentuq.schemas.results import Event, EventSeverity, SegmentResult


def _severity(event_type: str, priority: str) -> EventSeverity:
    if priority == "critical_action":
        return EventSeverity.CRITICAL if event_type in {"SCHEMA_INVALID", "ACTION_HEAD_UNCERTAIN", "LOW_PROB_SPIKE", "OFF_TOPK_TOKEN"} else EventSeverity.HIGH
    if priority == "important_action":
        return EventSeverity.HIGH
    if priority == "low_priority":
        return EventSeverity.INFO
    return EventSeverity.WARN


def events_for_segment(segment: SegmentResult, thresholds: ThresholdConfig, mode: str, capability_level: str) -> list[Event]:
    metrics = segment.metrics
    priority = segment.priority
    segment_events: list[Event] = []
    low_margin_threshold = thresholds.low_margin_log[priority]
    entropy_threshold = thresholds.entropy[priority]
    spike_threshold = thresholds.spike_surprise[priority]
    tail_threshold = thresholds.tail_surprise[priority]
    off_top1_threshold = thresholds.off_top1_rate[priority]
    action_head_surprise = thresholds.action_head_surprise[priority]

    if metrics.low_margin_run_max is not None and metrics.low_margin_run_max >= thresholds.min_run:
        segment_events.append(
            Event(
                type="LOW_MARGIN_CLUSTER",
                severity=_severity("LOW_MARGIN_CLUSTER", priority),
                segment_id=segment.id,
                message="Repeated low-margin tokens in segment.",
                details={
                    "trigger": "low_margin_run",
                    "low_margin_run_max": metrics.low_margin_run_max,
                    "min_run": thresholds.min_run,
                    "low_margin_rate": metrics.low_margin_rate,
                    "threshold": low_margin_threshold,
                },
            )
        )
    if metrics.high_entropy_run_max is not None and metrics.high_entropy_run_max >= thresholds.min_run:
        segment_events.append(
            Event(
                type="HIGH_ENTROPY_CLUSTER",
                severity=_severity("HIGH_ENTROPY_CLUSTER", priority),
                segment_id=segment.id,
                message="Repeated high-entropy tokens in segment.",
                details={
                    "trigger": "high_entropy_run",
                    "high_entropy_run_max": metrics.high_entropy_run_max,
                    "min_run": thresholds.min_run,
                    "high_entropy_rate": metrics.high_entropy_rate,
                    "threshold": entropy_threshold,
                },
            )
        )
    if metrics.max_surprise >= spike_threshold:
        segment_events.append(
            Event(
                type="LOW_PROB_SPIKE",
                severity=_severity("LOW_PROB_SPIKE", priority),
                segment_id=segment.id,
                message="Highly improbable token spike detected.",
                details={"trigger": "max_surprise", "max_surprise": metrics.max_surprise, "threshold": spike_threshold},
            )
        )
    if metrics.tail_surprise_mean >= tail_threshold:
        segment_events.append(
            Event(
                type="TAIL_RISK_HEAVY",
                severity=_severity("TAIL_RISK_HEAVY", priority),
                segment_id=segment.id,
                message="Segment has elevated tail surprise.",
                details={"trigger": "tail_surprise_mean", "tail_surprise_mean": metrics.tail_surprise_mean, "threshold": tail_threshold},
            )
        )
    if mode == "realized":
        if metrics.off_top1_run_max is not None and (
            metrics.off_top1_run_max >= thresholds.min_run or (metrics.off_top1_rate or 0.0) >= off_top1_threshold
        ):
            details = {"min_run": thresholds.min_run, "off_top1_run_max": metrics.off_top1_run_max, "off_top1_rate": metrics.off_top1_rate, "threshold": off_top1_threshold}
            if metrics.off_top1_run_max is not None and metrics.off_top1_run_max >= thresholds.min_run:
                details["trigger"] = "off_top1_run"
            else:
                details["trigger"] = "off_top1_rate"
            segment_events.append(Event(type="OFF_TOP1_BURST", severity=_severity("OFF_TOP1_BURST", priority), segment_id=segment.id, message="Realized path repeatedly diverges from local top-1 token.", details=details))
        if metrics.any_off_topk:
            segment_events.append(Event(type="OFF_TOPK_TOKEN", severity=_severity("OFF_TOPK_TOKEN", priority), segment_id=segment.id, message="Emitted token missing from returned top-k candidates.", details={"trigger": "off_topk", "off_topk_rate": metrics.off_topk_rate}))
    if segment.kind in {"tool_name", "browser_action", "sql_clause"} and (
        (metrics.mean_margin_log is not None and metrics.mean_margin_log < low_margin_threshold)
        or metrics.avg_surprise > action_head_surprise
    ):
        triggers: list[str] = []
        if metrics.mean_margin_log is not None and metrics.mean_margin_log < low_margin_threshold:
            triggers.append("mean_margin_log")
        if metrics.avg_surprise > action_head_surprise:
            triggers.append("avg_surprise")
        segment_events.append(
            Event(
                type="ACTION_HEAD_UNCERTAIN",
                severity=_severity("ACTION_HEAD_UNCERTAIN", priority),
                segment_id=segment.id,
                message="Action-bearing head appears unstable.",
                details={
                    "trigger": triggers,
                    "mean_margin_log": metrics.mean_margin_log,
                    "low_margin_threshold": low_margin_threshold,
                    "avg_surprise": metrics.avg_surprise,
                    "action_head_surprise": action_head_surprise,
                },
            )
        )
    if segment.kind in {"tool_argument_leaf", "json_leaf", "browser_selector", "browser_text_value"} and (
        metrics.avg_surprise >= action_head_surprise or metrics.max_surprise >= spike_threshold
    ):
        triggers = []
        if metrics.avg_surprise >= action_head_surprise:
            triggers.append("avg_surprise")
        if metrics.max_surprise >= spike_threshold:
            triggers.append("max_surprise")
        segment_events.append(
            Event(
                type="ARGUMENT_VALUE_UNCERTAIN",
                severity=_severity("ARGUMENT_VALUE_UNCERTAIN", priority),
                segment_id=segment.id,
                message="Argument or leaf value appears brittle.",
                details={
                    "trigger": triggers,
                    "avg_surprise": metrics.avg_surprise,
                    "action_head_surprise": action_head_surprise,
                    "max_surprise": metrics.max_surprise,
                    "spike_surprise": spike_threshold,
                },
            )
        )
    if capability_level == "selected_only":
        segment_events.append(Event(type="MISSING_TOPK", severity=EventSeverity.INFO, segment_id=segment.id, message="Top-k logprobs unavailable; entropy and rank diagnostics are degraded.", details={"trigger": "missing_topk"}))
    return segment_events
