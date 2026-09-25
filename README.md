# ProspectIQ

Local agentic B2B sales intelligence. A seller signs up, we learn their company from a website link, they can upload prospects, and the system researches those companies, finds contacts, scores fit, and prepares channel-specific outreach for human approval.

## Product in one picture

```text
Seller signup (name, phone, email)
        │
        ▼
Company website link  ──►  seller company + products
        │
        ▼
Optional prospect upload  ──►  companies of interest
        │
        ▼
Phase 1  Research + score prospects (Tavily, BDL, web)
Phase 2  Company + contact summaries / profiles
Phase 3  EXCON — draft, edit, approve, send
Phase 4  Analytics, UI, reports
```

Seller onboarding + CSV upload now run the existing orchestrator for each uploaded company. Phase 3 EXCON still uses mock contacts until contact discovery exists. Phase 4 is not built.

## Docs

| Doc | What it covers |
|---|---|
| [docs/USER_FLOW.md](docs/USER_FLOW.md) | How a seller uses the product, now vs intended |
| [docs/PIPELINE.md](docs/PIPELINE.md) | Onboard + CSV + live orchestrator (MLX, Tavily) |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | Components, machines, and how they connect |
| [docs/DATA_MODEL.md](docs/DATA_MODEL.md) | User, prospect, contact, profile, outreach objects |
| [docs/EXCON.md](docs/EXCON.md) | Outreach connectors, approval, dry-run |
| [docs/ROADMAP.md](docs/ROADMAP.md) | Four phases, what is done, what is next |

Older setup journals in `docs/*.docx` are historical. These markdown files are the current source of truth.

## Current stack

- **App:** Python, Pydantic, sequential agents
- **Model:** Qwen3 8B 4-bit on a Mac mini via MLX-LM (`LLMClient` → `/v1/chat/completions`)
- **Search:** Tavily
- **Outreach:** EXCON drafts for email, LinkedIn, WhatsApp, Slack, SMS. Send is approval-gated and dry-run by default

```text
Seller laptop / app
        │  HTTP
        ▼
Mac mini :8080  →  MLX-LM  →  Qwen3 8B 4-bit
```

## Setup

```bash
python3.12 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
cp .env.example .env
```

Fill `.env`:

- `MLX_BASE_URL` — MLX server, e.g. `http://192.168.x.x:8080`
- `MLX_MODEL` — `mlx-community/Qwen3-8B-4bit`
- `TAVILY_API_KEY` — required for live web research

On the Mac mini:

```bash
mlx_lm.server \
  --model mlx-community/Qwen3-8B-4bit \
  --host 0.0.0.0 \
  --port 8080 \
  --chat-template-args '{"enable_thinking":false}'
```

## Run

Seller form + prospect upload (orchestrator runs after the CSV):

```bash
./run_pipeline.sh \
  --name "Priya Mehta" \
  --phone "+919845512210" \
  --email "priya.mehta@nexusflow.io" \
  --website "https://www.zoho.com" \
  --prospects data/uploads/sample_prospects.csv
```

Omit the flags to be prompted. Each uploaded `company_name` is passed to live `ProspectIQ.analyze()` (Tavily + MLX). Results land in `data/runs/`. Details: [docs/PIPELINE.md](docs/PIPELINE.md).

Company research only:

```bash
python -m tests.test_orchestrator
```

EXCON (Phase 3, mocks + live model for drafts):

```bash
./run_excon.sh
```

That runs mock/schema/connector checks, then live outreach + EXCON against Qwen.

## Repository

```text
agents/          Research, scoring, report, outreach
app/             ProspectIQ.analyze(), seller pipeline, Excon
config/          Research schemas + EXCON schemas
connectors/      Email, LinkedIn, WhatsApp, Slack, SMS
data/mock/       Seller, products, prospects, contacts, profiles
llm/             MLX client + JSON parse/retry
tools/           Web search, website reader, evidence
tests/           Script-style tests (`python -m tests.test_*`)
```

EXCON is not wired into `ProspectIQ.analyze()`. Research and outreach stay separate until Phase 1–2 emit real people.
