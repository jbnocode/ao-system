# AO GPT-Live-1 direct demo (no Vapi)

Local WebRTC page that talks to **OpenAI GPT-Live-1** directly, so you can A/B
conversational nuance against the Vapi-wrapped assistant.

| Lane | How to try |
| --- | --- |
| **A · Direct OpenAI** | This app → `http://localhost:3000` |
| **B · Vapi** | Web call / `+1 (912) 766-9359` → assistant `ab2fd5b7-84c8-4909-9683-8eb7e05b44c2` |

## Requirements

- Node.js **≥ 22.6**
- OpenAI project API key with GPT-Live access

## Setup

```bash
cd infra/ao-gpt-live-demo
npm install

# Required: a real OpenAI API key (sk-… / sk-proj-…)
# Note: CRM AI Settings currently stores a Bedrock key — that will NOT work here.
export OPENAI_API_KEY='sk-proj-...'

npm start
```

Get a key from [platform.openai.com/api-keys](https://platform.openai.com/api-keys)
(project must have GPT-Live access).

Open [http://localhost:3000](http://localhost:3000), allow the mic, click
**Start conversation**.

## What to listen for

Same tests as OpenAI’s marketing demo:

1. Talk over the assistant mid-reply, then change the question  
2. Pause to think — it should wait  
3. Laugh / hesitate / short acknowledgments  

If **A** feels close to openai.com and **B** still feels stiff, the gap is the
Vapi integration — not the model ID alone.

## Notes

- Localhost only (`127.0.0.1`). Do not expose `/api/session` publicly without auth.
- Billed by OpenAI Live session duration (+ reasoner if it delegates).
- This demo uses a free-form “companion” prompt on purpose so nuance isn’t
  crushed by insurance scripting. Product prompts can be layered later.
