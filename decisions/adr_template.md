# ADR Template

An **Architecture Decision Record (ADR)** documents a significant design or technology decision made during the project. Copy this file and rename it `adr_NNN_short-title.md` (e.g., `adr_001_choose-database.md`).

ADRs are append-only — once written, they should not be deleted. If a decision is reversed, create a new ADR that supersedes the old one.

---

# ADR NNN — Decision Title

**Date:** YYYY-MM-DD
**Status:** Proposed | Accepted | Deprecated | Superseded by ADR-NNN
**Deciders:** _List of people involved in the decision_

---

## Context

> What is the situation or problem that prompted this decision? What forces are at play — technical, business, organizational?

_Describe the background and why a decision is needed. Include any constraints or requirements that shaped the options._

---

## Decision Drivers

> What are the most important factors in making this decision?

- _Driver 1 (e.g., must work within existing infrastructure)_
- _Driver 2 (e.g., team has no experience with X)_
- _Driver 3 (e.g., needs to be production-ready within 4 weeks)_

---

## Options Considered

### Option A — _Option Name_

_Brief description of this option._

**Pros:**
- _Pro 1_
- _Pro 2_

**Cons:**
- _Con 1_
- _Con 2_

---

### Option B — _Option Name_

_Brief description of this option._

**Pros:**
- _Pro 1_

**Cons:**
- _Con 1_

---

### Option C — _Option Name_ _(if applicable)_

_Brief description of this option._

**Pros:**
- _Pro 1_

**Cons:**
- _Con 1_

---

## Decision

> What was decided and why?

We chose **Option A** because _[primary reasoning]_.

_Explain how this option best satisfies the decision drivers. Note any trade-offs accepted._

---

## Consequences

### Positive
- _What becomes easier or better as a result of this decision_

### Negative
- _What becomes harder or worse as a result of this decision_
- _Technical debt or limitations introduced_

### Risks
- _What could go wrong, and how it would be mitigated_

---

## Links

- Related ADRs: _ADR-NNN_
- Relevant specs: _specs/api.md, specs/schema.md_
- External references: _links to documentation, articles, or prior art_
