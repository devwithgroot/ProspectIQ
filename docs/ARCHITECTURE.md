# Architecture

## Why two machines

The application does not load the model. The Mac mini M4 is an inference server. The app talks to it over HTTP.

```text
ProspectIQ app
  agents / EXCON / tools
        │
        │  POST /v1/chat/completions
        ▼
Mac mini :8080
  MLX-LM  →  mlx-community/Qwen3-8B-4bit
```

`LLMClient` is the only module that knows the MLX URL and model name. Agents call `llm.generate()`. Structured calls also run through `llm/json_util.py` (strip fences / `<think>`, retry once). Tavily is only used through `WebSearchTool`.

## Seller pipeline (current entry)

See [PIPELINE.md](PIPELINE.md). After signup fields + CSV, the orchestrator runs on the real APIs:

```text
name, phone, work email, outreach email, industry, title, website
        │
        ▼
WebsiteReaderTool + MLX     →  User + Products
        │
        ▼
CSV (company_name, ...)
        │
        ▼
ProspectIQ.analyze()  ×  each row
   MLX planner + Tavily + MLX score + MLX report
        │
        ▼
report_to_prospect()  →  data/runs/
```

## Two engines after that

```text
                    ┌─ ProspectIQ.analyze() ─┐
Company name + goal │  ResearchAgent         │
                    │  ScoringAgent          │
                    │  ReportAgent           │
                    └──────────┬─────────────┘
                               │ ProspectReport
                               ▼
                    report_to_prospect() → Prospect

                    ┌─ Excon.prepare() ──────┐
User + Products     │  OutreachAgent         │
Prospect            │  edit / approve / send │
Contacts + Profiles │  Connectors            │
                    └──────────┬─────────────┘
                               │ OutreachBatch + events
```

`analyze()` is company-level. EXCON still needs people. Contacts remain mock until a contact finder exists. `data/runs/` already has the researched `Prospect` objects.

## Phase 1 research loop

```text
ResearchState
    → LLM planner (search | finish)
    → WebSearchTool (Tavily)
    → EvidenceEvaluator (relevance + quality)
    → update state
    → repeat until finish or max_steps (5)
```

Python enforces guardrails: unknown actions, missing query, duplicate query, step cap. The model proposes; the app decides whether the action is allowed.

Scoring: the model rates five dimensions 0–100. Python applies fixed weights (expansion 25%, growth / technology / strategic 20%, hiring 15%) and a recommendation band (≥75 high-priority, ≥50 potential, else low).

The report agent writes the sales narrative but cannot change the score or recommendation.

## Phase 3 EXCON

```text
User + matched Products + Prospect + ContactProfile
    → skip if DNC / no handle / no consent
    → primary channel (preferred, else first eligible)
    → OutreachAgent (one LLM JSON draft)
    → seller edit
    → approve
    → Connector.send()   # refused unless approved
```

Connectors: email (SMTP), Slack (Web API), SMS (Twilio-shaped), WhatsApp (Cloud API-shaped), LinkedIn (official-API stub only, no scraping). `EXCON_DRY_RUN=true` by default.

## Tools

| Tool | Status | Used by |
|---|---|---|
| `WebSearchTool` | Live Tavily | Research agent |
| `WebsiteReaderTool` | Live fetch + readable text | Seller onboarding (`OnboardingAgent`) |
| `CompanyDataTool` | `NotImplementedError` | Future BDL / provider |
| `EvidenceEvaluator` | Keyword + domain heuristics | Research agent |
| `MockSearchTool` | Dev stub | Early tests only |

## Config

| File | Role |
|---|---|
| `config/schemas.py` | Research evidence, scores, `ProspectReport` |
| `config/catalog.json` | Closed `Industry` and `SellerTitle` lists, titles per industry |
| `config/excon_schemas.py` | User, Product, Prospect, Contact, Profile, drafts, events |
| `.env` | MLX, Tavily, connector keys. Never commit |

## What is not in the architecture yet

- Full app shell beyond the Next.js form (history, EXCON, auth)
- Signup / session persistence
- Persistence (DB / CRM)
- Contact discovery from Phase 1
- EXCON fed from pipeline runs (still mock contacts)
- Multi-touch sequences
- Rate limits
