# User flow

This is the product path a salesperson is supposed to take. Steps 1–4 run today from the Next.js form (`./run_app.sh`) or the CLI (`./run_pipeline.sh`) on MLX and Tavily. Contacts and outreach still use fixtures.

## Intended path

```text
1. Enter name, phone, email, industry, and title
2. Paste company website
3. Optionally upload prospect companies
4. System builds the seller + researches prospects
5. Seller picks a prospect → sees contacts
6. System drafts outreach from each contact profile
7. Seller edits / approves / sends
8. Analytics and reports
```

### 1. Identity

The seller types:

- Full name
- Phone number
- Work email
- Outreach email (can be different from work email)
- When `OTP_REQUIRED=true`, a code is sent to that inbox and must be confirmed in a dialog. It is off by default.
- Industry (suggestive dropdown, catalog only)
- Title (suggestive dropdown, titles for that industry only)

That becomes the `User` record. Work email is who they are. Outreach email is the from-address later. Industry and title are enums (`Industry`, `SellerTitle` in `config/catalog.py`). Free-typed values are rejected.

### 2. Company from a link

They paste their company website.

`OnboardingAgent` then:

1. Fetches the page with `WebsiteReaderTool`
2. Asks MLX to fill `SellerCompany` (name, description, size, HQ). Industry stays the value the seller picked.
3. Infers the `Product` list: what they sell, ICP, value props, typical buyers

If the page cannot be fetched, MLX still runs on the URL alone. The seller should be able to correct the result before outreach; that edit step is not in the CLI yet.

### 3. Optional prospect upload

They may already have a list. Upload (CSV / sheet) with at least:

| Column | Required | Notes |
|---|---|---|
| company_name | yes | Used as the research key |
| website | no | Speeds up research |
| notes | no | Why they care |
| owner | no | If a team later |

The form first stages the parsed rows (company, website, notes; duplicates dropped) so the seller can review and edit the list. Research starts from that staging screen. The form estimates time from list size: about a minute to read the seller site, then about 2–3 minutes per company, plus a few extra minutes of buffer. After research, briefings stay on a review screen so the seller can edit the wording before they keep it. Each company is then researched with Tavily, scored and reported with MLX, then mapped to a `Prospect` (`signals`, `pain_points`, score, `why_relevant_to_user`, `matched_product_ids`). See [PIPELINE.md](PIPELINE.md).

If they upload nothing, Phase 1 can later *discover* prospects from the seller ICP. That discovery path is not built yet. Upload is the first supported way to get companies into the system.

### 4. Research and summary (Phases 1–2)

For each prospect:

- Collect public evidence (Tavily, later BDL / company-data providers)
- Score growth, expansion, hiring, technology, strategic fit
- Write a company summary
- Find contacts at that company
- Build a `ContactProfile` per person (role, pain vs our product, talking points, preferred channel, consent)

The seller sees companies first, then people. They do not start from a raw lead dump.

### 5. Engage (Phase 3 EXCON)

The seller picks one or more prospects they want to talk to.

For each chosen prospect they see that company's contacts. EXCON then:

1. Skips do-not-contact and no-consent people
2. Drafts the **primary channel** only (email, LinkedIn, WhatsApp, Slack, or SMS)
3. Lets the seller edit the copy
4. Requires explicit approve before send
5. Sends through the matching connector, or dry-run if credentials are missing

`edit()` resets approval so stale copy cannot go out.

### 6. Analytics and UI (Phase 4)

Not built. The event log already records `drafted`, `edited`, `approved`, `rejected`, `sent`, `send_failed` so the UI can chart it later.

## What works if you run the repo today

The first application slice is the Next.js + shadcn form, plus the same CLI. Both use the same MLX and Tavily clients. The form is four sections: You, Role, Company, Prospects.

1. Enter name, phone, email, industry, title, and company website (`./run_app.sh` or `./run_pipeline.sh`)
2. Point at a prospect CSV (`company_name`, optional `website`, `notes`)
3. Onboarding reads the seller site and infers company + products via MLX
4. Live `ProspectIQ.analyze()` runs for **each uploaded company** (Tavily + MLX)
5. Researched prospects are saved under `data/runs/`

Sample files: `data/uploads/sample_*.csv` (short list, single company, names-only, mixed quality, and one file per NexusFlow product ICP).

Contacts are still mock (`data/mock/contacts.json`) until contact discovery exists. `./run_excon.sh` still drafts from those fixtures.

Company-only research without onboarding still runs through `ProspectIQ.analyze(company_name, research_goal)`.

## Rules the UI must keep

- Never send without approve
- Never draft or send a DNC / no-consent contact
- One primary channel first, not five messages at once
- Seller can always edit before approve
- Uploaded prospects are researched before they are engaged
- Seller company + products must exist before outreach
