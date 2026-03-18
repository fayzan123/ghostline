# Ghostline Outreach Agent — Phased Build Plan

This document divides the implementation of the LangGraph outreach agent (specified in `OUTREACH_AGENT_PLAN.md`) into 6 sequential phases. Each phase has a single clear goal, produces specific files, and is assigned to the most appropriate agent. Each phase depends on the previous one being complete.

---

## Dependency Graph

```
Phase 1 (Scaffolding)
    |
    v
Phase 2 (Data Access)
    |
    +---> Phase 3 (Email Generator)  ─┐  (3 and 4 are independent of each other)
    |                                  │
    +---> Phase 4 (Email Sender)    ─┘
                                       |
                                       v
                                   Phase 5 (LangGraph Graph)
                                       |
                                       v
                                   Phase 6 (CLI + Entry Point)
```

---

## Phase 1 — Project Scaffolding

**Goal:** Lay the entire foundation before any logic is written. Create the `outreach/` package, define the state schema every other module depends on, write the config module, install new dependencies, and extend the existing `GitHubClient` with README fetching.

**Assigned agent:** `Backend Architect`

**Suggested model:** `claude-sonnet-4-6` — scaffolding is well-defined structural work with no ambiguity; Sonnet handles it cleanly without needing Opus-level reasoning.

**Why this agent:** Pure structural Python — package layout, TypedDict definitions, constants, env var loading, and a single new API method on an existing class. No AI/ML logic, no complex protocol handling. Backend Architect is the right fit for clean, dependency-free scaffolding that the rest of the build depends on.

**Files to produce:**

| File                          | Action                             |
| ----------------------------- | ---------------------------------- |
| `outreach/__init__.py`        | Create (empty)                     |
| `outreach/outreach_config.py` | Create                             |
| `outreach/outreach_state.py`  | Create                             |
| `requirements.txt`            | Update — add new packages          |
| `discovery/github_client.py`  | Extend — add `get_readme()` method |

**Instructions:**

Read `OUTREACH_AGENT_PLAN.md` in full — specifically Sections 9 and 10 — then build the scaffolding. Create the `outreach/` package with a config module that loads all outreach settings from environment variables and fails loudly on missing credentials, a state module that defines the two TypedDicts with no project imports, updated dependencies in `requirements.txt`, and a `get_readme()` method on the existing `GitHubClient` that follows the same patterns already used in that class. Make all design decisions yourself based on what you read in the plan.

---

## Phase 2 — Data Access Layer

**Goal:** Build the two modules that reach out to external data sources — Google Sheets (read uncontacted leads, write back status) and GitHub (fetch READMEs). These are pure I/O modules with no LangGraph awareness.

**Assigned agent:** `Backend Architect`

**Suggested model:** `claude-sonnet-4-6` — I/O layer work with clear inputs and outputs; Sonnet can read the existing sheets patterns and replicate them reliably.

**Why this agent:** This is database/API integration work — reading records, filtering, mapping to typed structures, writing batched updates with retry logic. The Backend Architect specializes in exactly this kind of reliable, efficient I/O layer. The existing `shared/sheets.py` patterns must be reused correctly, which requires understanding the existing code architecture.

**Files to produce:**

| File                          | Action |
| ----------------------------- | ------ |
| `outreach/outreach_sheets.py` | Create |
| `outreach/readme_fetcher.py`  | Create |

**Instructions:**

Read `OUTREACH_AGENT_PLAN.md` — particularly Section 7 — and the existing `shared/sheets.py` to understand the patterns already in place. Build the Sheets module that loads uncontacted leads and writes back send outcomes, reusing the existing helpers rather than reimplementing them. Build the README fetcher that translates lead records into `get_readme()` calls. Own all design decisions within the constraints the plan specifies.

---

## Phase 3 — Email Generation Engine

**Goal:** Build the Claude API integration that takes a lead dict plus README text and produces a personalized cold email. This includes loading product context, constructing the system and user prompts, calling the Claude API, parsing the structured response, and validating output. emails should not include anything typical to AI like em dashes and whatnot

**Assigned agent:** `AI Engineer`

**Suggested model:** `claude-opus-4-6` — prompt design is the highest-leverage work in the entire project; Opus produces meaningfully better system prompts, output format decisions, and edge case handling than Sonnet.

**Why this agent:** This phase is entirely about integrating the Anthropic SDK, designing effective prompts, handling structured LLM output, and implementing retry logic for AI API calls. The AI Engineer specializes in exactly this — building reliable AI-powered features with proper error handling, token management, and response parsing.

**Files to produce:**

| File                          | Action |
| ----------------------------- | ------ |
| `outreach/email_generator.py` | Create |

**Instructions:**

Read `OUTREACH_AGENT_PLAN.md` — particularly Section 5 — and `docs/CHOX_CONTEXT.md`. Build the email generation module that uses the Anthropic SDK to produce personalized cold emails from lead data and README content. Design the prompts, output format, parsing strategy, retry logic, and error handling yourself based on what you find in the plan and the product context file.

---

