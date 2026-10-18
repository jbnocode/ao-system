# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""Offline demo replies when no API key is configured."""

from __future__ import annotations

import json


def demo_response(prompt: str, context: dict | None = None) -> dict:
	text = (prompt or "").lower()
	context = context or {}
	context_type = (context.get("type") or "general").lower()

	if context_type == "automation_builder":
		return automation_demo(text)

	from crm.ai.insurance_context import get_insurance_snapshot, insurance_reply_for_prompt

	insurance = insurance_reply_for_prompt(prompt, get_insurance_snapshot())
	if insurance:
		insurance["demo"] = True
		return insurance

	if "credit" in text or "top up" in text or "topup" in text:
		return {
			"reply": "Ask a System Manager to open Settings → AI and grant you credits, or use Grant credits there.",
			"ops": [],
			"blocks": [],
			"demo": True,
		}

	if "lead" in text:
		return {
			"reply": "To work leads: open Leads from the sidebar, create or import records, then move them through statuses. Need automations? Open Automations and use the Assistant there.",
			"ops": [],
			"blocks": [],
			"demo": True,
		}

	return {
		"reply": (
			"I'm the AO CRM assistant (demo mode — no API key). "
			"Try “generate quotes for a 56-year-old in Indiana”, “show my quotes”, or “show my policies”."
		),
		"ops": [],
		"blocks": [],
		"demo": True,
	}


def automation_demo(text: str) -> dict:
	if "qualif" in text or ("status" in text and "change" in text):
		return {
			"reply": "I'll set a Field Value Changed trigger on status → Qualified and add a follow-up task.",
			"ops": [
				{
					"op": "set_meta",
					"title": "Qualified lead follow-up",
					"document_type": "CRM Lead",
				},
				{
					"op": "set_trigger",
					"trigger_type": "Field Value Changed",
					"trigger_field": "status",
					"to_value": "Qualified",
					"document_type": "CRM Lead",
				},
				{
					"op": "add_step",
					"values": {
						"step_type": "Action",
						"action_type": "CreateDocument",
						"params": json.dumps(
							{
								"doctype": "CRM Task",
								"values": {
									"title": "Follow up with qualified lead",
									"priority": "High",
								},
							}
						),
					},
				},
			],
			"demo": True,
		}

	if "follow" in text or "wait" in text or "day" in text:
		return {
			"reply": "I'll add a 2-day wait, then create a CRM Task to follow up.",
			"ops": [
				{
					"op": "set_meta",
					"title": "Follow up after 2 days",
				},
				{
					"op": "set_trigger",
					"trigger_type": "Doc Created",
					"document_type": "CRM Lead",
				},
				{
					"op": "add_step",
					"values": {
						"step_type": "Wait",
						"params": json.dumps({"value": 2, "unit": "Days"}),
					},
				},
				{
					"op": "add_step",
					"values": {
						"step_type": "Action",
						"action_type": "CreateDocument",
						"params": json.dumps(
							{
								"doctype": "CRM Task",
								"values": {"title": "Follow up with lead"},
							}
						),
					},
				},
			],
			"demo": True,
		}

	return {
		"reply": "Try: “follow up after 2 days” or “when status becomes Qualified create a task”. I'll propose steps you can Apply to the canvas.",
		"ops": [],
		"demo": True,
	}
