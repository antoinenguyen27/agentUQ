from uq_runtime.analysis.analyzer import Analyzer
from uq_runtime.schemas.config import UQConfig
from uq_runtime.schemas.records import CapabilityReport, GenerationRecord, StructuredBlock, TopToken


def _quiet_record() -> tuple[GenerationRecord, CapabilityReport]:
    record = GenerationRecord(
        provider="openai",
        transport="direct_api",
        model="gpt-test",
        temperature=0.0,
        top_p=1.0,
        raw_text="Paris.",
        selected_tokens=["Paris", "."],
        selected_logprobs=[-0.01, -0.01],
        top_logprobs=[
            [TopToken(token="Paris", logprob=-0.01), TopToken(token="London", logprob=-4.0)],
            [TopToken(token=".", logprob=-0.01), TopToken(token="!", logprob=-3.0)],
        ],
        structured_blocks=[StructuredBlock(type="output_text", text="Paris.", metadata={"role": "final"})],
        metadata={"request_logprobs": True, "request_topk": 2, "deterministic": True},
    )
    capability = CapabilityReport(
        selected_token_logprobs=True,
        topk_logprobs=True,
        topk_k=2,
        structured_blocks=True,
        request_attempted_logprobs=True,
        request_attempted_topk=2,
    )
    return record, capability


def _noisy_record() -> tuple[GenerationRecord, CapabilityReport]:
    raw_text = 'weather{"city":"Paris"}'
    record = GenerationRecord(
        provider="openai",
        transport="direct_api",
        model="gpt-test",
        temperature=0.8,
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
        metadata={"request_logprobs": True, "request_topk": 2, "deterministic": False},
    )
    capability = CapabilityReport(
        selected_token_logprobs=True,
        topk_logprobs=True,
        topk_k=2,
        structured_blocks=True,
        function_call_structure=True,
        request_attempted_logprobs=True,
        request_attempted_topk=2,
    )
    return record, capability


def test_pretty_summary_includes_explanatory_event_thresholds():
    analyzer = Analyzer(UQConfig(mode="realized"))
    record, capability = _noisy_record()
    result = analyzer.analyze_step(record, capability)

    rendered = result.pretty()

    assert result.resolved_thresholds is not None
    assert "Summary" in rendered
    assert "mode: realized" in rendered
    assert "aggregate_primary_score:" in rendered
    assert "score_note: aggregate over full emitted path; compare segments for operational risk" in rendered
    assert "action:" in rendered
    assert "top_risk:" in rendered
    assert "risk_basis:" in rendered
    assert "rationale:" in rendered
    assert "capability: full" in rendered
    assert "Segments" in rendered
    assert "tool_argument_leaf" in rendered
    assert "ARGUMENT_VALUE_UNCERTAIN" in rendered
    assert "action_head_surprise=" in rendered


def test_pretty_compact_omits_segment_section_for_quiet_result():
    analyzer = Analyzer(UQConfig(mode="auto"))
    record, capability = _quiet_record()
    result = analyzer.analyze_step(record, capability)

    rendered = result.pretty(verbosity="compact")

    assert "Summary" in rendered
    assert "mode: canonical" in rendered
    assert "capability: full" in rendered
    assert "Segments" not in rendered
    assert "Highlights" not in rendered


def test_pretty_renders_cluster_events_from_actual_trigger_details():
    record = GenerationRecord(
        provider="openai",
        transport="direct_api",
        model="gpt-test",
        temperature=0.0,
        top_p=1.0,
        raw_text="hello",
        selected_tokens=["hello"],
        selected_logprobs=[-0.2],
        top_logprobs=[[TopToken(token="hello", logprob=-0.2), TopToken(token="hullo", logprob=-0.21), TopToken(token="hey", logprob=-0.22)]],
        structured_blocks=[StructuredBlock(type="output_text", text="hello", metadata={"role": "final"})],
        metadata={"request_logprobs": True, "request_topk": 3, "deterministic": True},
    )
    capability = CapabilityReport(
        selected_token_logprobs=True,
        topk_logprobs=True,
        topk_k=3,
        structured_blocks=True,
        request_attempted_logprobs=True,
        request_attempted_topk=3,
    )
    rendered = Analyzer(UQConfig(mode="canonical", tolerance="strict")).analyze_step(record, capability).pretty()

    assert "low_margin_run_max=1 >= min_run=1" in rendered
    assert "mean_margin_log" not in rendered


def test_pretty_debug_can_show_all_thresholds():
    analyzer = Analyzer(UQConfig(mode="auto"))
    record, capability = _quiet_record()
    result = analyzer.analyze_step(record, capability)

    rendered = result.pretty(verbosity="debug", show_thresholds="all")

    assert "capability_details:" in rendered
    assert "Segments" in rendered
    assert "thresholds:" in rendered
    assert "low_margin_log=" in rendered
    assert "action_head_surprise=" in rendered


def test_pretty_rejects_invalid_options():
    analyzer = Analyzer(UQConfig(mode="auto"))
    record, capability = _quiet_record()
    result = analyzer.analyze_step(record, capability)

    try:
        result.pretty(verbosity="loud")
    except ValueError:
        pass
    else:
        raise AssertionError("Expected invalid verbosity to raise ValueError")

    try:
        result.pretty(show_thresholds="sometimes")
    except ValueError:
        pass
    else:
        raise AssertionError("Expected invalid threshold display to raise ValueError")
