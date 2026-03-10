# Architecture

This document is the single source of truth for the project's design. Fill it in before generating tasks or writing code. All implementation decisions should trace back to something defined here.

---

## Project Overview

> Describe what this system does and the problem it solves. 1–3 paragraphs.

**Name:** TBD

**Problem:** _What pain or gap does this project address?_

**Solution:** _What does this system do to address it?_

**Primary Users:** _Who uses this system and how?_

---

## Goals

### Must Achieve
- _Goal 1_
- _Goal 2_

### Should Achieve
- _Goal 3_

### Non-Goals (explicitly out of scope)
- _What this project will NOT do_

---

## Architecture Principles

These principles guide every design and implementation decision.

- **Simplicity first** — prefer the simpler solution unless there's a compelling reason not to
- **Explicit over implicit** — make behavior visible and traceable
- **Spec before code** — nothing is implemented without a corresponding spec or task
- **Incremental delivery** — design for small, deployable increments
- _Add project-specific principles here_

---

## Tech Stack

> Fill this in once a language, runtime, and framework have been decided.

| Layer | Choice | Rationale |
|-------|--------|-----------|
| Language | TBD | |
| Runtime | TBD | |
| Framework | TBD | |
| Data Store | TBD | |
| Auth | TBD | |
| Hosting | TBD | |
| CI/CD | TBD | |

---

## Coding Standards

> These will be enforced in code reviews and AI-generated code.

- _Naming conventions (files, variables, functions, types)_
- _Error handling approach_
- _Logging and observability expectations_
- _Test coverage requirements_
- _Documentation expectations (comments, docstrings, etc.)_
- _Formatting and linting tools (TBD)_

---

## System Design

### High-Level Components

> Describe the major parts of the system and how they relate. A diagram or bulleted list works.

```
[ Component A ] --> [ Component B ] --> [ Component C ]
```

### Data Flow

> Describe how data moves through the system for the primary use case.

1. _Step 1_
2. _Step 2_
3. _Step 3_

### Key Interfaces

> List the boundaries between major components. These will become API/schema specs.

- _Interface 1 (e.g., client ↔ server)_
- _Interface 2 (e.g., service ↔ database)_

### Scalability and Performance Considerations

- _Expected load and growth_
- _Bottlenecks to watch_
- _Caching or optimization strategies (if applicable)_

### Security Considerations

- _Authentication and authorization model_
- _Data sensitivity and handling_
- _Known threat vectors to address_

---

## Open Questions

> Things that still need a decision. Move items to `decisions/` once resolved.

- [ ] _Question 1_
- [ ] _Question 2_
