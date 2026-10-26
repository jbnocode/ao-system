# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import annotations

import frappe
from frappe import _

from crm.live.client import get_client
from crm.live.prompts import BUILT_IN_VOICES


def list_voice_options() -> dict:
	"""Built-in Live voices + any prompt voices we can list."""
	custom = []
	try:
		client = get_client()
		for row in client.list_voices() or []:
			if not isinstance(row, dict):
				continue
			custom.append(
				{
					"id": row.get("id") or row.get("voice_id") or "",
					"label": row.get("name") or row.get("id") or "Custom",
					"description": (row.get("prompt") or row.get("description") or "")[:160],
					"custom": True,
				}
			)
	except Exception:
		# Listing may fail if endpoint/shape differs — built-ins still work
		custom = []

	return {
		"builtin": [
			{"id": k, "label": v["label"], "description": v["description"], "custom": False}
			for k, v in BUILT_IN_VOICES.items()
		],
		"custom": [c for c in custom if c.get("id")],
	}


def create_prompt_voice(name: str, prompt: str, assign_to_org: int | str | None = 0) -> dict:
	"""Create OpenAI prompt-to-voice; optionally set as org default."""
	name = (name or "").strip() or "AO Voice"
	prompt = (prompt or "").strip()
	if not prompt:
		frappe.throw(_("Voice prompt is required"))

	client = get_client()
	# OpenAI prompt-to-voice API shapes vary; try common payloads
	created = None
	last_err = None
	for payload_path in (
		lambda: client.create_prompt_voice(name, prompt),
		lambda: client.request(
			"POST",
			"/audio/voices",
			{"name": name, "type": "prompt", "prompt": prompt},
		),
		lambda: client.request(
			"POST",
			"/voices",
			{"name": name, "prompt": prompt},
		),
	):
		try:
			created = payload_path()
			break
		except Exception as exc:
			last_err = exc
			continue

	if not created:
		frappe.throw(_("Could not create prompt voice: {0}").format(str(last_err)[:200]))

	voice_id = (
		created.get("id")
		or created.get("voice_id")
		or (created.get("voice") or {}).get("id")
		or ""
	)
	if not voice_id:
		frappe.throw(_("OpenAI did not return a voice id"))

	if int(assign_to_org or 0):
		doc = frappe.get_single("CRM Live Settings")
		doc.default_live_voice_id = voice_id
		doc.default_live_voice_prompt = prompt
		doc.save(ignore_permissions=True)

	return {"id": voice_id, "name": name, "prompt": prompt, "raw": created}
