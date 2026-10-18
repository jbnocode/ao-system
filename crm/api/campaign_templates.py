# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""Starter CRM Campaign recipes (definition + schedules). Enroll via Email Campaign."""

from __future__ import annotations

import frappe
from frappe import _


# Email rows use Email Template (ERPNext Campaign Email Schedule).
# SMS rows are a CRM extension on the same schedule table.
TEMPLATES = [
	{
		"id": "quote_follow_up_email",
		"title": "Quote follow-up (email)",
		"description": "Day 0 welcome + day 2 reminder via Email Template.",
		"category": "email",
		"schedules": [
			{
				"channel": "Email",
				"send_after_days": 0,
				"email_template": "CRM Outbound Lead Welcome",
			},
			{
				"channel": "Email",
				"send_after_days": 2,
				"email_template": "CRM Lead Follow Up",
			},
		],
	},
	{
		"id": "welcome_sms",
		"title": "Welcome SMS (3-day)",
		"description": "Day 0 hello + day 3 check-in by SMS.",
		"category": "sms",
		"schedules": [
			{
				"channel": "SMS",
				"send_after_days": 0,
				"sms_body": (
					"Hi {{ doc.first_name or 'there' }}, thanks for connecting — "
					"happy to help with life coverage whenever you're ready."
				),
			},
			{
				"channel": "SMS",
				"send_after_days": 3,
				"sms_body": (
					"Hi {{ doc.first_name or 'there' }}, just checking in — "
					"want a quick call this week about your options?"
				),
			},
		],
	},
	{
		"id": "needs_analysis_nurture",
		"title": "Needs analysis nurture",
		"description": "SMS kickoff, then Email Template follow-up three days later.",
		"category": "mixed",
		"schedules": [
			{
				"channel": "SMS",
				"send_after_days": 0,
				"sms_body": (
					"Hi {{ doc.first_name or 'there' }}, I'll send a short needs summary soon — "
					"reply with any budget or timeline notes."
				),
			},
			{
				"channel": "Email",
				"send_after_days": 3,
				"email_template": "CRM Lead Follow Up",
			},
		],
	},
	{
		"id": "exam_reminder_sms",
		"title": "Exam reminder SMS",
		"description": "Day 0 confirmation + day 1 reminder before the medical exam.",
		"category": "sms",
		"schedules": [
			{
				"channel": "SMS",
				"send_after_days": 0,
				"sms_body": (
					"Hi {{ doc.first_name or 'there' }}, your exam is on the calendar. "
					"Bring a photo ID and list of medications."
				),
			},
			{
				"channel": "SMS",
				"send_after_days": 1,
				"sms_body": (
					"Reminder: exam coming up. Reply if you need to reschedule."
				),
			},
		],
	},
]


def _require_role():
	if not any(
		r in ("System Manager", "Sales Manager", "Sales User") for r in frappe.get_roles()
	):
		frappe.throw(_("Not permitted to manage campaigns"), frappe.PermissionError)


def _resolved_schedules(raw: list[dict]) -> list[dict]:
	rows = []
	for step in raw:
		channel = step.get("channel") or "Email"
		row = {
			"channel": channel,
			"send_after_days": int(step.get("send_after_days") or 0),
			"email_template": "",
			"sms_body": step.get("sms_body") or "",
		}
		if channel == "Email":
			tpl = step.get("email_template") or ""
			if tpl and frappe.db.exists("Email Template", tpl):
				row["email_template"] = tpl
			else:
				# Keep Email channel; pick any available Email Template, else SMS fallback
				fallback = frappe.get_all(
					"Email Template", pluck="name", limit=1, order_by="modified desc"
				)
				if fallback:
					row["email_template"] = fallback[0]
				else:
					row["channel"] = "SMS"
					row["sms_body"] = _(
						"Hi {{ doc.first_name or 'there' }}, following up on your file — reply when you're free."
					)
		rows.append(row)
	return rows


@frappe.whitelist()
def list_campaign_templates() -> list[dict]:
	_require_role()
	return [
		{
			"id": t["id"],
			"title": _(t["title"]),
			"description": _(t["description"]),
			"category": t["category"],
			"channel": "SMS"
			if t["category"] == "sms"
			else ("Email" if t["category"] == "email" else "Mixed"),
		}
		for t in TEMPLATES
	]


@frappe.whitelist()
def create_from_template(template_id: str, campaign_name: str | None = None) -> dict:
	_require_role()
	frappe.has_permission("CRM Campaign", "create", throw=True)

	meta = next((t for t in TEMPLATES if t["id"] == template_id), None)
	if not meta:
		frappe.throw(_("Unknown campaign template: {0}").format(template_id))

	title = (campaign_name or "").strip() or meta["title"]
	doc = frappe.get_doc(
		{
			"doctype": "CRM Campaign",
			"campaign_name": title,
			"description": meta["description"],
			"campaign_schedules": _resolved_schedules(meta["schedules"]),
		}
	)
	doc.insert()
	from crm.api.campaign import get_campaign

	return get_campaign(doc.name)
