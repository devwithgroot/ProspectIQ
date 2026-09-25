# Data model

Who is asked and which object is filled: [RESEARCH.md](RESEARCH.md).

User and outreach objects live in `config/excon_schemas.py`. Scratch notes from a live run (`Evidence`, `ProspectReport`, `PersonData`) live in `config/schemas.py` and are mapped before save.

```text
User ──owns──► Product
User ──targets──► Company
Company ──has──► CompanyProfile
Company ──has──► Contact
Contact ──has──► ContactProfile
User + Product + Company + CompanyProfile + Contact + ContactProfile
        ──► OutreachDraft
```

IDs: `us_`, `pd_`, `co_`, `cp_`, `ct_`, `pf_`, `dr_`.

## User

Who is signed in and what they sell. From name / phone / work email plus the company website.

Key fields: `user_id`, `full_name`, `title` (`UserTitle`), `email` (work identity), `outreach_email` (from-address), `outreach_email_verified`, `phone`, `company` (`UserCompany`), `voice`, `product_ids`.

Research signup only collects work email. Until engagement, `outreach_email` defaults to that address. `title` and `company.industry` are catalog enums (`config/catalog.json`). The Next.js form ships the same list as `web/lib/catalog-data.json`.

`User.company` is the user’s firm, not a researched target `Company`.

## Product

One thing the user can pitch. `CompanyProfile.matched_product_ids` points here.

ICP, target industries, value props, use cases, differentiators, objections, typical buyer titles, pricing note, proof points.

Inferred from the user’s website by `OnboardingAgent`.

## Company

The target firm (the record). Name, site, industry, HQ, size, year, short description, what they sell, sources.

`company_id` is `co_…` on live runs. Mock fixtures still use older `pr_…` ids.

## CompanyProfile

The company briefing (how to sell the firm). Joined by `company_id`.

Executive summary, score, recommendation, signals, pain points, risks, recommended approach (roles, not invented names), why relevant to this user, matched products.

## Contact

A person at that company. Joined by `company_id`.

- `decision_role`: economic_buyer | champion | influencer | blocker
- Handles: `email`, `phone`, `linkedin_url`, `whatsapp_number`, `slack_user_id` — any may be missing
- `preferred_channel` + `consent` per channel
- `do_not_contact`

Live research turns Prospeo `PersonData` into this. Email/SMS consent stays false until the user says so. LinkedIn consent is on if a profile URL exists.

Mocks still include: no email, SMS consent off, one DNC contact. Those cases must keep working.

## ContactProfile

The person briefing. Joined by `contact_id` and `company_id`. This is what the outreach prompt reads.

Bio, responsibilities, interests, recent activity, communication style, likely pain vs our product, talking points, risks, recommended approach, language.

Written from the company briefing plus public articles on that person.

## Do-not-contact

`DoNotContactEntry`: `kind` is `contact_id` | `email` | `phone`. Checked before draft and again before send.

## Outreach

| Object | Role |
|---|---|
| `OutreachDraft` | One message, one channel, status `draft` / `approved` / `rejected` / `sent`. Has `company_id`. |
| `OutreachPackage` | All drafts (or a skip reason) for one contact |
| `OutreachBatch` | One `prepare()` run for a user × company |
| `OutreachEvent` | `drafted` / `edited` / `approved` / `rejected` / `sent` / `send_failed` |
| `SendResult` | Connector outcome, including `dry_run` |

`edit()` sets status back to `draft`.

## Fixtures

`data/mock/` is the joined example:

| File | Contents |
|---|---|
| `user.json` | Priya Mehta, NexusFlow |
| `products.json` | Demand Planning, PlantConnect, TradePulse |
| `companies.json` | Asian Paints, Tata Steel, Havells |
| `company_profiles.json` | One briefing per company |
| `contacts.json` | 8 people |
| `contact_profiles.json` | 8 person briefings |
| `do_not_contact.json` | Deepak Nair + bounce fixture |

Load with `data.loader.load_mock_bundle()`.

## Live run files

`UserPipeline` writes `data/runs/<timestamp>/` with `user.json`, `products.json`, `companies.json`, `company_profiles.json`, `contacts.json`, `contact_profiles.json`.

EXCON still defaults to the mock bundle until `prepare()` is pointed at a run.
