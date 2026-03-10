"""Shared analysis engine."""

from __future__ import annotations

import math
import json
from statistics import mean

from agentuq.analysis.events import events_for_segment
from agentuq.analysis.metrics import emitted_rank, margin_log, max_run, percentile, surprises, tail_mean, truncated_entropy
from agentuq.analysis.policy import PolicyEngine
from agentuq.analysis.segmentation import segment_record
from agentuq.schemas.config import UQConfig, resolve_thresholds
from agentuq.schemas.errors import (
    LogprobsNotRequestedError,
    ProviderDroppedRequestedParameterError,
    SelectedTokenLogprobsUnavailableError,
    TopKLogprobsUnavailableError,
    UnsupportedForCanonicalModeError,
)
from agentuq.schemas.records import CapabilityLevel, CapabilityReport, GenerationRecord
from agentuq.schemas.results import Action, Diagnostics, Event, EventSeverity, PrimaryScoreType, SegmentMetrics, SegmentResult, UQResult


class Analyzer:
    def __init__(self, config: UQConfig | None = None) -> None:
        self.config = config or UQConfig()
        self.policy = PolicyEngine(self.config)
        self.thresholds = resolve_thresholds(self.config.tolerance, self.config.thresholds)

    def _mode(self, record: GenerationRecord, capability: CapabilityReport) -> tuple[str, str, list[Event]]:
        requested = self.config.mode
        temp = record.temperature
        top_p = record.top_p
        deterministic = self.config.deterministic
        deterministic_source = "config"
        if deterministic is None:
            if record.metadata.get("deterministic") is not None:
                deterministic = bool(record.metadata.get("deterministic"))
                deterministic_source = "explicit_metadata"
            elif temp is not None and top_p is not None:
                deterministic = math.isclose(temp, self.config.canonical_temperature_max, abs_tol=1e-9) and math.isclose(
                    top_p, self.config.canonical_top_p_min, abs_tol=1e-9
                )
                deterministic_source = "parameter_inference"
        canonical_ready = (
            deterministic is True
            and temp is not None
            and top_p is not None
            and math.isclose(temp, self.config.canonical_temperature_max, abs_tol=1e-9)
            and math.isclose(top_p, self.config.canonical_top_p_min, abs_tol=1e-9)
        )
        if requested == "canonical":
            if not canonical_ready:
                mismatch_event = Event(
                    type="TEMPERATURE_MISMATCH",
                    severity=EventSeverity.HIGH,
                    message="Canonical mode requested but runtime metadata looks sampled or unknown; downgrading to realized mode.",
                    details={"deterministic": deterministic, "temperature": temp, "top_p": top_p},
                )
                if self.config.capability.allow_degraded_mode:
                    return "realized", "downgraded from canonical because deterministic conditions were not satisfied", [mismatch_event]
                raise UnsupportedForCanonicalModeError(
                    message="Canonical mode requested but runtime metadata does not indicate a strictly greedy generation.",
                    provider=record.provider,
                    transport=record.transport,
                    model=record.model,
                    requested_params={"mode": "canonical", "temperature": temp, "top_p": top_p},
                    observed_capability={"deterministic": deterministic, "temperature": temp, "top_p": top_p},
                    remediation="Set deterministic=True with temperature=0 and top_p=1, or switch to realized mode.",
                )
        events: list[Event] = []
        if requested == "auto":
            if canonical_ready:
                if deterministic_source == "explicit_metadata":
                    return "canonical", "auto-selected canonical mode from explicit deterministic metadata", events
                if deterministic_source == "parameter_inference":
                    return "canonical", "auto-selected canonical mode from strict greedy parameter inference", events
                return "canonical", "auto-selected canonical mode from strict greedy configuration", events
            return "realized", "auto-selected realized mode because strict greedy conditions were missing", events
        if requested == "realized":
            return "realized", "configured realized mode", events
        return "canonical", "configured canonical mode", events

    def _enforce_capabilities(self, record: GenerationRecord, capability: CapabilityReport) -> list[str]:
        warnings: list[str] = []
        if not capability.request_attempted_logprobs and self.config.capability.require_logprobs:
            raise LogprobsNotRequestedError(
                message="Token logprobs were required but not requested.",
                provider=record.provider,
                transport=record.transport,
                model=record.model,
                remediation="Set provider-specific logprob request parameters before calling capture/analyze.",
            )
        if capability.request_attempted_logprobs and not capability.selected_token_logprobs:
            if self.config.capability.fail_on_missing_logprobs:
                raise SelectedTokenLogprobsUnavailableError(
                    message="Selected-token logprobs were requested but the response did not include them.",
                    provider=record.provider,
                    transport=record.transport,
                    model=record.model,
                    requested_params={"logprobs": capability.request_attempted_logprobs, "topk": capability.request_attempted_topk},
                    observed_capability=capability.model_dump(),
                    remediation="Check model/provider support and disable silent parameter dropping in UQ-critical paths.",
                )
            warnings.append("selected-token logprobs missing; analysis degraded or unsupported")
        if self.config.capability.require_topk and not capability.topk_logprobs:
            if self.config.capability.fail_on_missing_topk:
                raise TopKLogprobsUnavailableError(
                    message="Top-k logprobs were required but unavailable.",
                    provider=record.provider,
                    transport=record.transport,
                    model=record.model,
                    requested_params={"topk": capability.request_attempted_topk},
                    observed_capability=capability.model_dump(),
                    remediation="Use a model/provider that returns top-k logprobs or relax require_topk.",
                )
            warnings.append("top-k logprobs missing; entropy and rank diagnostics degraded")
        if capability.request_attempted_logprobs and not capability.selected_token_logprobs and not self.config.capability.allow_degraded_mode:
            raise ProviderDroppedRequestedParameterError(
                message="Provider appears to have dropped requested logprob parameters.",
                provider=record.provider,
                transport=record.transport,
                model=record.model,
                requested_params={"logprobs": True, "topk": capability.request_attempted_topk},
                observed_capability=capability.model_dump(),
                remediation="Use fail-loud routing or provider.require_parameters equivalents for UQ-critical requests.",
            )
        return warnings

    def analyze_step(self, record: GenerationRecord, capability: CapabilityReport | None = None) -> UQResult:
        capability = capability or CapabilityReport(
            selected_token_logprobs=bool(record.selected_logprobs),
            topk_logprobs=bool(record.top_logprobs),
            topk_k=len(record.top_logprobs[0]) if record.top_logprobs else None,
            structured_blocks=bool(record.structured_blocks),
            function_call_structure=any(block.type in {"function_call", "tool_call"} for block in record.structured_blocks),
            request_attempted_logprobs=bool(record.metadata.get("request_logprobs")),
            request_attempted_topk=record.metadata.get("request_topk"),
        )
        warnings = self._enforce_capabilities(record, capability)
        mode, mode_reason, mode_events = self._mode(record, capability)
        logprobs = record.selected_logprobs or []
        if capability.level == CapabilityLevel.NONE and self.config.capability.block_without_signal_for_critical:
            diagnostics = Diagnostics(warnings=warnings + ["No usable token logprobs returned."], mode_reason=mode_reason)
            result = UQResult(
                primary_score=math.inf,
                primary_score_type=PrimaryScoreType.REALIZED_NLL,
                mode=mode,
                capability_level=capability.level,
                capability_report=capability,
                segments=[],
                events=[Event(type="MISSING_LOGPROBS", severity=EventSeverity.CRITICAL, message="Critical workflow configured to block without signal.")],
                action=Action.BLOCK_EXECUTION,
                diagnostics=diagnostics,
                resolved_thresholds=self.thresholds,
            )
            result.decision = self.policy.decide(result)
            return result

        segment_specs = segment_record(record, self.config.segmentation)
        segment_results: list[SegmentResult] = []
        all_events = list(mode_events)
        all_surprises = surprises(logprobs)

        for block in record.structured_blocks:
            if block.type in {"json", "structured_output"} and block.text:
                try:
                    json.loads(block.text)
                except json.JSONDecodeError as exc:
                    all_events.append(Event(type="SCHEMA_INVALID", severity=EventSeverity.CRITICAL, message=f"Structured output was not valid JSON: {exc.msg}"))
            if block.type in {"function_call", "tool_call"} and block.arguments:
                try:
                    json.loads(block.arguments)
                except json.JSONDecodeError as exc:
                    all_events.append(Event(type="SCHEMA_INVALID", severity=EventSeverity.CRITICAL, message=f"Tool arguments were not valid JSON: {exc.msg}"))

        for segment in segment_specs:
            start, end = segment.token_span
            segment_logprobs = logprobs[start:end]
            segment_surprises = all_surprises[start:end]
            topk_slice = record.top_logprobs[start:end] if record.top_logprobs else []
            token_slice = record.selected_tokens[start:end]
            margins: list[float] = []
            entropies: list[float] = []
            off_top1_flags: list[bool] = []
            off_topk_flags: list[bool] = []
            for index, top_tokens in enumerate(topk_slice):
                margin = margin_log(top_tokens)
                if margin is not None:
                    margins.append(margin)
                entropy = truncated_entropy(top_tokens, token_slice[index], segment_logprobs[index] if index < len(segment_logprobs) else None)
                if entropy is not None:
                    entropies.append(entropy)
                if index < len(token_slice):
                    rank, off_topk = emitted_rank(top_tokens, token_slice[index])
                    if rank is not None:
                        off_top1_flags.append(rank > 1)
                    off_topk_flags.append(off_topk)
            low_margin_threshold = self.thresholds.low_margin_log[segment.priority]
            entropy_threshold = self.thresholds.entropy[segment.priority]
            metrics = SegmentMetrics(
                token_count=len(segment_logprobs),
                nll=sum(segment_surprises),
                avg_surprise=mean(segment_surprises) if segment_surprises else 0.0,
                max_surprise=max(segment_surprises) if segment_surprises else 0.0,
                p95_surprise=percentile(segment_surprises, 95) if segment_surprises else 0.0,
                tail_surprise_mean=tail_mean(segment_surprises) if segment_surprises else 0.0,
                mean_margin_log=mean(margins) if margins else None,
                min_margin_log=min(margins) if margins else None,
                low_margin_rate=(sum(1 for value in margins if value < low_margin_threshold) / len(margins)) if margins else None,
                low_margin_run_max=max_run([value < low_margin_threshold for value in margins]) if margins else None,
                mean_entropy_hat=mean(entropies) if entropies else None,
                max_entropy_hat=max(entropies) if entropies else None,
                high_entropy_rate=(sum(1 for value in entropies if value > entropy_threshold) / len(entropies)) if entropies else None,
                high_entropy_run_max=max_run([value > entropy_threshold for value in entropies]) if entropies else None,
                off_top1_rate=(sum(1 for flag in off_top1_flags if flag) / len(off_top1_flags)) if off_top1_flags else None,
                off_topk_rate=(sum(1 for flag in off_topk_flags if flag) / len(off_topk_flags)) if off_topk_flags else None,
                off_top1_run_max=max_run(off_top1_flags) if off_top1_flags else None,
                any_off_topk=any(off_topk_flags),
            )
            primary_score = sum(segment_surprises)
            result_segment = SegmentResult(
                id=segment.id,
                kind=segment.kind,
                priority=segment.priority,
                text=segment.text,
                token_span=segment.token_span,
                primary_score=primary_score,
                metrics=metrics,
                metadata=segment.metadata,
            )
            result_segment.events.extend(events_for_segment(result_segment, self.thresholds, mode, capability.level.value))
            segment_results.append(result_segment)
            all_events.extend(result_segment.events)

        primary_score = sum(all_surprises) if logprobs else math.inf
        primary_score_type = PrimaryScoreType.G_NLL if mode == "canonical" else PrimaryScoreType.REALIZED_NLL
        diagnostics = Diagnostics(
            warnings=warnings,
            mode_reason=mode_reason,
            token_count=len(record.selected_tokens),
        )
        result = UQResult(
            primary_score=primary_score,
            primary_score_type=primary_score_type,
            mode=mode,
            capability_level=capability.level,
            capability_report=capability,
            segments=segment_results,
            events=all_events,
            action=Action.CONTINUE,
            diagnostics=diagnostics,
            resolved_thresholds=self.thresholds,
        )
        decision = self.policy.decide(result)
        result.action = decision.action
        result.decision = decision
        return result
