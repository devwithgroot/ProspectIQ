# Research and the data model

What a research run asks for, which model it fills, and where the answer is stored.

User objects live in `config/excon_schemas.py`. Scratch notes the model writes while researching (`Evidence`, `ProspectReport`, `PersonData`) live in `config/schemas.py`. Those scratch notes are mapped into the saved graph before the run is written to `data/runs/<timestamp>/`.

## The graph

```text
User ──owns──► Product
User ──targets──► Company
Company ──has──► CompanyProfile
Company ──has──► Contact
Contact ──has──► ContactProfile

User + Product + Company + CompanyProfile + Contact + ContactProfile
        ──► OutreachDraft   (EXCON, not this run)
```

Two pairs on purpose:

| Record (who / what) | Profile (how to sell) |
|---|---|
| `Company` | `CompanyProfile` |
| `Contact` | `ContactProfile` |

The user’s own firm is `User.company` (`UserCompany`). That is not a researched `Company`.

IDs: `us_` user, `pd_` product, `co_` company, `cp_` company profile, `ct_` contact, `pf_` contact profile.

| Entity | Defined in | Filled by | Saved to (run / mock) |
|---|---|---|---|
| `User` + `UserCompany` | `config/excon_schemas.py` | `app/onboarding.py` | `user.json` |
| `Product` | `config/excon_schemas.py` | `app/onboarding.py` | `products.json` |
| `Company` | `config/excon_schemas.py` | `app/report_mapper.py` | `companies.json` |
| `CompanyProfile` | `config/excon_schemas.py` | `app/report_mapper.py` from `agents/report_agent.py` | `company_profiles.json` |
| `Contact` | `config/excon_schemas.py` | `app/people_mapper.py` from Prospeo | `contacts.json` |
| `ContactProfile` | `config/excon_schemas.py` | `agents/contact_profile_agent.py` | `contact_profiles.json` |
| `UploadedProspect` | `app/prospect_upload.py` | Form / CSV | not saved (input only) |
| `ProspectReport` / `PersonData` | `config/schemas.py` | Research scratch | not saved as themselves |

## Who is asked, and what they fill

```text
User (form)
        │
        ▼
OnboardingAgent
  website fetch  →  page text
  MLX            →  User + UserCompany + Product[]
        │
        ▼
Uploaded rows (company_name, website, notes)
        │
        ▼
ProspectIQ.analyze()                         for each uploaded company
  ResearchAgent  Tavily + MLX planner        →  Evidence[]
  ScoringAgent   MLX + fixed weights         →  ProspectScore
  ReportAgent    MLX                         →  ProspectReport
        │
        ▼
report_to_company()
                 →  Company + CompanyProfile
        │
        ▼
PeopleDataTool   Prospeo                     →  PersonData[]
person_to_contact()
                 →  Contact[]
        │
        ▼
ResearchAgent.lookup_person()  Tavily        →  Evidence[] on that person
ContactProfileAgent            MLX           →  ContactProfile
```

### 1. User — `User`, `UserCompany`, `Product`

**Asked:** name, phone, work email, industry, title, company website (suggested from the email domain). List of target companies (typed grid or CSV).

**Filled by:** `OnboardingAgent` (`app/onboarding.py`).

| Entity | What it is | Source |
|---|---|---|
| `User` | The salesperson | Form fields + MLX voice (tone, signature, CTA) |
| `UserCompany` | Their firm (`User.company`) | Website page via `WebsiteReaderTool`, then MLX. Industry stays the catalog value they picked. |
| `Product` | What they sell | MLX from the same page (ICP, buyers, value props) |

`title` and `company.industry` are catalog enums only (`config/catalog.json`).

Until outreach, `outreach_email` is the work email.

### 2. Upload row — not saved as its own entity

**Asked:** `company_name` (required), `website`, `notes`.

**Type:** `UploadedProspect` (`app/prospect_upload.py`). Used as input only. The saved company comes from research, not from this row alone.

### 3. Target firm — `Company` + `CompanyProfile`

**Asked (of the public web + model):** is this company a fit, what are the signals, who should we talk to (roles).

