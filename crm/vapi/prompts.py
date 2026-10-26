# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""Script packs + voice mappings for AI caller assistants."""

from __future__ import annotations

# Quality presets → provider TTS model ids (wired in voice_payload).
VOICE_MODELS = {
	"realistic": {
		"label": "Most realistic",
		"description": "Highest naturalness; slightly higher latency.",
		"model": "eleven_v3",
	},
	"balanced": {
		"label": "Balanced",
		"description": "Strong quality with snappier turn-taking on live calls.",
		"model": "eleven_v4_turbo",
	},
	"fast": {
		"label": "Fastest",
		"description": "Lowest latency; still clear on phone audio.",
		"model": "eleven_flash_v2_5",
	},
}

VOICES = {
	"warm": {
		"label": "Warm & professional",
		"description": "Calm, clear delivery for needs analysis and trust-building.",
		"vapi": {"provider": "11labs", "voiceId": "sarah"},
	},
	"energetic": {
		"label": "Upbeat & engaging",
		"description": "Friendly energy for outreach and appointment setting.",
		"vapi": {"provider": "11labs", "voiceId": "harry"},
	},
	"steady": {
		"label": "Steady & consultative",
		"description": "Measured tone for complex products and underwriting talk tracks.",
		"vapi": {"provider": "11labs", "voiceId": "daniel"},
	},
}

SCRIPTS = {
	"iul": {
		"label": "IUL - Indexed Universal Life",
		"description": "For prospects interested in tax-advantaged growth and flexible premium payments.",
		"first_message": "Hi, this is {agent_name} calling about indexed universal life options. Do you have a couple of minutes?",
		"system": (
			"You are a licensed life insurance agent assistant calling about Indexed Universal Life (IUL). "
			"Be concise, compliant, and never guarantee returns. Qualify interest in tax-advantaged growth "
			"and flexible premiums, then offer to schedule a human follow-up. If they ask to stop, apologize and end."
		),
	},
	"ibc": {
		"label": "Infinite Banking Concept",
		"description": "For prospects interested in becoming their own bank and building generational wealth.",
		"first_message": "Hi, this is {agent_name}. I'm reaching out about infinite banking strategies. Is now a good time?",
		"system": (
			"You are a life insurance agent assistant discussing the Infinite Banking Concept using whole life. "
			"Educate simply, avoid hype, and book a discovery call with a human agent. Honor opt-outs immediately."
		),
	},
	"final_expense": {
		"label": "Final Expense Insurance",
		"description": "For prospects ages 50-85 seeking affordable burial and final expense coverage.",
		"first_message": "Hi, this is {agent_name} calling about final expense coverage. Do you have a moment?",
		"system": (
			"You are a final expense insurance assistant for ages 50–85. Be respectful and clear about burial/"
			"final expense coverage. Qualify interest and schedule a callback. Never pressure; honor Do Not Call."
		),
	},
	"term": {
		"label": "Term Life Insurance",
		"description": "For prospects needing affordable, straightforward death benefit protection.",
		"first_message": "Hi, this is {agent_name} about term life protection. Is this a good time for a quick chat?",
		"system": (
			"You are a term life insurance assistant. Focus on affordable death benefit protection for a set term. "
			"Ask about dependents and coverage goals, then offer to connect with a licensed agent. Honor opt-outs."
		),
	},
	"custom": {
		"label": "Custom",
		"description": "Blank talk track for the agent to refine later.",
		"first_message": "Hi, this is {agent_name}. Thanks for taking my call — how are you today?",
		"system": (
			"You are a helpful life insurance sales assistant. Be brief, professional, and compliant. "
			"Qualify interest and offer to schedule a follow-up with a human agent. Honor opt-outs immediately."
		),
	},
}


def voice_payload(voice_id: str, voice_model: str | None = None) -> dict:
	meta = VOICES.get(voice_id) or VOICES["warm"]
	payload = dict(meta["vapi"])
	model_meta = VOICE_MODELS.get(voice_model or "") or VOICE_MODELS["realistic"]
	payload["model"] = model_meta["model"]
	return payload


def script_pack(script_id: str) -> dict:
	return SCRIPTS.get(script_id) or SCRIPTS["custom"]


def catalog() -> dict:
	return {
		"voices": [
			{"id": k, "label": v["label"], "description": v["description"]} for k, v in VOICES.items()
		],
		"voice_models": [
			{"id": k, "label": v["label"], "description": v["description"]} for k, v in VOICE_MODELS.items()
		],
		"scripts": [
			{"id": k, "label": v["label"], "description": v["description"]} for k, v in SCRIPTS.items()
		],
	}
