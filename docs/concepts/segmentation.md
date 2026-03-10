# Segmentation

Whole-response scoring is too blunt for agent systems. AgentUQ segments generations into action-bearing spans so policy can target the risky part rather than the whole response.

## Built-in segmentation

- Literal-first roots: structured blocks, fenced code, inline code spans, exact ReAct labels, standalone snippet lines, and explicit snippet-intro tails such as `Query: ...`
- Tool and function names when the adapter has explicit character grounding for them
- Tool arguments when the adapter has explicit character grounding for them
- JSON leaves by JSONPath
- ReAct blocks such as `Action:` and `Action Input:`
- Browser DSL commands and arguments
- URLs, paths, and shell-oriented spans in supported command contexts
- SQL clauses
- Code statements
- Fallback text spans

## Priority classes

- `critical_action`: tool names, selectors, URLs, IDs, action-bearing paths, SQL clauses, shell flags/values
- `important_action`: tool leaves, JSON leaves, browser text values, code statements
- `informational`: final answer prose
- `low_priority`: reasoning text

Higher-priority segments use stricter tolerance thresholds and stricter default actions.

Heuristic segmentation is intentionally conservative. AgentUQ does not mine arbitrary narrative prose for SQL, browser DSL, shell commands, or code-like spans just because the text resembles those formats.

For OpenAI-compatible chat/responses surfaces, tool calls are often returned as structured metadata without token-level grounding. AgentUQ records those tool calls, but it does not synthesize `tool_name` or `tool_argument_leaf` segments by substring-matching assistant prose.
