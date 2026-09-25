# Roadmap

Four phases. Build in this order. Do not skip seller context or approval.

## Phase 1 — Data collection and scoring

**Now**

- Autonomous research loop (planner + Tavily + evidence scores)
- Five-dimension scoring with deterministic weights
- Company `ProspectReport`

**Next**

- Wire `WebsiteReaderTool` into research and into seller onboarding
- Company-data provider (BDL or equivalent) behind `CompanyDataTool`
- Persist evidence and scores
- Accept uploaded prospect lists as research inputs
- Discover contacts at a researched company

## Phase 2 — Company + lead summary

**Now**

- Report agent writes an executive summary, signals, risks, sales approach
- Mock `Prospect`, `Contact`, and `ContactProfile` records that show the target shape

**Next**

- Map `ProspectReport` → `Prospect`
- Summarize the seller company from their website
- Infer and confirm products / ICP
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

- Signup: name, phone, email
- Company-from-link onboarding
- Prospect CSV upload
- Prospect list → contact list → draft reviewer
- Dashboards on drafted / approved / sent / failed
- Saved reports per prospect

## Near-term application slice

The first UI that matches the intended user flow, without waiting for every provider:

1. Form: name, phone, email, company URL
2. Optional CSV of prospect company names
3. Run existing `ProspectIQ.analyze()` per uploaded company
4. Keep using mock contacts until contact discovery exists
5. Run EXCON on the seller (from the form + site) + those prospects

That slice is enough to demo the full story: identity → company → uploaded prospects → research → drafts → approve.
