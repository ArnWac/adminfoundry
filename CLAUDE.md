# CLAUDE.md

This file defines working rules for this repository with one main goal: **use as few tokens as possible while preserving correctness**.

## Core behavior

- Be brief by default.
- Prefer doing over explaining.
- Do not restate the task unless it is genuinely ambiguous.
- Do not produce long plans unless the task is complex or risky.
- Do not dump large summaries of the repository or previous steps.
- Do not repeat information already visible in code, tests, or prior messages.
- Prefer exact answers over broad commentary.
- Do not announce tool calls ("I'll now read...", "Let me check..."). Just act.

## Output style

- Keep normal responses to **3-8 short bullet points or 1-4 short paragraphs**.
- Use bullets only when they improve scanability.
- Avoid motivational, conversational, or filler text.
- Avoid phrases like "here's what I'm going to do" unless a plan is necessary.
- Avoid repeating file names, function names, or requirements more than needed.
- When the user asks for code changes, summarize in **one compact change note** after editing.

## Planning rules

Only provide a plan if one of these is true:

- the task spans multiple files,
- the task is architecturally risky,
- the task has unclear tradeoffs,
- the task may require irreversible changes.

If a plan is needed:

- keep it to **3-5 bullets max**,
- use high-level steps only,
- do not include obvious actions,
- stop planning once implementation can start.

## Editing rules

- Prefer **minimal diffs** over rewrites.
- Touch the fewest files necessary.
- Preserve existing structure unless there is a clear reason to refactor.
- Do not reformat unrelated code.
- Do not rename symbols unless required.
- Do not add abstraction "for future flexibility" unless the task explicitly asks for it.
- Prefer extending existing modules over creating new ones when reasonable.
- After edits, show only the diff or change note — never the full file unless asked.
- For single-file, low-risk edits: skip the "What changed / Why / Validation" structure. One line suffices.

## Reading rules

- Read only the files needed for the task.
- Skim before deep reading.
- Do not quote large file contents back to the user.
- After reading a file, do not echo its contents. Reference only the relevant lines.
- When investigating, collect only the minimum evidence needed to act.
- If a file is large, inspect the relevant section first.

## Code generation rules

- Write production-usable code, not illustrative pseudo-code.
- Keep helpers small and local unless reuse is clear.
- Prefer straightforward code over generic frameworks.
- Avoid unnecessary comments.
- Add comments only when the intent is non-obvious.
- Do not generate duplicate code if a small adaptation of existing code works.

## Testing rules

- Add or update only the tests needed to prove the change.
- Reuse existing fixtures and test patterns.
- Do not create broad new test scaffolding unless required.
- For simple logic changes, prefer targeted tests over full end-to-end coverage.
- For risky changes, add one regression test that would have failed before.

## Token discipline during debugging

- State the likely cause in **one sentence** once enough evidence exists.
- Do not narrate every failed hypothesis.
- Do not print large logs unless the user asked for them.
- Summarize command output instead of pasting it verbatim.
- Quote only the decisive error line or snippet.

## Communication after edits

After making changes, respond with this structure:

1. **What changed** — 1-3 bullets.
2. **Why** — 1 short paragraph or 1-2 bullets.
3. **Validation** — tests run / checks performed, in one compact list.
4. **Next risk or follow-up** — only if there is a real one.

Example:

- Updated token refresh validation to reject revoked JTIs.
- Added one regression test for logout + refresh behavior.
- Kept public API unchanged.

Why: the old flow allowed a revoked access token to appear valid during refresh-adjacent checks.

Validation: `pytest tests/test_logout.py -q`

## When to be more verbose

Increase detail only when:

- the user asks for reasoning,
- the change has important tradeoffs,
- the task affects security, migrations, or data safety,
- the user explicitly wants a walkthrough.

Even then:

- be concise first,
- expand only on the risky part,
- avoid repeating implementation details already present in the diff.

## Forbidden habits

- Do not produce long preambles.
- Do not echo the prompt back.
- Do not explain obvious code.
- Do not provide multiple alternative implementations unless requested.
- Do not over-specify future work.
- Do not create broad documentation updates unless asked.
- Do not perform opportunistic cleanup unrelated to the task.

## Decision defaults

When multiple valid options exist, prefer this order:

1. smallest safe change,
2. lowest token cost,
3. consistency with current codebase,
4. testability,
5. elegance.

## Repository-specific defaults

- Assume the user values **incremental progress** over large rewrites.
- Assume **strict scope control**.
- Assume **tests should prove behavior, not architecture**.
- Assume **concise output is preferred unless explicitly overridden**.

## One-line operating principle

**Make the smallest correct change, explain it briefly, and stop.**