"""Policy engine with presets and custom rules."""

from __future__ import annotations

from dataclasses import dataclass

from uq_runtime.schemas.config import PolicyPreset, UQConfig
from uq_runtime.schemas.results import Action, Decision, EventSeverity, SegmentResult, UQResult


@dataclass
class DecisionContext:
    segment: SegmentResult
    result: UQResult


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


class PolicyEngine:
    def __init__(self, config: UQConfig) -> None:
        self.config = config

    def _preset(self) -> str:
        policy = self.config.policy
        if isinstance(policy, PolicyPreset):
            return policy.value
        return str(policy)

    def _apply_custom_rules(self, segment: SegmentResult) -> Action | None:
        event_types = {event.type for event in segment.events}
        for rule in self.config.custom_rules:
            when = rule.when
            if when.get("segment_kind") and when["segment_kind"] != segment.kind:
                continue
            if when.get("segment_priority") and when["segment_priority"] != segment.priority:
                continue
            events_any = set(when.get("events_any", []))
            if events_any and not (events_any & event_types):
                continue
            severity = when.get("severity_at_least")
            if severity:
                severities = {event.severity.value for event in segment.events}
                ordered = ["info", "warn", "high", "critical"]
                if not severities or max(ordered.index(value) for value in severities) < ordered.index(severity):
                    continue
            return Action(rule.then)
        return None

    def segment_action(self, ctx: DecisionContext) -> Action:
        custom = self._apply_custom_rules(ctx.segment)
        if custom is not None:
            return custom
        event_types = {event.type for event in ctx.segment.events}
        highest = max((event.severity for event in ctx.segment.events), default=EventSeverity.INFO, key=lambda sev: ["info", "warn", "high", "critical"].index(sev.value))
        preset = self._preset()

        if "SCHEMA_INVALID" in event_types:
            return Action.BLOCK_EXECUTION
        if ctx.segment.kind == "tool_name":
            if {"ACTION_HEAD_UNCERTAIN", "LOW_PROB_SPIKE"} & event_types:
                return Action.RETRY_STEP_WITH_CONSTRAINTS
        if ctx.segment.kind in {"tool_argument_leaf", "json_leaf", "browser_text_value"} and "ARGUMENT_VALUE_UNCERTAIN" in event_types:
            return Action.REGENERATE_SEGMENT
        if ctx.segment.kind in {"browser_selector", "url", "identifier"} and {"LOW_PROB_SPIKE", "LOW_MARGIN_CLUSTER"} & event_types:
            return Action.ASK_USER_CONFIRMATION if preset != "aggressive" else Action.REGENERATE_SEGMENT
        if ctx.segment.kind == "sql_clause" and highest in {EventSeverity.HIGH, EventSeverity.CRITICAL}:
            return Action.DRY_RUN_VERIFY
        if ctx.segment.kind in {"final_answer_text", "unknown_text"}:
            if highest in {EventSeverity.HIGH, EventSeverity.CRITICAL} and preset == "conservative":
                return Action.RETRY_STEP
            if preset == "conservative" and len(ctx.segment.events) >= 2:
                return Action.RETRY_STEP
            if ctx.segment.events:
                return Action.CONTINUE_WITH_ANNOTATION
        if ctx.segment.priority == "critical_action":
            if highest == EventSeverity.CRITICAL:
                return Action.BLOCK_EXECUTION if preset == "conservative" else Action.ASK_USER_CONFIRMATION
            if highest == EventSeverity.HIGH:
                return Action.ASK_USER_CONFIRMATION
        return Action.CONTINUE

    def decide(self, result: UQResult) -> Decision:
        segment_actions: dict[str, Action] = {}
        if any(event.type == "SCHEMA_INVALID" for event in result.events):
            return Decision(
                action=Action.BLOCK_EXECUTION,
                rationale="Structured output or tool arguments failed validation.",
                segment_actions=segment_actions,
                events=result.events,
            )
        overall = Action.CONTINUE
        for segment in result.segments:
            action = self.segment_action(DecisionContext(segment=segment, result=result))
            segment.recommended_action = action
            segment_actions[segment.id] = action
            if _action_rank(action) > _action_rank(overall):
                overall = action
        rationale = f"Policy preset {self._preset()} selected {overall.value} based on segment events."
        return Decision(action=overall, rationale=rationale, segment_actions=segment_actions, events=result.events)
