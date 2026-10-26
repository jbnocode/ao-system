# AO CRM changes on top of frappe/crm 1.88.0

Frontend + life-insurance Case hub. Base: frappe/crm `main` at 0baa1e8 (v1.88.0), running on Frappe 16.

## AO Desk admin (`ao` app)

Platform management for **System Manager** lives in a separate Frappe app:

```bash
# from frappe-bench (app lives at apps/ao)
bench --site <site> install-app ao
```

- Desk Apps tile **AO** → `/desk/ao-management`
- Workspace **AO Management**: Platform / Users / Integrations / Agency shortcuts (FCRM Settings, Vapi, Twilio, credits, users, etc.)
- Post-login home is `/crm/ai` for CRM roles (incl. System Manager); Desk stays at `/desk`

## Frontend

- Deal page: tabs Quotes, Applications, Policies; Life journey strip; Deal assistant
- **Life agency mode:** Deals labeled **Cases**, Household contacts, person-first titles, B2B org fields hidden
- Settings → Automation & Rules → **Life Insurance** (pipeline + Case mode + recipes)
- Automations page at `/crm/automations`
- **Campaigns** at `/crm/campaigns` — ERPNext-shaped Campaign + Email Campaign (schedules + enrollments); SMS is a CRM extension alongside Email Template rows
- **Booking** page (`/crm/booking`) + Settings → **Booking** (Google Calendar / Meet / Zoom)
- Public book route `/crm/book/:slug` → Calendly embed or redirect to frappe_appointment `/schedule/in/{slug}`
- UI skill: [`.cursor/skills/frappe-uiux/SKILL.md`](.cursor/skills/frappe-uiux/SKILL.md) — required for every frontend UI build

## Booking (frappe_appointment)

Native scheduling uses [rtCamp/frappe-appointment](https://github.com/rtCamp/frappe-appointment) (AGPLv3):

```bash
bench get-app https://github.com/rtCamp/frappe-appointment.git --branch version-16
bench --site <site> install-app frappe_appointment
bench --site <site> migrate
```

CRM wraps it via `crm.api.booking` (Calendly stays CRM-only).

## AI Voice (GPT-Live + Twilio)

- **Settings → AI Live**: OpenAI GPT-Live key, calling hours, media bridge / SIP
- **Settings → AI Caller**: Twilio assign + agent voice/script (Vapi buy/import frozen)
- Package `crm/live/` — WebRTC test, outbound/inbound Twilio bridge, Call Log `GPT-Live`
- Media bridge: `infra/ao-live-media-bridge/` (see `crm/live/README.md`)
- Legacy Vapi UI: **Settings → AI Calling (Legacy)**

## Backend (`crm/life/`)

- Life deal-status template + five Automation Flow recipes
- Case fields on CRM Deal: `primary_insured`, `case_title`, `date_of_birth`, `tobacco_use`, `insured_state`
- Household `relationship` on CRM Contacts child
- `FCRM Settings.life_agency_mode` + person-first side panel / quick entry layouts
- Quote → Application → Policy convert APIs + Deal assistant

### Install / apply

```bash
bench --site <site> migrate
bench --site <site> execute crm.life.install.install --kwargs "{'replace_pipeline': 1, 'enable_flows': 1, 'enable_life_mode': 1}"
```

Or **Settings → Life Insurance → Apply life pack** (also toggles Life agency mode).
