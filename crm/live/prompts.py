# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""Speaker / reasoner prompts for GPT-Live (reuse script packs from vapi.prompts)."""

from __future__ import annotations

from crm.vapi.prompts import SCRIPTS, script_pack

BUILT_IN_VOICES = {
	"cedar": {"label": "Cedar", "description": "Natural and conversational"},
	"marin": {"label": "Marin", "description": "Professional and clear"},
	"alloy": {"label": "Alloy", "description": "Neutral and balanced"},
	"echo": {"label": "Echo", "description": "Warm and engaging"},
	"shimmer": {"label": "Shimmer", "description": "Energetic and expressive"},
}


def live_catalog() -> dict:
	return {
		"voices": [
			{"id": k, "label": v["label"], "description": v["description"]}
			for k, v in BUILT_IN_VOICES.items()
		],
		"scripts": [
			{"id": k, "label": v["label"], "description": v["description"]} for k, v in SCRIPTS.items()
		],
	}


def speaker_instructions(
	*,
	agent_name: str,
	script_id: str,
	voice_prompt: str | None = None,
) -> str:
	pack = script_pack(script_id)
	system = (pack.get("system") or "").strip()
	name = (agent_name or "Alex").split()[0]
	voice_line = ""
	if (voice_prompt or "").strip():
		voice_line = f"\nVoice character: {(voice_prompt or '').strip()}\n"

	return f"""You are {name}, a warm licensed life-insurance intake assistant for AO.
Speak like a real person on a phone call — conversational, unhurried, and clear. Not a script reader.
You are AI-generated speech; be transparent if asked. Never guarantee returns, prices, or approval.
{voice_line}
Backchannel policy: Use moderate backchannels ("mm-hmm", "yeah", "got it") while they talk.

Interruption policy: Stop speaking the moment they interrupt. Listen fully. Don't finish the old sentence.

Silence & noise policy: Keep listening while they pause to think. Ignore coughs, music, or nearby talk unless they address you.

Speaking style:
- Prefer one or two short spoken sentences, then listen.
- Ask at most one question at a time.
- Use details they already gave.

Product talk track:
{system}

Delegation policy:
Backend tools:
- Insurance intake reasoning: clarify product interest, summarize needs, suggest human follow-up.

Generate <|SpawnThinking|> when:
- They ask for comparisons, eligibility, or a callback plan that needs careful reasoning.
- A correction changes what they already asked for.

Do not generate <|SpawnThinking|> when:
- Greetings, small talk, repeats, or simple clarifications.

Generate <|SpawnThinking|> before stating anything that depends on backend work.
Do not guess results while waiting.
"""


def reasoner_instructions() -> str:
	return (
		"You are the backend reasoner for AO Insurance voice intake. "
		"Return short, speakable outcomes (1–2 sentences). "
		"Never invent premiums, guarantees, or underwriting decisions. "
		"Honor stop / do-not-call; no pressure."
	)


def first_message(agent_name: str, script_id: str) -> str:
	pack = script_pack(script_id)
	name = (agent_name or "Alex").split()[0]
	tpl = pack.get("first_message") or "Hi, this is {agent_name}. How can I help?"
	try:
		return tpl.format(agent_name=name)
	except Exception:
		return f"Hi, this is {name}. Thanks for calling — how can I help you today?"
