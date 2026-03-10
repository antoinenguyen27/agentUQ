# OpenAI Agents SDK Quickstart

Use the helper functions with the SDK's `ModelSettings`, then analyze the SDK's raw Responses objects.

## Install

```bash
pip install openai-agents
pip install -e .[dev]
```

## Minimal pattern with readable terminal output

```python
from agents import Agent, ModelSettings, Runner
from uq_runtime.adapters.openai_agents import OpenAIAgentsAdapter, latest_raw_response, model_settings_with_logprobs
from uq_runtime.analysis.analyzer import Analyzer
from uq_runtime.schemas.config import UQConfig

settings = model_settings_with_logprobs(top_logprobs=5, temperature=0.0, top_p=1.0)
agent = Agent(
    name="AgentUQ Quickstart",
    instructions="Reply with the single word Paris.",
    model="gpt-4.1-mini",
    model_settings=ModelSettings(**settings),
)
run_result = Runner.run_sync(agent, "Return the single word Paris.")

request_meta = {
    "response_include": settings["response_include"],
    "top_logprobs": settings["top_logprobs"],
    "temperature": 0.0,
    "top_p": 1.0,
    "deterministic": True,
}
adapter = OpenAIAgentsAdapter()
analyzer = Analyzer(UQConfig(policy="balanced", tolerance="strict"))
response = latest_raw_response(run_result)
record = adapter.capture(response, request_meta)
result = analyzer.analyze_step(record, adapter.capability_report(response, request_meta))
print(result.pretty())
```

## Notes

- Intercept model outputs and tool boundaries only.
- The helper config is for the SDK `ModelSettings` surface. For analysis, pass the raw SDK response object exposed on `run_result.raw_responses` into the adapter.
- Attach `uq_result` or `decision` to traces as custom metadata if you use SDK tracing.

## Sample output excerpt

```text
Summary
  mode: canonical
  reason: auto-selected canonical mode from strict greedy parameter inference
  aggregate_primary_score: 0.021 g_nll
  action: continue
  rationale: Policy preset balanced selected continue based on segment events.
  capability: full

Segments
  final_answer_text [informational] -> continue
    text: Paris.
    metrics: score=0.021 avg_surprise=0.011 max_surprise=0.018 mean_entropy=0.104
    events: none
```

## Troubleshooting

- Use Responses-style outputs when possible because that is what the adapter expects.
- `model_settings_with_logprobs()` is for the Agents SDK `ModelSettings` surface, not raw `OpenAI().responses.create(...)`.
- OpenAI Agents inherits the Responses logprob surface: message text can be scored, but tool-call items are structural unless the SDK/provider adds explicit grounding.
- If the SDK stops exposing `raw_responses`, AgentUQ should treat that as integration drift and update the extraction path explicitly rather than silently skipping analysis.
- OpenAI Agents integration smoke checks should be run manually with local credentials.
