# Prompt: Generate Tests

Use this prompt when you want an AI coding tool to generate tests for a piece of implemented code.

---

## How to Use

1. Copy the prompt below into your AI coding tool
2. Replace all `{{ placeholder }}` values with real content
3. Paste the implementation to be tested
4. Review the generated tests for completeness and correctness before committing

---

## Prompt

```
You are writing tests for a software project. Generate thorough tests for the code provided below.

## Code to Test

{{ Paste the implementation to be tested }}

## What This Code Does

{{ Description from tasks.md or a brief explanation of the function/module's purpose }}

## Acceptance Criteria

{{ Copy the acceptance criteria from specs/requirements.md or tasks.md — each criterion should map to at least one test }}

## Testing Standards

{{ Paste testing conventions from architecture.md, e.g.:
   - Test framework: TBD
   - Naming convention: e.g., "should [do X] when [condition Y]"
   - What to mock vs. what to test with real implementations
   - Coverage requirements }}

## Test Scope

Generate tests for the following categories (mark N/A if not applicable):

1. **Happy path** — the expected successful behavior
2. **Edge cases** — boundary values, empty inputs, max inputs
3. **Error cases** — invalid inputs, missing required fields, unexpected states
4. **Integration points** — how this code interacts with dependencies (use mocks where appropriate)
5. **Acceptance criteria** — one test per criterion listed above

## Instructions

- Write tests that are readable and self-documenting
- Each test should have a clear name describing what it verifies
- Prefer explicit assertions over catch-all assertions
- Do not test implementation details — test observable behavior
- If a dependency needs to be mocked, explain the mocking approach
- Flag any behavior that cannot be tested without additional infrastructure
```

---

## Tips

- Run this after `prompts/implement_task.md` and alongside `prompts/code_review.md`
- If the acceptance criteria are unclear, clarify them in `specs/requirements.md` first
- Tests should be committed alongside implementation, not as an afterthought
