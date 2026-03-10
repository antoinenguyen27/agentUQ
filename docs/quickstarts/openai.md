# OpenAI Quickstart

Use the Responses API for new agentic integrations. AgentUQ supports both Responses and Chat Completions.

## Install

```bash
pip install openai
pip install -e .[dev]
```

## Minimal request with readable terminal output

Responses API:

```python
from openai import OpenAI
from uq_runtime.adapters.openai_responses import OpenAIResponsesAdapter
from uq_runtime.analysis.analyzer import Analyzer
from uq_runtime.schemas.config import UQConfig

client = OpenAI()
request_meta = {
    "model": "gpt-4.1-mini",
    "include": ["message.output_text.logprobs"],
    "top_logprobs": 5,
    "temperature": 0.0,
    "top_p": 1.0,
}
response = client.responses.create(
    model=request_meta["model"],
    input="Return the single word Paris.",
    include=request_meta["include"],
    top_logprobs=request_meta["top_logprobs"],
    temperature=request_meta["temperature"],
    top_p=request_meta["top_p"],
)

adapter = OpenAIResponsesAdapter()
analyzer = Analyzer(UQConfig(policy="balanced", tolerance="strict"))
record = adapter.capture(response, request_meta)
result = analyzer.analyze_step(record, adapter.capability_report(response, request_meta))
print(result.pretty())
```

## Capture -> analyze -> decide

Use `OpenAIResponsesAdapter` or `OpenAIChatAdapter`, then pass the normalized record into `Analyzer`.

For canonical mode, keep the request strictly greedy: `temperature=0`, `top_p=1`, and deterministic metadata in the capture request meta. If any of that is missing, AgentUQ will analyze the step in realized mode instead.

For a fuller diagnostic view, use `result.pretty(verbosity="debug", show_thresholds="all")`.

## Act on the result

```python
from uq_runtime.schemas.results import Action

decision = result.decision

if decision.action == Action.CONTINUE:
    run_next_step()
elif decision.action == Action.CONTINUE_WITH_ANNOTATION:
    logger.warning("AgentUQ flagged this step", extra={"uq_result": result.model_dump(mode="json")})
    run_next_step()
elif decision.action == Action.RETRY_STEP_WITH_CONSTRAINTS:
    retry_with_tighter_prompt()
elif decision.action == Action.DRY_RUN_VERIFY:
    run_safe_validator(result)
elif decision.action in {Action.ASK_USER_CONFIRMATION, Action.BLOCK_EXECUTION}:
    stop_before_side_effect(result)
```

If you need per-segment control rather than one step-level branch, inspect `result.decision.segment_actions` and `result.segments`.

## Sample output excerpt

```text
Summary
  recommended_action: Continue
  rationale: Policy preset balanced selected continue based on segment events.
  mode: canonical
  whole_response_score: 0.021 g_nll
  whole_response_score_note: Summarizes the full emitted path; it does not determine the recommended action by itself.
  capability: full

Segments
  final answer prose [informational] -> Continue
    text: Paris.
    surprise: score=0.021 nll=0.021 avg=0.011 p95=0.018 max=0.018 tail=0.018
    events: none
```

## Troubleshooting

- Chat Completions: pass `logprobs=True` and `top_logprobs=k`.
- Responses: include `message.output_text.logprobs`; do not assume function-call items carry token logprobs.
- OpenAI-family tool calls are captured structurally, but tool-name/tool-argument segments require explicit token grounding rather than incidental mentions in assistant prose.
- For the full runtime loop and customization model, see [Acting on decisions](../concepts/acting_on_decisions.md) and [Policies](../concepts/policies.md).
- This example can be adapted into a local live smoke test, but AgentUQ does not run provider-backed tests in required OSS CI.
