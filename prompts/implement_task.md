# Prompt: Implement Task

Use this prompt when you want an AI coding tool to implement a specific task from `tasks.md`.

---

## How to Use

1. Copy the prompt below into your AI coding tool
2. Replace all `{{ placeholder }}` values with real content
3. Attach or paste relevant spec sections as context
4. Review the output against the acceptance criteria before accepting

---

## Prompt

```
You are implementing a task for a software project. Follow the architecture and coding standards defined below exactly.

## Task

**ID:** {{ TASK-ID }}
**Title:** {{ Task title from tasks.md }}
**Description:** {{ Full description of what needs to be built }}

## Acceptance Criteria

{{ Copy the acceptance criteria from specs/requirements.md or tasks.md }}

## Architecture Context

{{ Paste the relevant section of architecture.md, including:
   - Tech stack
   - Coding standards
   - Relevant design principles }}

## Spec References

{{ Paste the relevant sections from specs/api.md and/or specs/schema.md }}

## Dependencies

The following has already been implemented and can be used:
{{ List any existing functions, modules, or interfaces this task can rely on }}

## Instructions

- Implement only what is described in the task — do not add extra features
- Follow the coding standards in the architecture section exactly
- Write code that is readable and maintainable
- Include inline comments only where the logic is non-obvious
- If you need to make an assumption, state it explicitly before writing code
- Do not introduce new dependencies without flagging them first
```

---

## Tips

- Keep tasks small — one task per prompt session produces better results
- If a task is too large, split it in `tasks.md` before prompting
- After implementation, use `prompts/code_review.md` to review the output
- After implementation, use `prompts/generate_tests.md` to add test coverage