**Filled by:** `ProspectIQ.analyze()` then `report_to_company()`.

| Scratch object | Entity it becomes |
|---|---|
| Tavily hits + scores | `Evidence` (kept on the report, URLs copied to `Company.sources`) |
| `ProspectScore` | `CompanyProfile.overall_score` and `recommendation` |
| `ProspectReport` | `Company` + `CompanyProfile` |

`Company` is the record:

- `company_id`, `name`, `website`, `industry`, HQ, size, year
- `description`, `products_services`, `sources`

`CompanyProfile` is the briefing:

- `profile_id`, `company_id`
- `executive_summary`, `overall_score`, `recommendation`
- `signals`, `pain_points`, `risks`
- `recommended_sales_approach` (can name **roles** to call, not invented people)
- `why_relevant_to_user`, `matched_product_ids`

The planner is told to look for growth, expansion, hiring, tech, funding, and **leadership / decision makers**.

### 4. People — `Contact` + `ContactProfile`

**Asked (of Prospeo + the public web + model):** who works there, what is public about them, how to pitch this person given the company briefing.

**Filled by:** `_find_people()` in `app/pipeline.py` after the company briefing. Up to 3 people per company.

| Scratch object | Entity it becomes |
|---|---|
| `PersonData` (Prospeo) | `Contact` via `person_to_contact()` |
| Tavily on `"Name" Company Title` | `Evidence` passed into the profile writer |
| `ContactProfileDraft` (MLX) | `ContactProfile` |

`Contact` is the person:

- `contact_id`, `company_id`
- `full_name`, `title`, `seniority`, `department`
- `decision_role`: `economic_buyer` \| `champion` \| `influencer` \| `blocker` (from the title)
- handles: `email`, `phone`, `linkedin_url` (often empty until enrich)
- `preferred_channel`, `consent`, `do_not_contact`

Consent: LinkedIn is on if we have a profile URL. Email and SMS stay off even if Prospeo returned a handle. EXCON will not email them until the user consents.

`ContactProfile` is their briefing:

- `profile_id`, `contact_id`, `company_id`
- `bio`, `responsibilities`, `interests`, `recent_activity`
- `communication_style`
- `likely_pain_vs_product`, `talking_points`, `risks`
- `recommended_approach`

That writer sees **both** the `CompanyProfile` and the person + company `Evidence`. It must not invent meetings or metrics.

## One company, in order

```text
Looking into Asian Paints
  → Tavily searches (planner, up to 5)
  → Score the company
  → Write Company + CompanyProfile
Ready with the Asian Paints briefing
Finding people at Asian Paints
  → Prospeo
Found 3 people at Asian Paints
  for each person:
    Looking up Name at Asian Paints
    → Tavily
    Writing a briefing for Name
    → Contact + ContactProfile
Putting your briefings together
```

Time estimate on the form includes this people pass (about 3–5 minutes per company, plus onboarding).

## Files: where each thing lives

### Schema (the types)

| File | What it defines |
|---|---|
| `config/excon_schemas.py` | `User`, `UserCompany`, `Product`, `Company`, `CompanyProfile`, `Contact`, `ContactProfile`, outreach types |
| `config/schemas.py` | Scratch notes: `Evidence`, `ResearchDecision`, `ProspectScore`, `ProspectReport`, `PersonData`, `ContactProfileDraft` |
| `config/catalog.py` + `config/catalog.json` | Industry and title enums |
| `web/lib/catalog-data.json` | Same catalog for the Next.js form (keep in sync) |
| `web/lib/types.ts` | Frontend copies of user, company, contact, job, result |
| `agents/state.py` | `ResearchState` (queries + evidence while a company is being researched) |
| `app/prospect_upload.py` | `UploadedProspect` (grid/CSV row, not saved as its own entity) |

### Code that fills them

