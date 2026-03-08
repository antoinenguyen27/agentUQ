# OpenAI Agents SDK Quickstart

Use the helper functions rather than wrapping the whole agent runtime.

## Install

```bash
pip install openai-agents
pip install -e .[dev]
```

## Minimal pattern

```python
from uq_runtime.adapters.openai_agents import OpenAIAgentsAdapter, model_settings_with_logprobs
from uq_runtime.analysis.analyzer import Analyzer
from uq_runtime.schemas.config import UQConfig

settings = model_settings_with_logprobs(top_logprobs=5)
adapter = OpenAIAgentsAdapter()
analyzer = Analyzer(UQConfig(policy="balanced", tolerance="strict"))

# After the agent model call returns a Responses-style payload:
record = adapter.capture(agent_result, {"include_output_text_logprobs": True, "top_logprobs": 5, "deterministic": True})
result = analyzer.analyze_step(record, adapter.capability_report(agent_result, {"include_output_text_logprobs": True, "top_logprobs": 5}))
print(result.decision.action)
```

## Notes

- Intercept model outputs and tool boundaries only.
- Attach `uq_result` or `decision` to traces as custom metadata if you use SDK tracing.

## Sample output excerpt

```text
{'top_logprobs': 5, 'include': ['message.output_text.logprobs']}
action=block_execution
```

## Troubleshooting

- Use Responses-style outputs when possible because that is what the adapter expects.
- If the SDK object shape differs, pass `model_dump()` output into the adapter.
- OpenAI Agents integration smoke checks should be run manually with local credentials.
