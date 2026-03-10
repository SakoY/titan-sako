# Prompt: Code Review

Use this prompt when you want an AI coding tool to review implemented code against the project's specs and standards.

---

## How to Use

1. Copy the prompt below into your AI coding tool
2. Replace all `{{ placeholder }}` values with real content
3. Paste the code to be reviewed inline or attach the relevant files
4. Use the output to guide revision before committing

---

## Prompt

```
You are performing a code review for a software project. Review the code below against the provided standards and spec.

## Code to Review

{{ Paste the code or describe the files to review }}

## Task Context

**Task ID:** {{ TASK-ID }}
**What this code is supposed to do:** {{ Description from tasks.md }}

## Architecture and Standards

{{ Paste the coding standards section from architecture.md }}

## Spec Reference

{{ Paste the relevant section from specs/api.md or specs/schema.md that this code implements }}

## Review Checklist

Evaluate the code against each of the following. For each item, state: Pass / Fail / N/A and explain why.

1. **Correctness** — Does the code do what the task requires? Does it satisfy the acceptance criteria?
2. **Standards compliance** — Does it follow the project's naming conventions, error handling, and formatting rules?
3. **Security** — Are there any injection risks, insecure defaults, or exposed secrets?
4. **Edge cases** — Are error conditions and edge cases handled appropriately?
5. **Readability** — Is the code easy to follow? Are complex sections explained?
6. **Scope creep** — Does the code do anything beyond what was asked?
7. **Test coverage** — Is there sufficient test coverage for the logic introduced?

## Output Format

For each issue found:
- **Severity:** Critical / Major / Minor / Suggestion
- **Location:** File and line reference (if applicable)
- **Issue:** What is wrong or could be improved
- **Recommendation:** What to change and why

Summarize with an overall verdict: Approved / Approved with minor changes / Changes required.
```

---

## Tips

- Run this after `prompts/implement_task.md` and before merging
- Critical issues must be resolved; suggestions are optional
- If changes are required, re-run `prompts/implement_task.md` with the review feedback as additional context
