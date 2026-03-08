from uq_runtime.analysis.analyzer import Analyzer
from uq_runtime.schemas.config import UQConfig
from uq_runtime.schemas.errors import (
    LogprobsNotRequestedError,
    ProviderDroppedRequestedParameterError,
    SelectedTokenLogprobsUnavailableError,
    TopKLogprobsUnavailableError,
    UnsupportedForCanonicalModeError,
)
from uq_runtime.schemas.records import CapabilityReport, GenerationRecord, StructuredBlock, TopToken
from uq_runtime.schemas.results import Action


def record_with_tool(
    *,
    temperature: float = 0.0,
    deterministic: bool = True,
    selected_logprobs: list[float] | None = None,
    top_logprobs: list[list[TopToken]] | None = None,
    request_logprobs: bool = True,
    request_topk: int | None = 2,
    raw_text: str = 'lookup{"city":"Paris"}',
) -> GenerationRecord:
    return GenerationRecord(
        provider="openai",
        transport="direct_api",
        model="gpt-test",
        temperature=temperature,
        top_p=1.0,
        raw_text=raw_text,
        selected_tokens=["lookup", '{"city"', ":", '"Paris"', "}"],
        selected_logprobs=selected_logprobs,
        top_logprobs=top_logprobs,
        structured_blocks=[StructuredBlock(type="function_call", name="lookup", arguments='{"city":"Paris"}', text=raw_text)],
        metadata={"request_logprobs": request_logprobs, "request_topk": request_topk, "deterministic": deterministic},
    )


def capability(
    *,
    selected: bool,
    topk: bool,
    request_logprobs: bool = True,
    request_topk: int | None = 2,
) -> CapabilityReport:
    return CapabilityReport(
        selected_token_logprobs=selected,
        topk_logprobs=topk,
        topk_k=2 if topk else None,
        structured_blocks=True,
        function_call_structure=True,
        request_attempted_logprobs=request_logprobs,
        request_attempted_topk=request_topk,
    )


FULL_TOPK = [
    [TopToken(token="lookup", logprob=-0.1), TopToken(token="search", logprob=-1.0)],
    [TopToken(token='{"city"', logprob=-0.2), TopToken(token='{"location"', logprob=-1.0)],
    [TopToken(token=":", logprob=-0.1), TopToken(token=",", logprob=-1.5)],
    [TopToken(token='"Paris"', logprob=-0.3), TopToken(token='"London"', logprob=-0.4)],
    [TopToken(token="}", logprob=-0.1), TopToken(token="]", logprob=-1.2)],
]


def test_raises_when_logprobs_required_but_not_requested():
    record = record_with_tool(selected_logprobs=[-0.1] * 5, top_logprobs=FULL_TOPK, request_logprobs=False, request_topk=None)
    with_exception = Analyzer(UQConfig())
    try:
        with_exception.analyze_step(record, capability(selected=True, topk=True, request_logprobs=False, request_topk=None))
    except LogprobsNotRequestedError:
        pass
    else:
        raise AssertionError("Expected LogprobsNotRequestedError")


def test_raises_when_selected_logprobs_requested_but_missing():
    record = record_with_tool(selected_logprobs=None, top_logprobs=None)
    try:
        Analyzer(UQConfig()).analyze_step(record, capability(selected=False, topk=False))
    except SelectedTokenLogprobsUnavailableError:
        pass
    else:
        raise AssertionError("Expected SelectedTokenLogprobsUnavailableError")


def test_raises_when_topk_required_but_missing():
    record = record_with_tool(selected_logprobs=[-0.1] * 5, top_logprobs=None)
    config = UQConfig(capability={"require_topk": True, "fail_on_missing_topk": True})
    try:
        Analyzer(config).analyze_step(record, capability(selected=True, topk=False))
    except TopKLogprobsUnavailableError:
        pass
    else:
        raise AssertionError("Expected TopKLogprobsUnavailableError")


def test_raises_provider_dropped_requested_param_when_degraded_mode_disabled():
    record = record_with_tool(selected_logprobs=None, top_logprobs=None)
    config = UQConfig(capability={"fail_on_missing_logprobs": False, "allow_degraded_mode": False})
    try:
        Analyzer(config).analyze_step(record, capability(selected=False, topk=False))
    except ProviderDroppedRequestedParameterError:
        pass
    else:
        raise AssertionError("Expected ProviderDroppedRequestedParameterError")


def test_canonical_mode_downgrades_with_temperature_mismatch_when_allowed():
    record = record_with_tool(
        temperature=0.8,
        deterministic=False,
        selected_logprobs=[-0.1] * 5,
        top_logprobs=FULL_TOPK,
    )
    result = Analyzer(UQConfig(mode="canonical")).analyze_step(record, capability(selected=True, topk=True))
    assert result.mode == "realized"
    assert any(event.type == "TEMPERATURE_MISMATCH" for event in result.events)


