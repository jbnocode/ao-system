# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""Build GPT-Live session configs for web and phone."""

from __future__ import annotations

import frappe

from crm.live.client import get_client
from crm.live.prompts import first_message, reasoner_instructions, speaker_instructions


def resolve_agent_context(user: str | None = None) -> dict:
	user = user or frappe.session.user
	settings = frappe.get_single("CRM Live Settings")
	agent = None
	if frappe.db.exists("CRM AI Caller Agent", user):
		agent = frappe.get_doc("CRM AI Caller Agent", user)

	full_name = frappe.db.get_value("User", user, "full_name") or user.split("@")[0]
	script_id = (agent.script_id if agent else None) or settings.default_script_id or "term"
	voice_prompt = (agent.live_voice_prompt if agent else None) or settings.default_live_voice_prompt or ""
	live_voice_id = (agent.live_voice_id if agent else None) or settings.default_live_voice_id or ""
	builtin = (agent.voice_id if agent else None) or settings.default_voice_id or "cedar"
	phone = (agent.phone_number if agent else None) or ""

	return {
		"user": user,
		"full_name": full_name,
		"script_id": script_id,
		"voice_prompt": voice_prompt,
		"live_voice_id": (live_voice_id or "").strip(),
		"builtin_voice": (builtin or "cedar").strip(),
		"phone_number": phone,
		"respect_dnc": bool(agent.respect_dnc) if agent else True,
		"first_message": first_message(full_name, script_id),
	}


def build_session_payload(ctx: dict | None = None) -> dict:
	ctx = ctx or resolve_agent_context()
	instructions = speaker_instructions(
		agent_name=ctx["full_name"],
		script_id=ctx["script_id"],
		voice_prompt=ctx.get("voice_prompt"),
	)
	# Include first message guidance in instructions (Live generates greeting)
	instructions = (
		f"{instructions}\n\n"
		f"When the call starts, greet with something like: {ctx['first_message']}\n"
		"Then listen."
	)

	audio_voice: dict | str
	if ctx.get("live_voice_id"):
		audio_voice = {"id": ctx["live_voice_id"]}
	else:
		audio_voice = ctx.get("builtin_voice") or "cedar"

	return {
		"model": "gpt-live-1",
		"instructions": instructions,
		"audio": {"output": {"voice": audio_voice}},
		"delegation": {
			"type": "responses",
			"responses": {
				"model": "gpt-5.6-terra",
				"instructions": reasoner_instructions(),
				"tool_choice": "auto",
			},
		},
	}


def create_webrtc_session(sdp: str, user: str | None = None) -> dict:
	if not (sdp or "").strip():
		frappe.throw(frappe._("An SDP offer is required"))
	ctx = resolve_agent_context(user)
	client = get_client()
	result = client.create_webrtc_session(sdp.strip(), build_session_payload(ctx))
	return {
		"session": result.get("session") or {},
		"transport": result.get("transport") or {},
		"agent": {
			"user": ctx["user"],
			"phone_number": ctx["phone_number"],
			"script_id": ctx["script_id"],
		},
	}
