# AO Simulation Game — AWS-hosted demo (disposable)

Spec: [`.pi/feats/simulation-game/spec.md`](../../.pi/feats/simulation-game/spec.md) §11.
Selected Region: `ap-southeast-2` (confirm in AWS Settings before deploy).
Hosting/state/voice run on AWS; the AI brain is the OpenAI API (decision
2026-10-20 — this FREE project's Bedrock quotas are 0). Nova Sonic is
**not** used — verified unavailable in this Region on Bedrock.

## Slices (all built locally 2026-10-20; NOT deployed yet)

- **D1 ✅:** CDK skeleton — S3+CloudFront site, HTTP API + Lambda, DynamoDB runs table (TTL).
- **D2 ✅ (revised):** Game brain — 30 stages, 9 objections, personas P1+P6, scripted
  fallback + AI prospect/coach. **Primary brain: OpenAI API** (`gpt-4o-mini`, Platform
  key from Secrets Manager — a ChatGPT/OpenAI Business subscription is NOT API access).
  Bedrock Converse retained as code path (quotas are 0 today). 14 unit tests green.
- **D3 ✅:** Playable UI — briefing → roleplay → report card (persona, difficulty,
  objection chips, manual stage move, fresh-run isolation).
- **D4 ✅ (revised):** Open-source voice — **Kokoro TTS + faster-whisper STT** container
  Lambda (`lambda-voice/`, models baked in), blocked on the sensitive Application
  stage. Deploy with `AO_SIM_VOICE=1` (needs Docker). Supersedes Polly/Transcribe —
  Transcribe is SCP-denied in this project anyway. 3 handler tests green.
- **Remaining:** pre-deploy gate (below) → deploy → acceptance run → teardown decision.

## Local (no AWS spend)

```bash
cd infra/ao-sim-demo
npm install
npm test          # template assertions
npx cdk synth --strict
npx cdk diff      # always diff before deploy; construct renames = replacements
```

## Live findings 2026-10-20 (verified against this project, ap-southeast-2)

- Identity OK after `aws login`: project `542468167557`, FREE plan, $97.85 credits.
- **Bedrock text models are AUTHORIZED/AVAILABLE but every on-demand daily-token
  quota is 0** → Converse returns `ThrottlingException: Too many tokens per day`.
  Nova 2 Lite / Claude 4.x also require cross-Region inference profiles (excluded
  by the single-Region rule). Real AI turns need a plan/quota change (see gate).
- **Amazon Transcribe is explicitly denied by the project's managed SCP** —
  D4 voice-in cannot use Transcribe in this project. Polly works (tested).
  Fallback for voice-in: browser speech recognition (as in the original Mac app).
- Deploying anyway is safe for the game itself: with no model configured the
  Lambda runs the scripted fallback (`ai_available: false`) — playable, scored.

## Pre-deploy gate (required, in order)

1. Confirm Region: AWS Settings > View all projects > Overview > Additional Info.
2. Check plan type + spend-limit status (AWS Settings > Billing).
3. Set a budget alert (Billing and Cost Management console).
4. Verify the Bedrock text model exists in `ap-southeast-2` and set
   `AO_SIM_MODEL_ID` (scope the Lambda Bedrock policy to its ARN — the
   skeleton ships `*` as a marked placeholder).
5. `npx cdk bootstrap` (first time only), then `diff`, then `deploy`.

## Teardown (default ending for this demo)

```bash
npx cdk destroy   # bucket auto-deletes objects; table is DESTROY + TTL
```

After destroy, ask: keep anything (e.g. exported report cards) or is the
project clean? Default answer is clean.
