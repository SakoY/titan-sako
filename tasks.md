# Tasks

This file tracks the implementation work for the project. Tasks should be derived from `architecture.md` and `specs/` — not invented ad-hoc. Each task should be small enough to implement in a single AI-assisted session.

---

## How to Use This File

1. Complete `architecture.md` and the `specs/` files first
2. Break the system into discrete, implementable units (tasks)
3. Order tasks by dependency — earlier tasks should not depend on later ones
4. For each task, use a prompt from `prompts/implement_task.md` with your AI tool

---

## Task States

| Symbol | Meaning |
|--------|---------|
| `[ ]` | Not started |
| `[~]` | In progress |
| `[x]` | Complete |
| `[!]` | Blocked |

---

## Milestones

### Milestone 1 — Foundation
> _Describe what "done" looks like for this milestone._

- [ ] **TASK-001** — _Task name_
  - Description: _What needs to be built_
  - Depends on: _nothing / TASK-00X_
  - Spec reference: `specs/requirements.md#section`
  - Prompt: `prompts/implement_task.md`

- [ ] **TASK-002** — _Task name_
  - Description: _What needs to be built_
  - Depends on: TASK-001
  - Spec reference: `specs/api.md#section`
  - Prompt: `prompts/implement_task.md`

### Milestone 2 — Core Features
> _Describe what "done" looks like for this milestone._

- [ ] **TASK-003** — _Task name_
  - Description: _What needs to be built_
  - Depends on: TASK-002
  - Spec reference: `specs/schema.md#section`
  - Prompt: `prompts/implement_task.md`

---

## Backlog (Unscheduled)

> Tasks identified but not yet assigned to a milestone.

- [ ] _Future task idea_

---

## Completed

> Move tasks here once done, for a record of what was built.

<!-- Example:
- [x] **TASK-001** — Project scaffolding
  - Completed: YYYY-MM-DD
-->
