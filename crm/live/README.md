# GPT-Live + Twilio (Phase 1)

In-CRM web test calls and Twilio phone (inbound/outbound) via OpenAI **GPT-Live-1**.
Vapi remains in the codebase but is **frozen** — new AI Caller paths use Live only.

## Keys & settings

| Where | What |
|---|---|
| **Settings → AI Live** (System Manager) | Enable Live, OpenAI API key (`sk-` / `sk-proj-`), webhook secret, media stream / SIP |
| **Settings → AI Caller** (Manager) | Org defaults, buy/assign Twilio numbers, agent voice + script |
| **Settings → Telephony** | Twilio account (unchanged) |
| **Settings → AI Calling (Legacy)** | Frozen Vapi keys |

Never put the OpenAI key in the browser. WebRTC sessions are created server-side via
`crm.live.api.create_webrtc_session`.

## Media bridge (phone)

```bash
cd infra/ao-live-media-bridge
cp .env.example .env   # CRM_BASE_URL + CRM_LIVE_WEBHOOK_SECRET
npm install && npm start
```

Expose `wss://…/media` and paste into AI Live → **Media Stream URL**.
Prefer OpenAI **SIP** trunk fields for outbound when available.

## Smoke checklist

1. Enable AI Live + save OpenAI key + webhook secret.
2. Manager assigns a Twilio number to an agent (AI Caller).
3. Agent opens `/crm/call` → sees number → **Start test call** (WebRTC).
4. Outbound AI call from dialer / Lead → Call Log `telephony_medium = GPT-Live`.
5. Inbound to that Twilio number → Live TwiML / bridge.
6. SMS on the same number still works (Twilio SMS webhooks unchanged).

## Migrate

```bash
bench --site <site> migrate
```

Patch: `crm.patches.v1_0.ensure_live_settings_fields`
