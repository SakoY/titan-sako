# Prompt: Refactor

Use this prompt when you want an AI coding tool to improve existing code without changing its external behavior.

---

## How to Use

1. Copy the prompt below into your AI coding tool
2. Replace all `{{ placeholder }}` values with real content
3. Be specific about the refactoring goal — unfocused refactoring produces unfocused results
4. Verify behavior is preserved by running existing tests after the refactor

---

## Prompt

```
You are refactoring existing code. Your goal is to improve the code's internal quality without changing its external behavior.

## Code to Refactor

{{ Paste the code to be refactored }}

## Refactoring Goal

{{ Describe what you want to improve. Be specific. Examples:
   - "Reduce duplication between these two functions"
   - "Break this function into smaller, single-responsibility units"
   - "Improve readability of the conditional logic"
   - "Rename variables and functions to better reflect their purpose"
   - "Extract repeated logic into a shared utility" }}

## Architecture and Standards

{{ Paste the relevant coding standards from architecture.md }}

## Constraints

- Do NOT change the external interface (function signatures, return shapes, exported names) unless explicitly asked
- Do NOT add new features or fix bugs — only improve internal structure
- Preserve all existing behavior, including error handling
- The refactored code must be compatible with existing tests

## Tests Available

{{ Describe or paste the existing tests that validate this code's behavior, if any }}

## Instructions

1. First, explain your refactoring plan before writing any code
2. List any assumptions you are making
3. Write the refactored code
4. Summarize what changed and why

## Output Format

**Plan:** _(your approach before writing code)_

**Assumptions:** _(anything assumed about the codebase or behavior)_

**Refactored Code:** _(the improved implementation)_

**Summary of Changes:**
- _Change 1 and rationale_
- _Change 2 and rationale_

**Verification:** _(how to confirm behavior is preserved)_
```

---

## Tips

- Always run tests before and after refactoring to catch regressions
- Keep refactoring commits separate from feature or bug fix commits
- If you discover a bug during refactoring, note it and fix it in a separate task
- For large refactors, break into smaller steps and review each one with `prompts/code_review.md`
