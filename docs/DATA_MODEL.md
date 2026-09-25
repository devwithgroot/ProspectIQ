# Data model

EXCON and the mocks use this graph. Phase 1–2 research objects stay in `config/schemas.py` and will map into `Prospect` later.

```text
User ──owns──► Product
User ──targets──► Prospect
Prospect ──has──► Contact
Contact ──has──► ContactProfile
ContactProfile + User + Product + Prospect ──► OutreachDraft
```

IDs are stable strings so files and future APIs can join: `us_`, `pd_`, `pr_`, `ct_`, `pf_`, `dr_`.

## User (seller)

Who is logged in and what they sell. Created from name / phone / email plus the company website.

Key fields: `user_id`, `full_name`, `title`, `email`, `phone`, `company` (`SellerCompany`), `voice` (tone, signature, calendar, CTA), `product_ids`.

Without `voice` and products, outreach has no sender and no offer.

## Product

One thing the seller can pitch. Prospects point at these with `matched_product_ids`.

Includes ICP, target industries, value props, use cases, differentiators, objections, typical buyer titles, pricing note, proof points.

Onboarding should infer these from the company site; the seller should be able to edit them.

## Prospect (company of interest)

A company the seller cares about. Comes from upload and/or later discovery, then research fills the rest.

Includes identity (name, site, industry, HQ, size), what they sell, signals, pain points, `overall_score`, `recommendation`, `why_relevant_to_user`, `matched_product_ids`, sources.

This is the object EXCON consumes instead of a raw `ProspectReport`.

## Contact

A person at a prospect. Handles, role, consent.

- `decision_role`: economic_buyer | champion | influencer | blocker
- Handles: `email`, `phone`, `linkedin_url`, `whatsapp_number`, `slack_user_id` — any may be missing
- `preferred_channel` + `consent` per channel
- `do_not_contact`

Mocks include: no email, SMS consent off, one DNC contact. Those cases must keep working.

## ContactProfile

Researched view of the contact. This is what the outreach prompt reads.

Bio, responsibilities, interests, recent activity, communication style, likely pain vs our product, talking points, risks, recommended approach, language.

## Do-not-contact

`DoNotContactEntry`: `kind` is `contact_id` | `email` | `phone`. Matched against the contact before draft and again before send.

## Outreach

| Object | Role |
|---|---|
| `OutreachDraft` | One message, one channel, status `draft` / `approved` / `rejected` / `sent` |
| `OutreachPackage` | All drafts (or a skip reason) for one contact |
| `OutreachBatch` | One prepare() run for a user × prospect |
| `OutreachEvent` | `drafted` / `edited` / `approved` / `rejected` / `sent` / `send_failed` |
| `SendResult` | Connector outcome, including `dry_run` |

`edit()` sets status back to `draft`.

## Fixtures

`data/mock/` is the joined example of this graph:

| File | Contents |
|---|---|
| `user.json` | Priya Mehta, NexusFlow |
| `products.json` | Demand Planning, PlantConnect, TradePulse |
| `prospects.json` | Asian Paints, Tata Steel, Havells |
| `contacts.json` | 8 people |
| `profiles.json` | 8 profiles |
| `do_not_contact.json` | Deepak Nair + bounce fixture |

Load with `data.loader.load_mock_bundle()`.

## Mapping from today's research pipeline

`ProspectIQ.analyze()` returns `ProspectReport` (summary, score, signals, evidence). That is company-only.

Future adapter:

1. `ProspectReport` → `Prospect`
2. New contact finder → `Contact` list
3. New profile builder → `ContactProfile` list
4. Signup + website → `User` + `Product` list
5. Upload rows → `Prospect` shells before research
