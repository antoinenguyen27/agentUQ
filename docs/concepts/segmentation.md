---
title: Segmentation
description: How AgentUQ localizes emitted-path likelihood onto action-bearing spans without inventing a new score.
slug: /concepts/segmentation
sidebar_position: 5
---

# Segmentation

Whole-response scoring is too blunt for agent systems. AgentUQ segments generations into action-bearing spans so policy can target the risky part rather than the whole response.

The simplest way to think about it is:

- whole-response uncertainty is a smoke alarm
- segmentation tells you which room

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
- Residual prose slices around embedded literal/action spans

## Priority classes

- `critical_action`: tool names, selectors, URLs, IDs, action-bearing paths, SQL clauses, shell flags/values
- `important_action`: tool leaves, JSON leaves, browser text values, code statements
- `informational`: final answer prose
- `low_priority`: reasoning text

Higher-priority segments use stricter tolerance thresholds and stricter default actions.

Heuristic segmentation is intentionally conservative. AgentUQ does not mine arbitrary narrative prose for SQL, browser DSL, shell commands, or code-like spans just because the text resembles those formats.

Text containers such as final answers, observations, and reasoning blocks are structural only. When they contain embedded literal/action spans, AgentUQ emits non-overlapping residual text slices instead of one wrapper text segment for the full block. This keeps prose warnings localized and prevents text segments from overlapping SQL, browser, shell, or code children.

Inline literals that are explicit but not recognized as action-bearing are treated as transparent and absorbed back into the surrounding prose. Opaque block literals such as unclassified fenced blocks remain separate text segments so coverage is preserved without fragmenting prose into tiny slices.

For OpenAI-compatible chat/responses surfaces, tool calls are often returned as structured metadata without token-level grounding. AgentUQ records those tool calls, but it does not synthesize `tool_name` or `tool_argument_leaf` segments by substring-matching assistant prose.

## Why this matters in practice

Consider a mixed final answer:

- explanation prose
- `SELECT *`
- `FROM users;`
- more explanation

Without segmentation, a whole-response score can only tell you that some part of the answer looked brittle.

With segmentation, AgentUQ can distinguish:

- prose that might deserve annotation,
- from SQL that might deserve dry-run verification or a stricter policy,
- without pretending that the whole answer is one uniform risk object.

That is what makes the signal operationally useful inside agent loops.
