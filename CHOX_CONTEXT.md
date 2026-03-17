# Chox — Product Context

*This document provides context about what Chox is and what it does. It is intended to be fed to an AI as background context when reasoning about outreach, messaging, or positioning tasks.*

---

## What Chox Is

Chox is an **AI agent governance layer** — infrastructure that sits between an AI agent and the external APIs it calls. Its purpose is to give developers visibility into what their agents are doing at the action level, classify those actions by risk, and ultimately allow teams to enforce policies that prevent dangerous or unintended agent actions from executing.

The core problem Chox solves: AI agents are increasingly being given access to real tools — payment APIs, databases, communication platforms, file systems. An agent making a Stripe charge, running a SQL query, or sending a Slack message is not a hypothetical risk. It is a production reality. Existing observability tools (LangSmith, Langfuse) record what an LLM said and how long it took. They do not classify whether an action was dangerous, and they cannot stop it. Chox operates one layer lower — at the point where the agent's decision becomes an API call — and governs that layer.

---

## The Two Integration Paths

Chox offers two ways to integrate, which are complementary rather than competing:

### 1. HTTP Proxy

The developer points their tool's base URL at their Chox project URL instead of the real API endpoint. No code changes to the agent itself. Every outbound API call passes through Chox, which inspects, classifies, logs, and evaluates it before forwarding to the real destination. From the agent's perspective, nothing has changed. From Chox's perspective, every call is now observable and governable.

**Best for:** Teams that want network-level visibility across all outbound API traffic without modifying agent code.

### 2. SDK (Python + TypeScript)

The developer wraps individual tool functions using the Chox SDK's `guard.wrap()` pattern. The wrapped function behaves identically to the original — it calls the same underlying API — but every invocation is logged, classified, and evaluated by Chox before execution.

```python
guard = ChoxGuard(base_url="https://chox.ai/my-project", token="chox_token_...")
charge = guard.wrap("stripe.create_charge", stripe.Charge.create)
```

**Best for:** Framework-integrated agents (LangGraph, LangChain, CrewAI, custom pipelines) where the developer wants fine-grained per-tool governance.

Both paths feed the same pipeline: classification, risk scoring, shadow verdict evaluation, logging, and — when enforcement is enabled — blocking.

---

## What Chox Does to Every Request

When a tool call passes through Chox (via proxy or SDK), the following happens:

1. **Action Classification** — The request is classified by action type: `read`, `write`, `delete`, or `financial`. This is determined by semantic analysis of the API endpoint, HTTP method, and request body. A `POST /v1/charges` to Stripe is classified as `financial`. A `DELETE FROM users` is classified as `delete`. A `GET /messages` is classified as `read`.

2. **Risk Scoring** — A risk score between 0 and 1 is assigned. The scoring is argument-aware: a Stripe charge for $500 scores differently than one for $50,000. A `SELECT *` scores differently than a `DROP TABLE`. Financial baselines, SQL destructiveness, bulk operation indicators, and PII signals all feed the score.

3. **Content Inspection** — Optional gates inspect the request body for secrets (API keys, tokens), PII (emails, phone numbers, SSNs), denied keywords, or disallowed URLs. A request containing a raw API key being forwarded to an external service can be flagged before it leaves.

4. **Shadow Verdict** — A verdict (`allow`, `block`, or `escalate`) is generated based on the current policy rules. In shadow mode — the default — this verdict is recorded but does not affect the request. The agent continues normally. The developer can see what *would have been blocked* without any production impact.

5. **Logging** — Every request is written to the audit log: action type, risk score, shadow verdict, reason string, request/response metadata, caller identity, timestamp. This log is queryable from the dashboard.

6. **Enforcement (when enabled)** — In enforce mode, a `block` verdict stops execution. The SDK raises a `ChoxBlockedError`. The agent never calls the underlying API. This is the circuit breaker.

---

## Shadow Verdicts — The Key Concept

Shadow verdicts are Chox's primary differentiator from every observability tool in the space.

The standard problem with AI governance is that nobody wants to turn on enforcement in production. If you misconfigure a rule, you break your agent. So teams observe, worry, and do nothing.

Shadow mode resolves this. Every call gets evaluated against the full policy engine and receives a real verdict — but that verdict is invisible to the agent. The developer watches the dashboard, sees that their agent *would have been blocked* three times last week (and why), inspects those cases, tunes the rules if needed, and only then flips enforcement on. The transition from observation to enforcement happens with full confidence rather than as a gamble.

This is the path from "I want to govern my agents" to "my agents are governed."

---

## What Chox Is Not

