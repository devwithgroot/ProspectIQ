# Seller pipeline

The current application entry. A seller enters identity + a company website, uploads prospect companies, and `ProspectIQ.analyze()` runs for each row. No stand-ins: onboarding uses the website reader + MLX, research uses Tavily + MLX.

## Flow

```text
Name, phone, email, industry, title, company website
        │
        ▼
WebsiteReaderTool  →  page text
        │
        ▼
MLX (Qwen3)        →  User + Products
        │
        ▼
CSV upload         →  company_name [, website, notes]
        │
        ▼
for each company
        │
        ▼
ProspectIQ.analyze()
   ResearchAgent   →  Tavily search + MLX planner
   ScoringAgent    →  MLX dimension scores
   ReportAgent     →  MLX sales report
        │
        ▼
report_to_prospect()  →  Prospect
        │
        ▼
data/runs/<timestamp>/
   user.json
   products.json
   prospects.json
   reports.json
```

## APIs already in `.env`

| Variable | Used for |
|---|---|
| `MLX_BASE_URL` | Onboarding, research planner, scoring, report |
| `MLX_MODEL` | Same (`mlx-community/Qwen3-8B-4bit`) |
| `TAVILY_API_KEY` | `WebSearchTool` inside the research loop |

Do not add a second LLM or search client. `LLMClient` and `WebSearchTool` are the only network paths.

## Command

Next.js + shadcn form (website and upload in the browser):

```bash
./run_app.sh
```

UI: http://localhost:3000 · API: http://localhost:8000

CLI:

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

Or `python -m app.pipeline` with the same flags. Omit flags to be prompted.

CSV header:

```text
company_name,website,notes
```

`company_name` is required. Duplicate names are skipped. Samples live in `data/uploads/` (`sample_prospects.csv` is the short default; others cover Demand Planning, PlantConnect, TradePulse, names-only, mixed columns, and a CRM-style export). Maximum **5 MB per file** (Next.js form, FastAPI, and `load_prospect_csv` all enforce this).

## What each step calls

1. **Onboarding** (`app/onboarding.py`) — fetch the seller site, ask MLX for company name/description + products, then attach the seller-selected `Industry` and `SellerTitle`.
2. **Upload** (`app/prospect_upload.py`) — parse the CSV.
3. **Orchestrator** (`app/orchestrator.py`) — for every uploaded company, run research → score → report against that seller's products.
4. **Map** (`app/report_mapper.py`) — `ProspectReport` → `Prospect` (score, signals, risks, sources, `matched_product_ids`).
5. **Save** — JSON under `data/runs/`. That folder is gitignored.

## Live check

`python -m tests.test_pipeline` is this path end to end. A run against Zoho as seller and the sample CSV produced:

| Prospect | Score | Recommendation |
|---|---|---|
| Asian Paints | 81 | High-priority prospect |
| Havells India | 80 | High-priority prospect |

Expect several minutes: onboarding is about a minute, then each company can take about 2–3 minutes (up to five Tavily searches plus scoring and a report). The form shows that range before and during research.

## Not in this pipeline yet

- Browser form (CLI only)
- Contact discovery (people still come from `data/mock/` for EXCON)
- Feeding `data/runs/` into EXCON automatically
