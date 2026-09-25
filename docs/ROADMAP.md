# Roadmap

Four phases. Build in this order. Do not skip seller context or approval.

## Phase 1 — Data collection and scoring

**Now**

- Autonomous research loop (planner + Tavily + evidence scores)
- Five-dimension scoring with deterministic weights
- Company `ProspectReport`
- Seller website onboarding (`WebsiteReaderTool` + MLX)
- Prospect CSV upload → live `analyze()` per company
- Reports saved under `data/runs/`

**Next**

- Company-data provider (BDL or equivalent) behind `CompanyDataTool`
- Database persistence (runs are JSON files today)
- Discover contacts at a researched company

## Phase 2 — Company + lead summary

**Now**

- Report agent writes an executive summary, signals, risks, sales approach
- `report_to_prospect()` maps a live report into `Prospect`
- Seller company + products inferred from the website
- Mock `Contact` and `ContactProfile` records until people are researched

**Next**

- Build real contact profiles (not fixtures)
- Store the joined graph User → Products → Prospects → Contacts → Profiles

## Phase 3 — EXCON

**Now**

- Schemas, mocks, outreach agent, approval-gated send
- Email / Slack / SMS / WhatsApp / LinkedIn connectors
- Dry-run default, DNC + consent, primary channel, event log
- `./run_excon.sh`

**Next**

- Point EXCON at Phase 1–2 output instead of `data/mock/`
- Live connector credentials per workspace
- Edit/approve in a real UI
- Official LinkedIn partner path only if/when available

## Phase 4 — Analytics, UI, reports

**Now**

- Nothing user-facing
- `OutreachEvent` is the analytics hook

**Next**

- Browser UI for the CLI form
- Prospect list → contact list → draft reviewer
- Dashboards on drafted / approved / sent / failed
- Browse `data/runs/` reports in the UI

## Near-term application slice

Done as a CLI, not a browser UI:

1. Form: name, phone, email, company URL — `./run_pipeline.sh`
2. CSV of prospect companies — `data/uploads/sample_prospects.csv`
3. `ProspectIQ.analyze()` runs for each uploaded company
4. Mock contacts still used for EXCON
5. Next: wire the saved seller + researched prospects into EXCON, then a real UI
