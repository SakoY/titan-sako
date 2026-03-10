# Project Title

> Replace this with your project name and a one-line description.

---

## What This Repository Is

This repository is structured for **spec-driven AI development** — a workflow where you define what to build before writing any code, then use AI coding tools to implement it systematically.

The core idea: well-structured specs and architecture documentation produce better AI-assisted output than ad-hoc prompting.

---

## Workflow Overview

```
architecture.md  →  tasks.md  →  prompts/  →  implementation
     ↑                                              ↓
  specs/                                       decisions/
```

### Step 1 — Define Architecture
Fill out [architecture.md](architecture.md) with your project goals, tech stack, and design principles. This is the single source of truth for all downstream decisions.

### Step 2 — Define Specs
Fill out the files in [specs/](specs/) to document:
- System requirements → `specs/requirements.md`
- API contracts → `specs/api.md`
- Data schema → `specs/schema.md`

### Step 3 — Generate Tasks
Once architecture and specs are stable, use [tasks.md](tasks.md) to break the work into discrete, AI-implementable units.

### Step 4 — Implement with AI
Use the prompt templates in [prompts/](prompts/) with your AI coding tool of choice. Each template is designed to be filled in with context from `architecture.md`, `specs/`, and `tasks.md`.

### Step 5 — Record Decisions
When a significant architectural or design decision is made, create an ADR using the template in [decisions/adr_template.md](decisions/adr_template.md).

---

## Directory Reference

| Path | Purpose |
|------|---------|
| `architecture.md` | Goals, principles, tech stack, coding standards |
| `tasks.md` | Breakdown of implementation work |
| `specs/requirements.md` | Functional and non-functional requirements |
| `specs/api.md` | API contract definitions |
| `specs/schema.md` | Data model and schema definitions |
| `prompts/implement_task.md` | AI prompt for implementing a task |
| `prompts/code_review.md` | AI prompt for reviewing code |
| `prompts/generate_tests.md` | AI prompt for generating tests |
| `prompts/architecture_review.md` | AI prompt for reviewing architecture |
| `prompts/refactor.md` | AI prompt for targeted refactoring |
| `decisions/adr_template.md` | Template for architecture decision records |
| `docs/notes.md` | Freeform design notes and discussions |

---

## Getting Started

1. Read `architecture.md` and fill in the project overview and goals
2. Complete `specs/requirements.md` with what the system must do
3. Fill in `specs/api.md` and `specs/schema.md` as you design the system
4. Populate `tasks.md` with implementation tasks derived from the specs
5. Use prompts from `prompts/` with your AI tool to implement each task