def test_canonical_mode_raises_when_mismatch_and_degradation_disabled():
    record = record_with_tool(
        temperature=0.8,
        deterministic=False,
        selected_logprobs=[-0.1] * 5,
        top_logprobs=FULL_TOPK,
    )
    config = UQConfig(mode="canonical", capability={"allow_degraded_mode": False})
    try:
        Analyzer(config).analyze_step(record, capability(selected=True, topk=True))
    except UnsupportedForCanonicalModeError:
        pass
    else:
        raise AssertionError("Expected UnsupportedForCanonicalModeError")


def test_policy_preset_diff_for_browser_selector_risk():
    record = GenerationRecord(
        provider="openai",
        transport="direct_api",
        model="gpt-test",
        temperature=0.4,
        top_p=1.0,
        raw_text='click(selector="#delete")',
        selected_tokens=["click", "(", "selector", "=", '"#delete"', ")"],
        selected_logprobs=[-0.3, -0.1, -0.1, -0.1, -4.2, -0.1],
        top_logprobs=[
            [TopToken(token="click", logprob=-0.3), TopToken(token="type", logprob=-0.4)],
            [TopToken(token="(", logprob=-0.1), TopToken(token="[", logprob=-2.0)],
            [TopToken(token="selector", logprob=-0.1), TopToken(token="target", logprob=-1.0)],
            [TopToken(token="=", logprob=-0.1), TopToken(token=":", logprob=-2.0)],
            [TopToken(token='"#delete"', logprob=-4.2), TopToken(token='"#cancel"', logprob=-4.3)],
            [TopToken(token=")", logprob=-0.1), TopToken(token="]", logprob=-2.0)],
        ],
        metadata={"request_logprobs": True, "request_topk": 2, "deterministic": False},
    )
    cap = CapabilityReport(selected_token_logprobs=True, topk_logprobs=True, topk_k=2, request_attempted_logprobs=True, request_attempted_topk=2)
    balanced = Analyzer(UQConfig(mode="realized", policy="balanced")).analyze_step(record, cap)
    aggressive = Analyzer(UQConfig(mode="realized", policy="aggressive")).analyze_step(record, cap)
    balanced_selector = next(segment for segment in balanced.segments if segment.kind == "browser_selector")
    aggressive_selector = next(segment for segment in aggressive.segments if segment.kind == "browser_selector")
    assert balanced_selector.recommended_action == Action.ASK_USER_CONFIRMATION
    assert aggressive_selector.recommended_action == Action.REGENERATE_SEGMENT


def test_conservative_policy_retries_risky_final_prose():
    record = GenerationRecord(
        provider="openai",
        transport="direct_api",
        model="gpt-test",
        temperature=0.5,
        top_p=1.0,
        raw_text="Final answer: definitely transfer all funds now",
        selected_tokens=["Final", " answer", ":", " definitely", " transfer", " all", " funds", " now"],
        selected_logprobs=[-0.1, -0.2, -0.1, -4.8, -4.7, -4.6, -4.5, -4.4],
        top_logprobs=[
            [TopToken(token="Final", logprob=-0.1), TopToken(token="Answer", logprob=-0.2)],
            [TopToken(token=" answer", logprob=-0.2), TopToken(token=" response", logprob=-0.4)],
            [TopToken(token=":", logprob=-0.1), TopToken(token="-", logprob=-1.0)],
            [TopToken(token=" definitely", logprob=-4.8), TopToken(token=" maybe", logprob=-4.9)],
            [TopToken(token=" transfer", logprob=-4.7), TopToken(token=" wait", logprob=-4.8)],
            [TopToken(token=" all", logprob=-4.6), TopToken(token=" some", logprob=-4.7)],
            [TopToken(token=" funds", logprob=-4.5), TopToken(token=" money", logprob=-4.6)],
            [TopToken(token=" now", logprob=-4.4), TopToken(token=" later", logprob=-4.5)],
        ],
        metadata={"request_logprobs": True, "request_topk": 2, "deterministic": False},
    )
    cap = CapabilityReport(selected_token_logprobs=True, topk_logprobs=True, topk_k=2, request_attempted_logprobs=True, request_attempted_topk=2)
    result = Analyzer(UQConfig(mode="realized", policy="conservative")).analyze_step(record, cap)
    prose = next(segment for segment in result.segments if segment.kind == "final_answer_text")
    assert prose.recommended_action == Action.RETRY_STEP


def test_custom_policy_rule_is_applied():
    record = record_with_tool(selected_logprobs=[-0.1, -0.2, -0.1, -4.2, -0.1], top_logprobs=FULL_TOPK, temperature=0.6, deterministic=False)
    config = UQConfig(
        mode="realized",
        custom_rules=[
            {
                "when": {"segment_kind": "tool_argument_leaf", "events_any": ["ARGUMENT_VALUE_UNCERTAIN"]},
                "then": "emit_webhook",
            }
        ],
    )
    result = Analyzer(config).analyze_step(record, capability(selected=True, topk=True))
    leaf = next(segment for segment in result.segments if segment.kind == "tool_argument_leaf")
    assert leaf.recommended_action == Action.EMIT_WEBHOOK

