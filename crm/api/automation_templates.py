# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""Catalog of Automation Flow starters for the Automations → Templates library.

General recipes come from `crm.automation.reference_flows`; insurance recipes
from `crm.life.flows`. Creating from a template inserts a disabled draft so
authors can review before enabling.
"""

from __future__ import annotations

import frappe
from frappe import _

from crm.automation import reference_flows as rf
from crm.life import flows as life


# id → catalog row + builder callable. Titles come from the builder payload so
# the library stays in sync with install() recipes.
_TEMPLATE_META = {
	"welcome_sequence": {
		"description": "Welcome new leads by source, then follow up after two days.",
		"category": "general",
		"build": rf.welcome_sequence,
	},
	"reply_temperature": {
		"description": "Warm / hot / cold temperature from email replies.",
		"category": "general",
		"build": rf.reply_temperature,
	},
	"profile_scoring": {
		"description": "Score a lead from profile fields when it is created.",
		"category": "general",
		"build": rf.profile_scoring,
	},
	"assign_on_outreach": {
		"description": "Assign the lead when your team emails it.",
		"category": "general",
		"build": rf.assign_on_outreach,
	},
	"lead_routing": {
		"description": "Route the lead as key fields change.",
		"category": "general",
		"build": rf.lead_routing,
	},
	"qualified_routing": {
		"description": "Route the lead once it becomes Qualified.",
		"category": "general",
		"build": rf.qualified_routing,
	},
	"engagement_scoring": {
		"description": "Rescore the lead as engagement fields change.",
		"category": "general",
		"build": rf.engagement_scoring,
	},
	"qualified_conversion": {
		"description": "Turn a Qualified lead into a Deal.",
		"category": "general",
		"build": rf.qualified_conversion,
	},
	"stalled_deal": {
		"description": "Follow up when a deal stalls in the pipeline.",
		"category": "general",
		"build": rf.stalled_deal,
	},
	"high_value_deal_watch": {
		"description": "Watch high-value deals and alert the owner.",
		"category": "general",
		"build": rf.high_value_deal_watch,
	},
	"life_quote_follow_up": {
		"description": "Task to follow up three days after a life quote is sent.",
		"category": "insurance",
		"build": life.quoted_follow_up,
	},
	"life_schedule_exam": {
		"description": "Schedule a medical exam after the application is submitted.",
		"category": "insurance",
		"build": life.application_exam_task,
	},
	"life_exam_reminder": {
		"description": "Confirm the exam appointment once it is scheduled.",
		"category": "insurance",
		"build": life.exam_reminder,
	},
	"life_underwriting_check_in": {
		"description": "Track underwriting and nudge if it is still open after a week.",
		"category": "insurance",
		"build": life.underwriting_check_in,
	},
	"life_policy_welcome": {
		"description": "Welcome call and 30-day service check after policy delivery.",
		"category": "insurance",
		"build": life.policy_delivered_welcome,
	},
}


def _check_create():
	if not frappe.has_permission("Automation Flow", ptype="create"):
		frappe.throw(_("Not permitted"), frappe.PermissionError)


@frappe.whitelist()
def list_automation_templates() -> list[dict]:
	"""Rows for the Automations template library dialog."""
	_check_create()
	if not frappe.db.exists("DocType", "Automation Flow"):
		return []

	out = []
	for tid, meta in _TEMPLATE_META.items():
		payload = meta["build"]()
		out.append(
			{
				"id": tid,
				"title": _(payload.get("title") or tid),
				"description": _(meta["description"]),
				"category": meta["category"],
				"document_type": payload.get("document_type") or "",
				"trigger_type": payload.get("trigger_type") or "",
			}
		)
	return out


@frappe.whitelist()
def create_from_template(template_id: str) -> dict:
	"""Insert a disabled Automation Flow from a catalog template and return it."""
	_check_create()
	meta = _TEMPLATE_META.get(template_id)
	if not meta:
		frappe.throw(_("Unknown automation template: {0}").format(template_id))
	if not frappe.db.exists("DocType", "Automation Flow"):
		frappe.throw(_("Automation Flow is not installed on this site"))

	# Email templates / life statuses some recipes depend on
	if meta["category"] == "general":
		rf.ensure_email_templates()
	else:
		from crm.life.pipeline import ensure_life_statuses

		ensure_life_statuses()

	payload = meta["build"]()
	payload["enabled"] = 0
	payload["title"] = _unique_title(payload.get("title") or template_id)
	# Drop identity if a builder ever leaks it
	payload.pop("name", None)

	doc = frappe.get_doc(payload)
	doc.insert()
	return {"name": doc.name, "title": doc.title}


def _unique_title(title: str) -> str:
	"""Avoid colliding with an existing flow title (install recipes share names)."""
	if not frappe.db.exists("Automation Flow", {"title": title}):
		return title
	taken = set(frappe.get_all("Automation Flow", pluck="title"))
	index = 1
	while f"{title} ({index})" in taken:
		index += 1
	return f"{title} ({index})"
