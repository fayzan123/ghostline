"""
chox_context.py — Single source of truth for the Chox product context
string injected into Claude prompts (email generation and ICP scoring).

This used to live at docs/CHOX_CONTEXT.md. It was moved into a Python
constant so the repository no longer carries a standalone marketing
document on disk: anything that needs the context imports CHOX_CONTEXT
from here.
"""

CHOX_CONTEXT = """\
# Chox — Product Context

## What Chox Is

Chox is an AI agent governance layer — infrastructure that sits between
an AI agent and the external APIs it calls. Its purpose is to give
developers visibility into what their agents are doing at the action
level, classify those actions by risk, and ultimately allow teams to
enforce policies that prevent dangerous or unintended agent actions from
executing.

The core problem Chox solves: AI agents are increasingly being given
access to real tools — payment APIs, databases, communication platforms,
file systems. An agent making a Stripe charge, running a SQL query, or
sending a Slack message is not a hypothetical risk. It is a production
reality. Existing observability tools (LangSmith, Langfuse) record what
an LLM said and how long it took. They do not classify whether an action
was dangerous, and they cannot stop it. Chox operates one layer lower,
at the point where the agent's decision becomes an API call, and
governs that layer.

## The Two Integration Paths

Chox offers two complementary ways to integrate:

1. HTTP Proxy. The developer points their tool's base URL at their Chox
   project URL. No code changes to the agent itself. Every outbound API
   call passes through Chox, which inspects, classifies, logs, and
   evaluates it before forwarding to the real destination.

2. SDK (Python and TypeScript). The developer wraps individual tool
   functions using the Chox SDK's guard.wrap() pattern. The wrapped
   function behaves identically to the original, but every invocation
   is logged, classified, and evaluated by Chox before execution.

Both paths feed the same pipeline: classification, risk scoring, shadow
verdict evaluation, logging, and (when enforcement is enabled) blocking.

## What Chox Does to Every Request

1. Action Classification. The request is classified by action type:
   read, write, delete, or financial. A POST /v1/charges to Stripe is
   classified as financial. A DELETE FROM users is classified as delete.

2. Risk Scoring. A risk score between 0 and 1 is assigned. The scoring
   is argument-aware: a Stripe charge for $500 scores differently than
   one for $50,000. Financial baselines, SQL destructiveness, bulk
   operation indicators, and PII signals all feed the score.

3. Content Inspection. Optional gates inspect the request body for
   secrets, PII, denied keywords, or disallowed URLs.

4. Shadow Verdict. A verdict (allow, block, or escalate) is generated
   based on current policy rules. In shadow mode, the default, this
   verdict is recorded but does not affect the request. The developer
   can see what would have been blocked without any production impact.

5. Logging. Every request is written to the audit log.

6. Enforcement (when enabled). In enforce mode, a block verdict stops
   execution. The SDK raises a ChoxBlockedError. The agent never calls
   the underlying API.

## Shadow Verdicts

Shadow verdicts are Chox's primary differentiator. The standard problem
with AI governance is that nobody wants to turn on enforcement in
production. If you misconfigure a rule, you break your agent. Shadow
mode resolves this: every call is evaluated against the full policy
engine and receives a real verdict, but that verdict is invisible to
the agent. The developer watches the dashboard, sees what would have
been blocked, tunes the rules, and only then flips enforcement on.

## What Chox Is Not

- Not an LLM observability tool. Chox does not trace prompt I/O, token
  counts, or LLM latency. LangSmith and Langfuse solve that.
- Not an output validator. Guardrails AI and similar tools validate
  LLM-generated text. Chox operates after the LLM has already decided
  to call a tool.
- Not a routing layer. Chox does not orchestrate multi-agent workflows.
- Not platform-locked. Chox works with any framework that makes HTTP
  calls or wraps Python/TypeScript functions.

## Who Uses Chox and Why

Primary user: a developer building an AI agent that touches real
external APIs, using a framework like LangGraph, LangChain, CrewAI, or
AutoGen, whose agent has been given tools that can move money, modify
databases, send communications, or otherwise create real-world side
effects.

Their problem: they can see what their LLM is generating but they
cannot see what their agent is doing at the action level. They have no
safe path to enforcement.

What they get from Chox: every tool call classified, scored, and logged
with a shadow verdict from day one. A clear, safe path to enforcement
when they are ready.

## Technical Characteristics

- Zero framework lock-in.
- Fail-open by default. If Chox itself errors, the underlying request
  goes through.
- Caller token authentication. Each agent instance authenticates with a
  scoped caller token. Tokens are SHA-256 hashed server-side.
- Async logging. The proxy path never waits for a DB write.
- Python SDK (chox-ai-sdk) and TypeScript SDK (@chox-ai/sdk).

## The Meaningful Distinction

LangSmith governs what the LLM says. Chox governs what the agent does.
"""
