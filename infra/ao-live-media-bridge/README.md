# AO Live Media Bridge (Twilio ↔ GPT-Live)

Sidecar for Phase 1 phone AI. Twilio Media Streams connect here; the bridge
creates an OpenAI GPT-Live session and relays audio.

## Prefer SIP when possible

If **CRM Live Settings** has SIP trunk fields filled, CRM dials via OpenAI SIP
and this bridge is not used for outbound. Keep the bridge for inbound (and as
outbound fallback) unless you terminate inbound on OpenAI SIP directly.

## Setup

```bash
cd infra/ao-live-media-bridge
cp .env.example .env
# edit CRM_BASE_URL + CRM_LIVE_WEBHOOK_SECRET
npm install
npm start
```

Expose with TLS (ngrok / reverse proxy) as `wss://…/media` and paste that URL
into **Settings → AI Live → Media Stream URL**.

Also set the same webhook secret in CRM Live Settings.

## Flow

1. CRM mints a short-lived call token and returns TwiML `<Connect><Stream url="wss://…?token=…"/>`.
2. Twilio opens a WebSocket to this service.
3. Bridge calls `crm.live.api.resolve_call_token` (Bearer webhook secret) for
   session instructions + OpenAI API key.
4. Bridge creates `gpt-live-1` (WebRTC datachannel path or SIP when available)
   and relays Twilio mulaw ↔ Live audio.

## Health

`GET /health` → `{ ok: true }`