## Phase 4 — Email Delivery Module

**Goal:** Build the SMTP sending module that handles Outlook.com connection, MIME message construction, send pacing, CAN-SPAM compliance in message headers, bounce detection, and per-email error handling.

**Assigned agent:** `Backend Architect`

**Suggested model:** `claude-sonnet-4-6` — SMTP and MIME are well-documented protocols; Sonnet knows them thoroughly and can implement the deliverability requirements without needing deeper reasoning.

**Why this agent:** SMTP protocol handling, MIME construction, rate limiting, and network error handling are squarely in backend infrastructure territory. The deliverability requirements — pacing, correct headers, CAN-SPAM compliance — require careful, methodical implementation rather than AI expertise.

**Files to produce:**

| File                       | Action |
| -------------------------- | ------ |
| `outreach/email_sender.py` | Create |

**Instructions:**

Read `OUTREACH_AGENT_PLAN.md` — particularly Sections 3 and 4 — then build the SMTP sending module. You own all decisions about connection management, message construction, pacing, error classification, and CAN-SPAM compliance. The plan has the full spec; implement it the way a senior backend engineer would.

---

## Phase 5 — LangGraph Orchestrator

**Goal:** Build the core `outreach_graph.py` — the LangGraph `StateGraph` that wires all the preceding modules together into a stateful, interruptible workflow. This includes all 8 node functions, the conditional edges, the `SqliteSaver` checkpointer setup, and the `interrupt_before` configuration for the human review gate.

**Assigned agent:** `AI Engineer`

**Why this agent:** LangGraph is an AI orchestration framework. Building a `StateGraph` with interrupts, conditional edges, checkpoint persistence, and the `Command(resume=...)` pattern for human-in-the-loop requires deep familiarity with the LangGraph API. This is AI infrastructure work, not general backend work.

**Files to produce:**

| File                         | Action |
| ---------------------------- | ------ |
| `outreach/outreach_graph.py` | Create |

**Instructions:**

Read `OUTREACH_AGENT_PLAN.md` — particularly Sections 2 and 6 — then read all the modules built in Phases 1–4 to understand what each one exposes. Wire them into a LangGraph `StateGraph` with the correct nodes, edges, interrupt, and checkpointer. All architectural decisions about how to structure the graph are yours to make based on the plan.

---

## Phase 6 — Review CLI & Entry Point

**Goal:** Build the interactive terminal review interface that operates in the human-in-the-loop gap, and the `run_outreach.py` entry point that wires everything together with argument parsing, handles `--resume` and `--dry-run` flags, and manages the full run lifecycle.

**Assigned agent:** `Backend Architect`

**Why this agent:** Terminal UI design, argparse, subprocess and editor integration, and the glue connecting all modules into a single runnable script are pure backend and systems work. The Backend Architect is suited for building reliable, user-facing CLI tools with clean error handling and clear UX.

**Files to produce:**

| File                     | Action |
| ------------------------ | ------ |
| `outreach/review_cli.py` | Create |
| `run_outreach.py`        | Create |

**Instructions:**

Read `OUTREACH_AGENT_PLAN.md` — particularly Section 6 — then read the completed `outreach_graph.py` from Phase 5. Build the review CLI that collects operator decisions in the human-in-the-loop gap, and the entry point that manages the full run lifecycle including `--dry-run`, `--batch-size`, and `--resume`. Make all UX and implementation decisions yourself.

---

## Summary Table

| Phase | Goal                                                                           | Files                                                                                                                                 | Agent             |
| ----- | ------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------- | ----------------- |
| 1     | Scaffolding — config, state schema, github_client extension                    | `outreach/__init__.py`, `outreach/outreach_config.py`, `outreach/outreach_state.py`, `requirements.txt`, `discovery/github_client.py` | Backend Architect |
| 2     | Data access — Sheets I/O and README fetching                                   | `outreach/outreach_sheets.py`, `outreach/readme_fetcher.py`                                                                           | Backend Architect |
| 3     | Email generation — Claude API integration and prompt engine                    | `outreach/email_generator.py`                                                                                                         | AI Engineer       |
| 4     | Email delivery — SMTP sender with deliverability and pacing                    | `outreach/email_sender.py`                                                                                                            | Backend Architect |
| 5     | LangGraph orchestrator — full graph with nodes, edges, checkpointer, interrupt | `outreach/outreach_graph.py`                                                                                                          | AI Engineer       |
| 6     | CLI review interface + entry point                                             | `outreach/review_cli.py`, `run_outreach.py`                                                                                           | Backend Architect |

**Total new files:** 9 (`outreach/__init__.py`, `outreach_config.py`, `outreach_state.py`, `outreach_sheets.py`, `readme_fetcher.py`, `email_generator.py`, `email_sender.py`, `outreach_graph.py`, `review_cli.py`, `run_outreach.py`)
**Modified files:** 2 (`requirements.txt`, `discovery/github_client.py`)

After Phase 6 is complete, run `python run_outreach.py --dry-run` to verify the full pipeline end-to-end before sending a single real email.
