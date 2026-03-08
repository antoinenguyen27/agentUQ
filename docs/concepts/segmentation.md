# Segmentation

Whole-response scoring is too blunt for agent systems. AgentUQ segments generations into action-bearing spans so policy can target the risky part rather than the whole response.

## Built-in segmentation

- Tool and function names
- Tool arguments
- JSON leaves by JSONPath
- ReAct blocks such as `Action:` and `Action Input:`
- Browser DSL commands and arguments
- SQL clauses
- Code statements
- Fallback text spans

## Priority classes

- `critical_action`: tool names, selectors, URLs, IDs, SQL clauses, destructive shell values
- `important_action`: tool leaves, JSON leaves, browser text values, code statements
- `informational`: final answer prose
- `low_priority`: reasoning text

Policies are stricter on higher-priority segments.

