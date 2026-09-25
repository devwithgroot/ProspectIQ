# EXCON

External connectors for engaging prospect contacts. Phase 3 of ProspectIQ.

EXCON does not invent people. It takes a user, the user’s products, a researched prospect, and that prospect's contact profiles, then prepares one message per eligible person.

## API

```python
from app.excon import Excon
from data.loader import load_mock_bundle

bundle = load_mock_bundle()
prospect = bundle.prospect_map()["pr_asian_paints"]
excon = Excon(dry_run=True, dnc=bundle.dnc)

batch = excon.prepare(
    user=bundle.user,
    prospect=prospect,
    profiles=bundle.profiles_for(prospect.prospect_id),
    contacts=bundle.contacts_for(prospect.prospect_id),
    products=bundle.products_for(prospect),
)

excon.edit(draft_id, body="...")
excon.approve(draft_id)
excon.send(draft_id)    # raises if not approved
```

`Excon.reject(draft_id)` is also available. Sent drafts cannot be approved or rejected again.

## Draft rules

- Primary channel first: `preferred_channel` if handle + consent exist, else the first eligible of email → LinkedIn → WhatsApp → Slack → SMS
- Skip DNC, missing handle, or no consent
- Use only provided facts (user, product, prospect, profile)
- Channel shape:
  - Email: subject, 120–180 words, unsubscribe line
  - LinkedIn: ~300 characters, no subject
  - WhatsApp: short, mobile
  - Slack: 1–3 sentences
  - SMS: shorter than WhatsApp, STOP line
- JSON from the model is fence-stripped and retried once

## Send gates

`Connector.send()` refuses unless all of these hold:

1. `draft.status == "approved"`
2. Contact is not on the DNC list
3. Channel consent is true
4. Handle is present

`EXCON_DRY_RUN` defaults to `true`. Dry-run logs the payload and marks the draft `sent` without a network call.

## Connectors

| Channel | Module | Live send |
|---|---|---|
| Email | `connectors/email.py` | SMTP if `SMTP_*` is set |
| Slack | `connectors/slack.py` | Slack Web API if `SLACK_BOT_TOKEN` is set |
| SMS | `connectors/sms.py` | Twilio-shaped if `TWILIO_*` is set |
| WhatsApp | `connectors/whatsapp.py` | Cloud API if `WHATSAPP_*` is set |
| LinkedIn | `connectors/linkedin.py` | Stub only. No scraping |

Missing credentials return `SendResult(success=False, error=...)` rather than pretending the message went out.

## Events

Every state change appends an `OutreachEvent`. Phase 4 analytics should read this log, not scrape connector APIs first.

## Test

```bash
./run_excon.sh
```

Requires `.env` with a reachable `MLX_BASE_URL`. Outreach drafts call Qwen; connector tests stay local.