Understanding the boundaries is as important as understanding the capabilities:

- **Not an LLM observability tool.** Chox does not trace prompt inputs/outputs, token counts, or LLM latency. Those are solved problems (LangSmith, Langfuse). Chox governs what the agent *does*, not what the LLM *says*.
- **Not an output validator.** Guardrails AI and similar tools validate the text or structured data an LLM produces. Chox operates after the LLM has already decided to call a tool — it governs the action, not the generation.
- **Not a routing layer.** Chox does not route traffic between agents or orchestrate multi-agent workflows. It sits in the data plane of individual tool calls.
- **Not platform-locked.** Chox works with any framework that makes HTTP calls or wraps Python/TypeScript functions. It has no dependency on LangChain, OpenAI, or any specific LLM provider.

---

## The Dashboard

Chox ships with a web dashboard at `chox.ai/dashboard`. It provides:

- **Logs page** — Full audit log of every request: action type, risk score, shadow verdict, reason string, integration, caller, timestamp. Filterable by action type, verdict, and free-text search.
- **Visualizations** — Charts showing request volume over time, action type breakdown, and per-integration traffic distribution.
- **AI Systems page** — Manage caller tokens (the credentials agent instances use to authenticate to Chox).
- **Integrations page** — Configure integration targets (the real APIs Chox proxies to).
- **Rules page** — Define content inspection rules (keyword deny, URL allow/block, PII detection, secrets detection, gate enable).
- **Disputes page** — Review flagged requests, approve or reject disputes, manage the allowlist for fingerprint-based suppression of known-safe patterns.
- **Settings page** — Project configuration including financial thresholds and enforcement mode.

---

## Who Uses Chox and Why

**Primary user:** A developer building an AI agent that touches real external APIs. They are using an agentic framework — LangGraph, LangChain, CrewAI, AutoGen, or a custom pipeline — and their agent has been given tools that can move money, modify databases, send communications, or otherwise create real-world side effects.

**Their problem:** They can see what their LLM is generating (via existing tools) but they cannot see what their agent is *doing* at the action level in a structured, risk-classified way. They have no safe path to enforcement. They are either flying blind in production or blocking progress with manual review.

**What they get from Chox:** Every tool call classified, scored, and logged with a shadow verdict from day one. A clear, safe path to enforcement when they're ready. Two lines of SDK code or a URL change to get started.

**The broader context:** The teams most likely to feel this pain acutely are those operating in environments where a bad agent action has real consequences — financial services (an agent that moves money), healthcare technology (an agent that accesses patient data), developer tooling (an agent that can modify production infrastructure), and any SaaS product where agents are being given write access to customer data.

---

## Technical Characteristics Relevant to Developers

- **Zero framework lock-in.** The SDK wraps any callable. The proxy intercepts any HTTP call. No LangChain dependency required.
- **Fail-open by default.** If Chox itself errors, the underlying request goes through. Governance failures never block production traffic.
- **Caller token authentication.** Each agent instance authenticates with a scoped caller token. Tokens are SHA-256 hashed server-side and shown once on creation. Different agents get different tokens — the audit log records which caller made each request.
- **Single-binary deployment.** Chox is a single Go binary with embedded assets and auto-running migrations. `docker run` or `fly deploy` — no orchestration required.
- **Async logging.** All logging is non-blocking. The proxy path never waits for a DB write. Batched, buffered, fail-open.
- **Language support.** Python SDK (`chox-ai-sdk`) and TypeScript SDK (`@chox-ai/sdk`). Both are zero-dependency.

---

## Competitive Context (Brief)

The tools developers commonly compare Chox to:

| Tool | What it does | Gap Chox fills |
|------|-------------|----------------|
| LangSmith | Traces LLM calls, token usage, prompt I/O | Does not classify actions by risk or block anything |
| Langfuse | Open-source observability and evals | Does not classify actions by risk or block anything |
| agentgateway | Routes traffic between agents and MCP servers | No policy engine, no classification, no verdicts |
| Guardrails AI | Validates LLM text/structured output | Governs LLM outputs, not tool call actions |

The meaningful distinction: **LangSmith governs what the LLM says. Chox governs what the agent does.**

---

## Current State of the Product

Chox is a live, deployed product at chox.ai. The core proxy, classification engine, risk scoring, shadow verdict system, content inspection gates, dashboard, dispute/allowlist system, and both SDKs are built and functional. Active enforcement mode (where Chox can actually block calls in production) is on the near-term roadmap. The product is currently in the pre-launch, pre-external-user phase — technically complete for the shadow-mode governance use case, being prepared for its first wave of developer users.
