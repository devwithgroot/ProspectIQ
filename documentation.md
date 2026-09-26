# ProspectIQ — Project Documentation

Consolidated reference for the ProspectIQ repository. Deeper topic guides live under [`docs/`](docs/) (see [Related documentation](#related-documentation)).

---

## Project Summary

**ProspectIQ** is local, agentic B2B sales intelligence: a seller shares who they are and their company website, uploads a list of prospect companies, and the system researches each firm on the public web, scores fit against the seller’s products, finds people at those companies, writes briefings, and (in a separate EXCON path) drafts channel-specific outreach that only sends after human approval.

At a glance:

| Layer | Role |
|--------|------|
| **Next.js UI** (`web/`) | Four-step seller form, prospect list/CSV, live research progress, briefing review |
| **FastAPI API** (`app/server.py`) | Catalog, CSV preview, async research jobs, optional outreach draft |
| **Python pipeline** (`app/pipeline.py`, `app/orchestrator.py`) | Onboarding → per-company research → people → saved JSON runs |
| **Agents + tools** (`agents/`, `tools/`, `llm/`) | MLX-backed planner/scoring/report/profile; Tavily search; Prospeo people search |
| **EXCON** (`app/excon.py`, `connectors/`) | Approval-gated outreach; dry-run by default |

Inference runs on a **separate Mac mini** (MLX-LM + Qwen3 8B 4-bit over HTTP), not inside the app process.

```text
Seller (browser or CLI)
        │  HTTP
        ▼
FastAPI :8000  →  agents / pipeline / EXCON
        │  POST /v1/chat/completions
        ▼
Mac mini MLX-LM :8080  →  Qwen3-8B-4bit
        │
Tavily / Prospeo / SMTP*  (*connectors optional)
```

---

## Project Overview

ProspectIQ exists to shorten the path from “I have a territory list” to “I know why this account matters, who to talk to, and what to say”—without auto-sending messages. The product assumes a **seller context** first: name, phone, work email, catalog industry/title, and company website. `OnboardingAgent` reads the site and asks the local MLX model to infer the seller’s company and product portfolio. Uploaded prospect rows (`company_name`, optional `website` and `notes`) drive **Phase 1–2** work: autonomous Tavily research (planner loop, evidence scoring), weighted fit scoring, company report, then Prospeo-backed people discovery and per-person briefings.

**Phase 3 (EXCON)** prepares one primary-channel draft per eligible contact, supports edit/approve/reject, and sends only through connectors when approved and credentialed—or logs a dry-run. **Phase 4** (analytics, full app shell, auth, DB) is largely unbuilt; events and JSON run files are the hooks for later UI.

The same pipeline runs from the **Next.js form** (`./run_app.sh`) or the **CLI** (`./run_pipeline.sh`). Until signup exists, the web app persists draft state in **browser localStorage** (`prospectiq-draft-v1`).

---

## Features

- **Seller onboarding** from company website (`WebsiteReaderTool` + MLX) → `User`, `SellerCompany`, `Product[]`
- **Closed catalog** for industry and title (`config/catalog.json`, mirrored in `web/lib/catalog-data.json`)
- **Prospect intake**: typed grid and/or CSV upload (max **5 MB**); duplicate company names dropped
- **Company website suggestion** from work-email domain (consumer domains excluded)
- **Live research per company**: planner + Tavily (up to 5 steps), evidence evaluation, MLX scoring and report
- **Deterministic scoring**: five dimensions 0–100 with fixed weights; recommendation bands enforced in Python
- **People at target companies**: Prospeo search (up to 3 per company), Tavily person lookup, MLX `ContactProfile`
- **Async research jobs** with progress, cancel, and skip-current-company (`data/jobs/`)
- **Persisted run output** under `data/runs/<timestamp>/` (full graph JSON, no database)
- **EXCON**: primary-channel drafts (email, LinkedIn, WhatsApp, Slack, SMS); DNC and consent gates; `EXCON_DRY_RUN` default **true**
- **API outreach draft** for a contact from a completed research `result` (`POST /api/outreach/draft`)
- **Optional outreach-email OTP** when `OTP_REQUIRED=true` and SMTP is configured
- **Script-style tests** under `tests/` (`python -m tests.test_*`, `python -m tests.run_ui`)

---

## Architecture

### Two-machine inference

The application never loads the LLM weights. `llm/client.py` (`LLMClient`) is the only module that knows `MLX_BASE_URL` and `MLX_MODEL`. Agents call `llm.generate()`; structured JSON flows through `llm/json_util.py` (fence/thinking stripping, one retry).

### Seller pipeline (primary entry)

```text
Form / CLI: identity + website + CSV
        │
        ▼
OnboardingAgent  →  User + Products
        │
        ▼
For each uploaded company_name
        │
        ▼
ProspectIQ.analyze()
   ResearchAgent   (Tavily loop)
   ScoringAgent    (MLX + fixed weights)
   ReportAgent     (MLX narrative)
        │
        ▼
report_to_company()  →  Company + CompanyProfile
        │
        ▼
PeopleDataTool (Prospeo)  →  Contact[]
ContactProfileAgent + lookup_person (Tavily)
        │
        ▼
save_run()  →  data/runs/<timestamp>/
```

### Research loop (company)

```text
ResearchState
  → LLM planner (search | finish), step budget + feedback on guardrails
  → WebSearchTool (Tavily)
  → EvidenceEvaluator (signal-based relevance, tiered quality)
  → evidence kept if relevance ≥ 0.35 or quality ≥ 0.85; URL dedupe
  → repeat until finish, max_steps (5), or guardrail exhaustion
```

Python enforces guardrails: invalid/duplicate queries replan (with cap), search errors and empty results do not consume a step, unknown actions replan, step cap sets `stop_reason`.

### EXCON (separate from `analyze()`)

```text
User + Products + Company + CompanyProfile + Contact + ContactProfile
  → skip if DNC / no handle / no consent
  → primary channel draft (OutreachAgent + MLX)
  → seller edit → approve → Connector.send()  (refused unless approved)
```

`ProspectIQ.analyze()` does not call EXCON. The web API can draft one message via `draft_for_contact()` using a finished job `result`. `./run_excon.sh` still exercises the full EXCON flow against **mock bundle** data by default.

### Main modules

| Area | Location | Responsibility |
|------|----------|----------------|
| Orchestrator | `app/orchestrator.py` | `ProspectIQ.analyze()` — research, score, report |
| Seller pipeline | `app/pipeline.py` | `SellerPipeline.run()`, `save_run()`, people pass |
| Onboarding | `app/onboarding.py` | Website → seller + products |
| Upload | `app/prospect_upload.py` | CSV parse, `UploadedProspect` |
| Report mapping | `app/report_mapper.py` | `ProspectReport` → `Company` + `CompanyProfile` |
| People mapping | `app/people_mapper.py` | `PersonData` → `Contact` |
| Research jobs | `app/research_jobs.py` | In-memory/disk job store, cancel/skip |
| API | `app/server.py` | FastAPI routes, background research thread |
| EXCON | `app/excon.py` | `prepare`, `edit`, `approve`, `reject`, `send` |
| Agents | `agents/` | Research, scoring, report, outreach, contact profile |
| Tools | `tools/` | Web search, website reader, evidence, people data |
| Connectors | `connectors/` | Channel send implementations |
| Schemas | `config/schemas.py`, `config/excon_schemas.py` | Research scratch types vs persisted graph |
| UI | `web/` | Next.js + shadcn research form |

---

## Tech Stack

| Category | Choices |
|----------|---------|
| Language | Python 3.12+ (venv), TypeScript |
| API | FastAPI, Uvicorn, Pydantic v2 |
| UI | Next.js 16, React 19, Tailwind 4, shadcn/Radix, Zod, Zustand |
| LLM | MLX-LM server, OpenAI-compatible `/v1/chat/completions`, model `mlx-community/Qwen3-8B-4bit` |
| Search | Tavily (`tavily-python`) |
| People data | Prospeo (`tools/providers/prospeo.py`) |
| HTTP / parsing | `httpx`, `requests`, BeautifulSoup |
| Outreach | SMTP, Slack Web API, Twilio-shaped SMS, WhatsApp Cloud API-shaped, LinkedIn stub |
| Persistence | JSON files (`data/runs/`, `data/jobs/`); mocks in `data/mock/` |

See `requirements.txt` and `web/package.json` for pinned versions.

---

## Setup & Installation

### Prerequisites

- Python 3.12+
- Node.js/npm (for `web/`)
- Reachable **MLX-LM** server (typically Mac mini M4)
- **Tavily** API key (live company/person search)
- **Prospeo** API key (people search in the live pipeline)
- Bash-compatible shell for `run_*.sh` (Git Bash/WSL on Windows), or run equivalent commands manually

### Python environment

```bash
python3.12 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
cp .env.example .env
```

### Environment variables

Edit `.env` (never commit secrets):

| Variable | Required for | Description |
|----------|----------------|-------------|
| `MLX_BASE_URL` | All MLX calls | e.g. `http://192.168.x.x:8080` |
| `MLX_MODEL` | Same | `mlx-community/Qwen3-8B-4bit` |
| `TAVILY_API_KEY` | Research | Tavily web search |
| `PROSPEO_API_KEY` | People in pipeline | Prospeo people search |
| `EXCON_DRY_RUN` | EXCON send | Default `true` — no real network send |
| `OTP_REQUIRED` | Outreach email verify | Default `false` |
| `SMTP_*` | Email send / OTP | Host, port, user, password, from |
| `SLACK_BOT_TOKEN` | Slack send | |
| `TWILIO_*` | SMS send | |
| `WHATSAPP_*` | WhatsApp send | |
| `LINKEDIN_ACCESS_TOKEN` | LinkedIn | Stub only; no scraping |

### MLX server (inference host)

On the Mac mini (example from project docs):

```bash
mlx_lm.server \
  --model mlx-community/Qwen3-8B-4bit \
  --host 0.0.0.0 \
  --port 8080 \
  --chat-template-args '{"enable_thinking":false}'
```

### Web dependencies

```bash
cd web && npm install && cd ..
```

---

## Usage

### Full app (UI + API)

```bash
./run_app.sh
```

- UI: http://localhost:3000  
- API: http://localhost:8000  
- Form sections: **You**, **Role**, **Company**, **Prospects**  
- After CSV upload, companies are staged for review before research starts  
- Expect ~1 minute onboarding plus ~3–5 minutes per prospect company (varies with Tavily/MLX/Prospeo)

API only:

```bash
./run_api.sh
```

### CLI seller pipeline

```bash
./run_pipeline.sh \
  --name "Priya Mehta" \
  --phone "+919845512210" \
  --email "priya.mehta@nexusflow.io" \
  --website "https://www.zoho.com" \
  --industry "Software / SaaS" \
  --title "Account Executive" \
  --prospects data/uploads/sample_prospects.csv
```

Omit flags to be prompted. Equivalent: `python -m app.pipeline` with the same arguments.

**CSV format:**

```text
company_name,website,notes
```

`company_name` is required. Samples: `data/uploads/sample_*.csv`.

### Company-only research (no onboarding)

```bash
python -m tests.test_orchestrator
```

### EXCON (Phase 3, mocks + live MLX for drafts)

```bash
./run_excon.sh
```

Requires reachable `MLX_BASE_URL`. Connector tests stay local; sends respect `EXCON_DRY_RUN`.

### UI / API contract checks

```bash
python -m tests.run_ui
python -m tests.test_api
```

### End-to-end pipeline test

```bash
python -m tests.test_pipeline
```

(Documented sample: seller site Zoho + sample CSV → high-priority scores for Asian Paints and Havells India; several minutes wall time.)

---

## File / Folder Structure

```text
agents/           Research, scoring, report, outreach, contact profile agents
app/              Pipeline, onboarding, FastAPI server, EXCON wrapper, research jobs
connectors/       Email, LinkedIn, WhatsApp, Slack, SMS
config/           Pydantic schemas, catalog, EXCON types
data/
  mock/           Joined fixtures for EXCON demos (load_mock_bundle)
  uploads/        Sample prospect CSVs
  runs/           Finished pipeline output (gitignored)
  jobs/           In-flight research job JSON (+ staged CSV)
docs/             Topic guides (USER_FLOW, PIPELINE, ARCHITECTURE, …)
llm/              MLX client and JSON utilities
tools/            Tavily search, website reader, evidence, people providers
web/              Next.js UI (research-form, catalog, job polling)
tests/            Module and integration tests (python -m tests.*)
run_app.sh        API + Next dev
run_api.sh        API only
run_pipeline.sh   CLI SellerPipeline
run_excon.sh      EXCON test runner
```

**Key files**

| File | Purpose |
|------|---------|
| `app/server.py` | HTTP API surface |
| `app/pipeline.py` | `SellerPipeline`, run persistence |
| `app/orchestrator.py` | `ProspectIQ.analyze()` |
| `web/components/research-form.tsx` | Main seller UX |
| `web/lib/research-job.ts` | Poll `GET /api/research/{job_id}` |
| `data/loader.py` | Load mock bundle for EXCON scripts |

---

## Configuration

- **Catalog**: `config/catalog.json` — allowed `Industry` and `SellerTitle` values; titles filtered by industry. Must stay aligned with `web/lib/catalog-data.json`.
- **Research schemas**: `config/schemas.py` — `Evidence`, `ProspectScore`, `ProspectReport`, `PersonData`, etc.
- **Graph / outreach schemas**: `config/excon_schemas.py` — `User`, `Company`, `Contact`, `OutreachDraft`, events.
- **CORS**: API allows `http://localhost:3000` and `http://127.0.0.1:3000`.
- **Upload limit**: 5 MB enforced in UI logic, FastAPI, and `load_prospect_csv`.
- **People cap**: `PEOPLE_PER_COMPANY = 3` in `app/pipeline.py`.
- **Research step cap**: 5 planner steps per company (see `docs/ARCHITECTURE.md`).

---

## API Reference

Base URL: `http://127.0.0.1:8000` when using `run_api.sh` / `run_app.sh`.

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | `{"status":"ok"}` |
| `GET` | `/api/catalog` | Industries and titles-by-industry for the form |
| `GET` | `/api/settings` | e.g. `{"otp_required": bool}` |
| `POST` | `/api/verify-email` | Body: `{ "email" }` — start OTP flow |
| `POST` | `/api/verify-email/confirm` | Body: `{ "email", "code" }` |
| `POST` | `/api/preview` | Multipart CSV `prospects` → parsed company list (no research) |
| `POST` | `/api/research` | Multipart form: seller fields + CSV; starts background job → `{ job_id, status, companies, ... }` |
| `GET` | `/api/research/{job_id}` | Job status, progress messages, `result` when complete |
| `POST` | `/api/research/{job_id}/cancel` | Request cancel while `running` |
| `POST` | `/api/research/{job_id}/skip` | Skip current company while `running` |
| `POST` | `/api/outreach/draft` | Body: `{ "contact_id", "job_id" \| "result" }` → single EXCON-style draft |

**`POST /api/research` form fields** (required unless noted): `full_name`, `phone`, `email`, `website`, `title`, `industry`, file `prospects`; optional `outreach_email` (defaults to `email`).

### Python EXCON API (library)

```python
from app.excon import Excon
from data.loader import load_mock_bundle

bundle = load_mock_bundle()
excon = Excon(dry_run=True, dnc=bundle.dnc)
batch = excon.prepare(
    user=bundle.user,
    prospect=...,  # legacy mock may use prospect_id; live graph uses Company
    profiles=...,
    contacts=...,
    products=...,
)
excon.edit(draft_id, body="...")
excon.approve(draft_id)
excon.send(draft_id)  # raises if not approved
```

See [`docs/EXCON.md`](docs/EXCON.md) for draft rules and connector behavior.

### Core orchestration

```python
from app.orchestrator import ProspectIQ

iq = ProspectIQ()
report = iq.analyze(company_name="Example Corp", research_goal="...")
```

Returns a `ProspectReport` (scratch type); the seller pipeline maps and saves the full graph.

---

## Known Issues / Limitations

- **No database or signup/session persistence** — runs are JSON on disk; web draft is localStorage-only.
- **Phase 4 not built** — no dashboards, run history UI, or full EXCON reviewer in the browser.
- **EXCON not integrated into `ProspectIQ.analyze()`** — full batch `prepare()` is separate; UI has single-contact draft endpoint only.
- **`./run_excon.sh` defaults to `data/mock/`** — live `data/runs/` output is not auto-wired into EXCON batch flows.
- **`CompanyDataTool`** — raises `NotImplementedError` (future BDL/provider).
- **`tools/people_enrichment.py`** — not called during research (email/mobile enrich optional later).
- **LinkedIn connector** — official-API stub only; no scraping.
- **Email/SMS consent** — false by default even when Prospeo returns handles; EXCON will not use those channels until consent is set.
- **Timing** — full runs are slow (minutes per company); depends on MLX, Tavily, and Prospeo latency.
- **Windows** — shell runners are bash scripts; use WSL/Git Bash or invoke `uvicorn` / `npm run dev` manually.
- **Doc drift** — some older notes in `docs/PIPELINE.md` still mention “CLI only” for the browser form; the Next.js form is the current primary UX (see `README.md`, `docs/USER_FLOW.md`).

TODO: Confirm whether production deployments should document non-local `MLX_BASE_URL` networking/firewall requirements beyond the Mac mini example.

---

## Future Improvements

From [`docs/ROADMAP.md`](docs/ROADMAP.md) and architecture notes:

**Phase 1**

- Company-data provider behind `CompanyDataTool`
- Database persistence instead of JSON-only runs
- Prospect discovery from seller ICP (no upload)

**Phase 2**

- Richer contact profiles from live research only (reduce reliance on mocks for EXCON demos)
- Persisted graph: User → Products → Companies → Contacts → Profiles

**Phase 3**

- Point EXCON `prepare()` at `data/runs/` output by default
- Live connector credentials per workspace
- Edit/approve/send in a dedicated UI
- Official LinkedIn partner path if available

**Phase 4**

- App shell: history, seller edit, EXCON inbox
- Dashboards on `OutreachEvent` (`drafted`, `approved`, `sent`, …)
- Browse and report on `data/runs/` in the UI

**Near-term application slice (partially done)**

1. Form + CSV → live `analyze()` per company — **done** (web + CLI)  
2. Wire saved seller + researched prospects into full EXCON — **in progress** (draft API exists; batch/UI incomplete)  
3. Real UI for engagement and analytics — **not started**

---

## Related documentation

| Document | Topics |
|----------|--------|
| [docs/USER_FLOW.md](docs/USER_FLOW.md) | Seller journey, rules (approve before send, DNC, primary channel) |
| [docs/PIPELINE.md](docs/PIPELINE.md) | CLI/form pipeline, CSV, timing |
| [docs/RESEARCH.md](docs/RESEARCH.md) | Who fills which entity; file map |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | Two-machine design, tools table |
| [docs/DATA_MODEL.md](docs/DATA_MODEL.md) | IDs, objects, fixtures |
| [docs/EXCON.md](docs/EXCON.md) | Connectors, dry-run, events |
| [docs/ROADMAP.md](docs/ROADMAP.md) | Four-phase plan |
| [README.md](README.md) | Quick start and repo map |

Historical `.docx` files under `docs/` are journals only; markdown in `docs/` is the maintained source of truth.
