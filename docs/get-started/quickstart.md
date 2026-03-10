---
title: Quickstart
description: Capture a model response, analyze it with AgentUQ, and route the workflow using the returned decision.
slug: /get-started/quickstart
sidebar_position: 4
---

# Quickstart

Use the OpenAI Responses API for new agentic integrations. AgentUQ supports both Responses and Chat Completions, but this is the shortest end-to-end loop.

## Minimal `capture -> analyze -> decide` loop

```python
from openai import OpenAI

from agentuq import Action, Analyzer, UQConfig
from agentuq.adapters.openai_responses import OpenAIResponsesAdapter

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
    input="Return a SQL query for active users created in the last 7 days.",
    include=request_meta["include"],
    top_logprobs=request_meta["top_logprobs"],
    temperature=request_meta["temperature"],
    top_p=request_meta["top_p"],
)

adapter = OpenAIResponsesAdapter()
analyzer = Analyzer(UQConfig(policy="balanced", tolerance="strict"))
record = adapter.capture(response, request_meta)
result = analyzer.analyze_step(record, adapter.capability_report(response, request_meta))
decision = result.decision

print(result.pretty())

if decision.action == Action.DRY_RUN_VERIFY:
    run_explain_before_execution(result)
elif decision.action in {Action.ASK_USER_CONFIRMATION, Action.BLOCK_EXECUTION}:
    stop_before_side_effect(result)
else:
    continue_workflow(response)
```

That is the public runtime contract:

1. capture the response into a `GenerationRecord`
2. analyze it with `Analyzer`
3. read `result.decision.action`
4. branch into retry, verification, confirmation, or blocking logic

## What decisions AgentUQ can return

- `continue`: proceed normally
- `continue_with_annotation`: proceed, but attach the result to logs, traces, or monitoring
- `regenerate_segment`: retry only the risky leaf or clause when your framework supports structured repair
- `retry_step` / `retry_step_with_constraints`: rerun the model step with tighter instructions or narrower decoding
- `dry_run_verify`: run a safe validator before execution
- `ask_user_confirmation` / `block_execution`: stop before a side effect

Advanced actions such as `escalate_to_human`, `emit_webhook`, and `custom` are available for user-defined dispatch logic.

## Pretty output

Use `UQResult.pretty()` when you want a readable multiline summary for a terminal, log, or trace note:

```python
print(result.pretty())
print(result.pretty(verbosity="compact"))
print(result.pretty(verbosity="debug", show_thresholds="all"))
```

Plain-text output is the canonical rendering contract. Rich output is optional.

## What to read next

- [Acting on decisions](../concepts/acting_on_decisions.md) for runtime branching patterns
- [Reading results](../concepts/reading_results.md) for metric interpretation and threshold semantics
- [Policies](../concepts/policies.md) and [Tolerance](../concepts/tolerance.md) for tuning
- [OpenAI Quickstart](../quickstarts/openai.md) if you want the full provider-specific path

