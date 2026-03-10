from uq_runtime.analysis.analyzer import Analyzer
from uq_runtime.schemas.config import UQConfig
from uq_runtime.schemas.records import CapabilityReport, GenerationRecord, StructuredBlock, TopToken
from uq_runtime.schemas.results import Action, PrimaryScoreType


def make_record(**overrides):
    raw_text = 'weather{"city":"Paris"}'
    base = GenerationRecord(
        provider="openai",
        transport="direct_api",
        model="gpt-test",
        temperature=0.0,
        top_p=1.0,
        raw_text=raw_text,
        selected_tokens=["weather", '{"city"', ":", '"Paris"', "}"],
        selected_logprobs=[-0.1, -0.2, -0.05, -3.8, -0.1],
        top_logprobs=[
            [TopToken(token="weather", logprob=-0.1), TopToken(token="search", logprob=-1.3)],
            [TopToken(token='{"city"', logprob=-0.2), TopToken(token='{"name"', logprob=-1.0)],
            [TopToken(token=":", logprob=-0.05), TopToken(token=",", logprob=-2.0)],
            [TopToken(token='"Paris"', logprob=-3.8), TopToken(token='"London"', logprob=-3.9)],
            [TopToken(token="}", logprob=-0.1), TopToken(token="]", logprob=-1.2)],
        ],
        structured_blocks=[
            StructuredBlock(
                type="function_call",
                name="weather",
                arguments='{"city":"Paris"}',
                text=raw_text,
                char_start=0,
                char_end=len(raw_text),
                metadata={"token_grounded": True},
            )
        ],
        metadata={"request_logprobs": True, "request_topk": 2, "deterministic": True},
    )
    return base.model_copy(update=overrides)


def make_capability(full: bool = True):
    return CapabilityReport(
        selected_token_logprobs=True,
        topk_logprobs=full,
        topk_k=2 if full else None,
        structured_blocks=True,
        function_call_structure=True,
        request_attempted_logprobs=True,
        request_attempted_topk=2 if full else None,
    )


def test_auto_mode_picks_canonical_for_deterministic_run():
    analyzer = Analyzer(UQConfig(mode="auto"))
    result = analyzer.analyze_step(make_record(), make_capability())
    assert result.mode == "canonical"
    assert result.primary_score_type == PrimaryScoreType.G_NLL
    assert result.diagnostics.mode_reason == "auto-selected canonical mode from explicit deterministic metadata"


def test_auto_mode_reports_parameter_inference_when_metadata_is_absent():
    analyzer = Analyzer(UQConfig(mode="auto"))
    record = make_record(metadata={"request_logprobs": True, "request_topk": 2})
    result = analyzer.analyze_step(record, make_capability())
    assert result.mode == "canonical"
    assert result.diagnostics.mode_reason == "auto-selected canonical mode from strict greedy parameter inference"


def test_auto_mode_picks_realized_when_temperature_is_high():
    analyzer = Analyzer(UQConfig(mode="auto"))
    record = make_record(temperature=0.8, metadata={"request_logprobs": True, "request_topk": 2, "deterministic": False})
    result = analyzer.analyze_step(record, make_capability())
    assert result.mode == "realized"
    assert result.primary_score_type == PrimaryScoreType.REALIZED_NLL


def test_auto_mode_picks_realized_when_top_p_is_missing_under_strict_canonical_rules():
    analyzer = Analyzer(UQConfig(mode="auto"))
    record = make_record(top_p=None, metadata={"request_logprobs": True, "request_topk": 2, "deterministic": True})
    result = analyzer.analyze_step(record, make_capability())
    assert result.mode == "realized"
    assert result.primary_score_type == PrimaryScoreType.REALIZED_NLL


def test_selected_only_capability_degrades_and_emits_missing_topk():
    analyzer = Analyzer(UQConfig(mode="realized", capability={"fail_on_missing_topk": False}))
    record = make_record(top_logprobs=None)
    capability = make_capability(full=False)
    result = analyzer.analyze_step(record, capability)
    assert result.capability_level.value == "selected_only"
    assert any(event.type == "MISSING_TOPK" for event in result.events)


def test_tool_argument_low_prob_spike_requests_regeneration():
    analyzer = Analyzer(UQConfig(mode="realized"))
    result = analyzer.analyze_step(make_record(temperature=0.6, metadata={"request_logprobs": True, "request_topk": 2, "deterministic": False}), make_capability())
    leaf_segments = [segment for segment in result.segments if segment.kind == "tool_argument_leaf"]
    assert leaf_segments
    assert any(event.type == "ARGUMENT_VALUE_UNCERTAIN" for event in leaf_segments[0].events)
    assert leaf_segments[0].recommended_action == Action.REGENERATE_SEGMENT
