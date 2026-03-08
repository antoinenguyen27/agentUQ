from uq_runtime.analysis.analyzer import Analyzer
from uq_runtime.schemas.config import UQConfig
from uq_runtime.schemas.records import CapabilityReport, GenerationRecord, TopToken


def test_react_and_sql_segmentation_are_detected():
    react_record = GenerationRecord(
        provider="openai",
        transport="direct_api",
        model="gpt-test",
        temperature=0.0,
        top_p=1.0,
        raw_text="Thought: inspect\nAction: click(selector=\"#submit\")\nAction Input: {\"selector\":\"#submit\"}\nFinal Answer: done",
        selected_tokens=["Thought:", " inspect", "Action:", " click", "Action Input:", " {", "Final Answer:", " done"],
        selected_logprobs=[-0.1] * 8,
        top_logprobs=[[TopToken(token="x", logprob=-0.1), TopToken(token="y", logprob=-0.3)]] * 8,
        metadata={"request_logprobs": True, "request_topk": 2, "deterministic": True},
    )
    sql_record = GenerationRecord(
        provider="openai",
        transport="direct_api",
        model="gpt-test",
        temperature=0.2,
        top_p=1.0,
        raw_text="SELECT email FROM users WHERE active = true LIMIT 10",
        selected_tokens=["SELECT", " email", " FROM", " users", " WHERE", " active", " LIMIT", " 10"],
        selected_logprobs=[-0.2] * 8,
        top_logprobs=[[TopToken(token="x", logprob=-0.2), TopToken(token="y", logprob=-0.4)]] * 8,
        metadata={"request_logprobs": True, "request_topk": 2, "deterministic": True},
    )
    cap = CapabilityReport(selected_token_logprobs=True, topk_logprobs=True, topk_k=2, request_attempted_logprobs=True, request_attempted_topk=2)
    react_result = Analyzer(UQConfig()).analyze_step(react_record, cap)
    sql_result = Analyzer(UQConfig()).analyze_step(sql_record, cap)
    react_kinds = {segment.kind for segment in react_result.segments}
    sql_kinds = {segment.kind for segment in sql_result.segments}
    assert "reasoning_text" in react_kinds
    assert "browser_action" in react_kinds
    assert "tool_arguments_raw" in react_kinds
    assert "final_answer_text" in react_kinds
    assert "sql_clause" in sql_kinds


def test_low_margin_entropy_and_off_top1_events_are_emitted():
    record = GenerationRecord(
        provider="openai",
        transport="direct_api",
        model="gpt-test",
        temperature=0.7,
        top_p=1.0,
        raw_text='click(selector="#submit")',
        selected_tokens=["click", "(", '"#submit"', ")"],
        selected_logprobs=[-0.5, -0.1, -0.6, -0.1],
        top_logprobs=[
            [TopToken(token="tap", logprob=-0.49), TopToken(token="click", logprob=-0.5), TopToken(token="type", logprob=-0.51)],
            [TopToken(token="(", logprob=-0.1), TopToken(token="[", logprob=-0.2), TopToken(token="{", logprob=-0.21)],
            [TopToken(token='"#cancel"', logprob=-0.58), TopToken(token='"#submit"', logprob=-0.6), TopToken(token='"#ok"', logprob=-0.61)],
            [TopToken(token=")", logprob=-0.1), TopToken(token="]", logprob=-0.2), TopToken(token="}", logprob=-0.21)],
        ],
        metadata={"request_logprobs": True, "request_topk": 3, "deterministic": False},
    )
    cap = CapabilityReport(selected_token_logprobs=True, topk_logprobs=True, topk_k=3, request_attempted_logprobs=True, request_attempted_topk=3)
    result = Analyzer(
        UQConfig(
            mode="realized",
            thresholds={
                "entropy": {
                    "critical_action": 1.0,
                    "important_action": 1.0,
                    "informational": 1.0,
                    "low_priority": 1.0,
                }
            },
        )
    ).analyze_step(record, cap)
    event_types = {event.type for event in result.events}
    assert "LOW_MARGIN_CLUSTER" in event_types
    assert "HIGH_ENTROPY_CLUSTER" in event_types
    assert "OFF_TOP1_BURST" in event_types
    assert "ACTION_HEAD_UNCERTAIN" in event_types