| File | Used for |
|---|---|
| `web/components/research-form.tsx` | User form, company list, researching UI, briefing review |
| `web/components/engagements.tsx` | Draft inbox after you pick a channel on a contact |
| `web/components/companies-book.tsx` | Saved companies, profiles, people, channel engage |
| `web/lib/book.ts` | Merge research runs into the seller’s company book; reuse seller company |
| `web/lib/research-store.ts` | Browser draft in localStorage (`prospectiq-draft-v1`) |
| `web/lib/research-job.ts` | Poll `GET /api/research/{job_id}`; stop or skip company |
| `web/lib/research-estimate.ts` | Time left and activity copy |
| `app/server.py` | FastAPI: start research, poll, cancel, skip company |
| `app/research_jobs.py` | Job store + percent + cancel/skip; writes `data/jobs/rj_*.json` |
| `app/pipeline.py` | `UserPipeline` — whole run; `save_run()` writes `data/runs/` |
| `app/onboarding.py` | Fills `User`, `UserCompany`, `Product` from the website |
| `app/orchestrator.py` | `ProspectIQ.analyze()` — company research, score, report |
| `agents/research_agent.py` | Company Tavily loop; `lookup_person()` for each contact |
| `agents/scoring_agent.py` | Fills `ProspectScore` |
| `agents/report_agent.py` | Fills `ProspectReport` |
| `app/report_mapper.py` | `ProspectReport` → `Company` + `CompanyProfile` |
| `tools/website_reader.py` | Fetch user (and any) website page |
| `tools/web_search.py` | Tavily search → `Evidence` |
| `tools/evidence_evaluator.py` | Relevance / quality on each article |
| `tools/people_data.py` | People search entry point |
| `tools/providers/prospeo.py` | Prospeo search → `PersonData` |
| `tools/people_enrichment.py` | Email/mobile enrich (not used in research yet) |
| `tools/providers/prospeo_enrichment.py` | Prospeo enrich API |
| `app/people_mapper.py` | `PersonData` → `Contact` |
| `agents/contact_profile_agent.py` | Fills `ContactProfile` |
| `llm/client.py` | All MLX `/v1/chat/completions` calls |
| `llm/json_util.py` | Parse model JSON, strip `<think>`, Why-lines |

### Saved output (a live run)

`data/runs/<UTC stamp>/`

| File | Entity |
|---|---|
| `user.json` | `User` (includes `UserCompany`) |
| `products.json` | `Product[]` |
| `companies.json` | `Company[]` |
| `company_profiles.json` | `CompanyProfile[]` |
| `contacts.json` | `Contact[]` |
| `contact_profiles.json` | `ContactProfile[]` |

In-flight research (not the finished graph):

| File | Used for |
|---|---|
| `data/jobs/rj_*.json` | Job status, percent, live log |
| `data/jobs/rj_*.csv` | Staged prospect CSV for that job (deleted when the job ends) |

### Mocks (EXCON fixtures, same shapes)

`data/mock/` — loaded by `data/loader.py`

| File | Entity |
|---|---|
| `user.json` | `User` |
| `products.json` | `Product[]` |
| `companies.json` | `Company[]` |
| `company_profiles.json` | `CompanyProfile[]` |
| `contacts.json` | `Contact[]` |
| `contact_profiles.json` | `ContactProfile[]` |
| `do_not_contact.json` | `DoNotContactEntry[]` |

Sample upload lists (input only): `data/uploads/sample_*.csv`.

### Browser vs disk

| Where | File / key | What |
|---|---|---|
| Browser localStorage | `prospectiq-draft-v1` | Form fields, company grid, last `jobId`, last result |
| API disk | `data/jobs/` | Live research progress |
| API disk | `data/runs/` | Finished graph |

There is no database.

## What still uses fixtures

EXCON drafts (`OutreachDraft`) still run from `data/mock/` unless you point `Excon.prepare()` at a run (`app/excon.py`, `agents/outreach_agent.py`). The live run already has the four researched objects EXCON needs.

Email/mobile enrich (`tools/people_enrichment.py`) is not called during research.

## Keys

| Env (`.env` / `.env.example`) | Used for |
|---|---|
| `MLX_BASE_URL`, `MLX_MODEL` | `llm/client.py` — onboarding, planner, score, both briefings |
| `TAVILY_API_KEY` | `tools/web_search.py` — company and per-person search |
| `PROSPEO_API_KEY` | `tools/providers/prospeo.py` — people search → `Contact` |
