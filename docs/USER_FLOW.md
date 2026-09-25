# User flow

This is the product path a salesperson is supposed to take. Only the research and EXCON engines exist today. The signup UI, company-from-link onboarding, and prospect upload are the next application layer.

## Intended path

```text
1. Enter name, phone, email
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

That becomes the `User` record: who is sending, how they sign messages, and which channels they can use as the from-address later.

### 2. Company from a link

They paste their company website (and later, maybe a LinkedIn company URL).

ProspectIQ should then:

1. Fetch the page with `WebsiteReaderTool`
2. Research the company the same way we research a prospect (search + evidence)
3. Fill `SellerCompany`: name, industry, description, size, HQ
4. Infer `Product` list: what they sell, ICP, value props, typical buyers

The seller can correct that before anything is messaged. Outreach is only as good as this seller context. Without it, drafts are generic.

### 3. Optional prospect upload

They may already have a list. Upload (CSV / sheet) with at least:

| Column | Required | Notes |
|---|---|---|
| company_name | yes | Used as the research key |
| website | no | Speeds up research |
| notes | no | Why they care |
| owner | no | If a team later |

Uploaded rows become `Prospect` shells with `source = upload`. Phase 1 then researches each one: signals, pain points, score, `why_relevant_to_user`, `matched_product_ids`.

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

There is no signup screen. The flow is exercised as code + fixtures:

1. `data/mock/user.json` — Priya Mehta (stands in for step 1–2)
2. `data/mock/products.json` — NexusFlow products (stands in for company-from-link)
3. `data/mock/prospects.json` — Asian Paints, Tata Steel, Havells (stands in for upload + research)
4. `data/mock/contacts.json` + `profiles.json` — people and researched profiles
5. `./run_excon.sh` — drafts real Qwen copy, approve/send stays dry-run

Company-only research (no people) still runs through `ProspectIQ.analyze(company_name, research_goal)`.

## Rules the UI must keep

- Never send without approve
- Never draft or send a DNC / no-consent contact
- One primary channel first, not five messages at once
- Seller can always edit before approve
- Uploaded prospects are researched before they are engaged
- Seller company + products must exist before outreach
