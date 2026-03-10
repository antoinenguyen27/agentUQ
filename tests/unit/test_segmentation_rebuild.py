from uq_runtime.analysis.analyzer import Analyzer
from uq_runtime.analysis.segmentation import segment_record
from uq_runtime.schemas.config import SegmentationConfig, UQConfig
from uq_runtime.schemas.records import CapabilityReport, GenerationRecord, StructuredBlock, TopToken


def _record(raw_text: str, structured_blocks: list[StructuredBlock] | None = None) -> GenerationRecord:
    return GenerationRecord(
        provider="openai",
        transport="direct_api",
        model="gpt-test",
        temperature=0.0,
        top_p=1.0,
        raw_text=raw_text,
        selected_tokens=[raw_text],
        selected_logprobs=[-0.1],
        top_logprobs=[[TopToken(token=raw_text, logprob=-0.1), TopToken(token="other", logprob=-1.0)]],
        structured_blocks=structured_blocks or [],
        metadata={"request_logprobs": True, "request_topk": 2, "deterministic": True},
    )


def _capability() -> CapabilityReport:
    return CapabilityReport(
        selected_token_logprobs=True,
        topk_logprobs=True,
        topk_k=2,
        structured_blocks=True,
        request_attempted_logprobs=True,
        request_attempted_topk=2,
    )


def test_multiline_final_prose_does_not_promote_to_code():
    raw_text = "- Paris is the capital of France.\n- Berlin is the capital of Germany."
    record = _record(
        raw_text,
        [StructuredBlock(type="output_text", text=raw_text, char_start=0, char_end=len(raw_text), metadata={"role": "final"})],
    )

    segments = segment_record(record, SegmentationConfig())

    assert [segment.kind for segment in segments] == ["final_answer_text"]
    assert segments[0].priority == "informational"


def test_fenced_code_is_scoped_to_code_statements():
    raw_text = "Summary:\n```python\nx = 1\ny = x + 1\n```\nDone."
    record = _record(
        raw_text,
        [StructuredBlock(type="output_text", text=raw_text, char_start=0, char_end=len(raw_text), metadata={"role": "final"})],
    )

    segments = segment_record(record, SegmentationConfig())
    code_segments = [segment for segment in segments if segment.kind == "code_statement"]

    assert any(segment.kind == "final_answer_text" for segment in segments)
    assert [segment.text for segment in code_segments] == ["x = 1", "y = x + 1"]
    assert all(segment.priority == "important_action" for segment in code_segments)


def test_grounded_tool_call_only_emits_tool_segments():
    raw_text = 'weather{"city":"Paris"}'
    record = _record(
        raw_text,
        [
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
    )

    segments = segment_record(record, SegmentationConfig())

    assert {segment.kind for segment in segments} == {"tool_name", "tool_arguments_raw", "tool_argument_leaf"}


def test_json_segments_are_scoped_without_code_fallback():
    raw_text = '{"url":"https://example.com","count":2}'
    record = _record(
        raw_text,
        [StructuredBlock(type="json", text=raw_text, char_start=0, char_end=len(raw_text))],
    )

    segments = segment_record(record, SegmentationConfig())

    assert {segment.kind for segment in segments} == {"json_leaf"}
    assert {segment.text for segment in segments} == {"https://example.com", "2"}


def test_browser_and_sql_are_scoped_without_generic_code_duplicates():
    browser_record = _record('click(selector="#submit")')
    sql_record = _record("SELECT email FROM users WHERE active = true LIMIT 10")

    browser_segments = segment_record(browser_record, SegmentationConfig())
    sql_segments = segment_record(sql_record, SegmentationConfig())

    assert {segment.kind for segment in browser_segments} == {"browser_action", "browser_selector"}
    assert "code_statement" not in {segment.kind for segment in sql_segments}
    assert {segment.kind for segment in sql_segments} == {"sql_clause"}


def test_uncovered_plain_text_uses_unknown_fallback_only():
    raw_text = "Just a plain note.\nNothing executable here."
    record = _record(raw_text)

    segments = segment_record(record, SegmentationConfig())

    assert {segment.kind for segment in segments} == {"unknown_text"}


def test_pretty_debug_no_longer_shows_code_for_plain_final_prose():
    raw_text = "- Fact one\n- Fact two"
    record = _record(
        raw_text,
        [StructuredBlock(type="output_text", text=raw_text, char_start=0, char_end=len(raw_text), metadata={"role": "final"})],
    )
    result = Analyzer(UQConfig()).analyze_step(record, _capability())

    rendered = result.pretty(verbosity="debug", show_thresholds="all")

    assert "final_answer_text" in rendered
    assert "code_statement" not in rendered
