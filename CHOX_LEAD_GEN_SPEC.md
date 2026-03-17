You are the Agents Orchestrator coordinating a parallel multi-agent session.

Activate the following agents simultaneously and have them collaborate:

- Outbound Strategist
- Growth Hacker

PRODUCT CONTEXT:
[PASTE CHOX_CONTEXT.MD HERE]

MISSION:
Research and produce a single exhaustive markdown document that serves as the master plan for building an automated tool that runs daily to find 50–100 qualified developer leads on GitHub who are actively building with LangChain or LangGraph, extract their public email from GitHub profile or commit data, and export them to a Google Sheet.

This plan will be handed directly to Claude coding agents to implement. Every decision must be researched, justified, and specific enough that no ambiguity remains at implementation time. Do not write vague recommendations. Write decisions.

CONSTRAINTS:

- GitHub API free tier only (authenticated: 5000 req/hr)
- Google Sheets as the lead database
- Python preferred
- Must run as a single command: python run.py
- Zero cost

QUALIFYING SIGNAL:
A lead is qualified if they meet ALL of the following:

- Has committed code to a repo that imports langgraph or langchain in the last 30 days
- The repo is not a fork of the official LangChain/LangGraph repos
- The repo is not a tutorial, course, or demo (research common patterns in repo names and descriptions to build a reliable filter list)
- Their GitHub profile or commit metadata contains a resolvable public email
- They have not been contacted before (checked against Google Sheet)

RESEARCH INSTRUCTIONS:

Outbound Strategist researches and documents:

- The exact ICP: who these developers are, what they are building, what pain they feel that Chox solves, and how to detect that pain from public GitHub signals
- Lead scoring criteria: what signals indicate tier 1 vs tier 2 (repo stars, commit frequency, README keywords like "production", "deployed", "API", team size indicators)

Growth Hacker researches and documents:

- The most efficient GitHub API search strategy to surface 50–100 qualified leads per day within rate limits — exact endpoints, query parameters, and pagination approach
- Email extraction methods: which GitHub API endpoints expose commit emails, how to parse profile bios for emails, known patterns and edge cases
- Google Sheets API setup and schema: exact column structure for the lead database, how deduplication is handled, how contacted status is tracked
- Rate limit management: how to calculate daily request budgets across all API calls and build in safe margins
- Full module architecture: every script the implementation will need, what each does, what it takes as input and returns as output, and how they connect

OUTPUT FORMAT:
Produce a single markdown file with the following sections:

1. Executive Summary (what this tool does, who it targets, why this approach)
2. ICP & Qualifying Signals (who we're targeting, how we identify them)
3. Lead Scoring Framework (tier 1 vs tier 2 criteria and logic)
4. GitHub Discovery Strategy (API approach, search queries, rate limit budget)
5. Email Extraction Strategy (methods, endpoints, fallbacks)
6. Lead Database Schema (Google Sheets column structure, deduplication logic)
7. Tool Architecture (ASCII diagram + module descriptions)
8. Module Specifications (for each module: purpose, inputs, outputs, logic, edge cases)
9. Setup Requirements (all API keys, OAuth configs, dependencies, environment variables needed)
10. Daily Run Sequence (exact order of operations when python run.py executes)
11. Known Risks & Mitigations (rate limits, false positives in lead scoring, GitHub ToS considerations)

Where the two agents disagree on an approach, document both options, state the tradeoff clearly, and make a final recommendation.
