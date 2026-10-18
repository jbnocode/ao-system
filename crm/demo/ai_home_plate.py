# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""Seed AI home briefing work for role users (tasks, cold leads, meetings).

	bench --site <site> execute crm.demo.ai_home_plate.apply
	bench --site <site> execute crm.demo.ai_home_plate.apply --kwargs "{'user': 'sales.user@local.dev'}"
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta

import frappe
from frappe.utils import get_datetime, getdate, now_datetime

STATE_KEY = "crm_ai_home_plate"
DEFAULT_USER = "sales.manager@local.dev"


def apply(user: str | None = None) -> dict:
	"""Idempotent: replace prior plate seed for this user, then create fresh rows."""
	frappe.set_user("Administrator")
	user = (user or DEFAULT_USER).strip()
	if not frappe.db.exists("User", user):
		frappe.throw(f"User {user} does not exist — run crm.seed_role_users.execute first")

	_clear_user_state(user)

	now = now_datetime()
	today = getdate()
	lead_names = _seed_leads(user, now)
	task_names = _seed_tasks(user, lead_names, now)
	event_names = _seed_meetings(user, today)

	state = _load_state()
	state[user] = {
		"leads": lead_names,
		"tasks": task_names,
		"events": event_names,
	}
	_save_state(state)
	frappe.db.commit()

	from crm.ai.home import get_home_briefing

	frappe.set_user(user)
	brief = get_home_briefing()
	result = {
		"user": user,
		"leads": lead_names,
		"tasks": task_names,
		"events": event_names,
		"stats": brief.get("stats"),
	}
	print(frappe.as_json(result, indent=2))
	return result


def clear(user: str | None = None) -> dict:
	"""Remove plate seed for one user (or all if user is None)."""
	frappe.set_user("Administrator")
	state = _load_state()
	if user:
		_clear_user_state(user.strip())
		state.pop(user.strip(), None)
	else:
		for email in list(state.keys()):
			_clear_user_state(email)
		state = {}
	_save_state(state)
	frappe.db.commit()
	return {"cleared": True, "remaining": list(state.keys())}


def _seed_leads(user: str, now: datetime) -> list[str]:
	specs = [
		{
			"first_name": "Nora",
			"last_name": "Whitfield",
			"email": "nora.whitfield.plate@example.com",
			"organization": "Whitfield Family Office",
			"status": "Contacted",
			"lead_temperature": "Cold",
			"job_title": "Household CFO",
			"source": "Referral",
			"days_ago": 45,
		},
		{
			"first_name": "Marcus",
			"last_name": "Hale",
			"email": "marcus.hale.plate@example.com",
			"organization": "Hale Logistics",
			"status": "Nurture",
			"lead_temperature": "Cold",
			"job_title": "Owner",
			"source": "Cold Calling",
			"days_ago": 32,
		},
		{
			"first_name": "Priya",
			"last_name": "Nair",
			"email": "priya.nair.plate@example.com",
			"organization": "Nair Consulting",
			"status": "New",
			"lead_temperature": "Cold",
			"job_title": "Principal",
			"source": "Website",
			"days_ago": 21,
		},
		{
			"first_name": "Owen",
			"last_name": "Brooks",
			"email": "owen.brooks.plate@example.com",
			"organization": "Brooks Dental Group",
			"status": "Contacted",
			"lead_temperature": "Warm",
			"job_title": "Practice Manager",
			"source": "Advertisement",
			"days_ago": 6,
		},
	]
	created = []
	for spec in specs:
		days_ago = spec.pop("days_ago")
		ts = now - timedelta(days=days_ago)
		doc = frappe.get_doc(
			{
				"doctype": "CRM Lead",
				"lead_owner": user,
				"mobile_no": "+1 555 200 0100",
				**spec,
			}
		)
		doc.flags.ignore_permissions = True
		doc.insert()
		frappe.db.set_value(
			"CRM Lead",
			doc.name,
			{
				"owner": user,
				"modified_by": user,
				"creation": ts,
				"modified": ts,
				"lead_owner": user,
				"lead_temperature": spec["lead_temperature"],
			},
			update_modified=False,
		)
		created.append(doc.name)
	return created


def _seed_tasks(user: str, lead_names: list[str], now: datetime) -> list[str]:
	ref0 = lead_names[0] if lead_names else None
	ref1 = lead_names[1] if len(lead_names) > 1 else ref0
	ref2 = lead_names[2] if len(lead_names) > 2 else ref0
	specs = [
		{
			"title": "Re-engage Nora Whitfield (cold)",
			"priority": "High",
			"status": "Todo",
			"due_date": now - timedelta(days=2),
			"reference_docname": ref0,
			"description": "No reply in 3 weeks — call or send a short check-in about term coverage.",
		},
		{
			"title": "Prep Hale Logistics discovery notes",
			"priority": "High",
			"status": "Todo",
			"due_date": now.replace(hour=17, minute=0, second=0, microsecond=0),
			"reference_docname": ref1,
			"description": "Pull last call notes before today's afternoon meeting.",
		},
		{
			"title": "Send Priya Nair welcome packet",
			"priority": "Medium",
			"status": "In Progress",
			"due_date": now + timedelta(days=1),
			"reference_docname": ref2,
			"description": "Email brochure + calendar link for a 20-min intro.",
		},
		{
			"title": "Review pipeline for Monday standup",
			"priority": "Low",
			"status": "Backlog",
			"due_date": now + timedelta(days=3),
			"reference_docname": ref0,
			"description": "Flag deals stuck in Qualification / Proposal.",
		},
	]
	created = []
	for spec in specs:
		doc = frappe.get_doc(
			{
				"doctype": "CRM Task",
				"assigned_to": user,
				"reference_doctype": "CRM Lead" if spec.get("reference_docname") else None,
				**spec,
			}
		)
		doc.flags.ignore_permissions = True
		doc.insert()
		frappe.db.set_value(
			"CRM Task",
			doc.name,
			{"owner": user, "modified_by": user, "assigned_to": user},
			update_modified=False,
		)
		created.append(doc.name)
	return created


def _seed_meetings(user: str, today) -> list[str]:
	if not frappe.db.exists("DocType", "Event"):
		return []

	slots = [
		{
			"subject": "Discovery call — Hale Logistics",
			"starts_on": get_datetime(f"{today} 10:30:00"),
			"ends_on": get_datetime(f"{today} 11:00:00"),
			"description": "AI home plate seed — morning discovery.",
		},
		{
			"subject": "Pipeline review with team",
			"starts_on": get_datetime(f"{today} 15:00:00"),
			"ends_on": get_datetime(f"{today} 15:30:00"),
			"description": "AI home plate seed — afternoon sync.",
		},
	]
	created = []
	for slot in slots:
		doc = frappe.get_doc(
			{
				"doctype": "Event",
				"event_type": "Private",
				"event_category": "Meeting",
				"status": "Open",
				"owner": user,
				"event_participants": [
					{
						"reference_doctype": "User",
						"reference_docname": user,
						"email": user,
					}
				],
				**slot,
			}
		)
		doc.flags.ignore_permissions = True
		doc.insert()
		frappe.db.set_value(
			"Event",
			doc.name,
			{"owner": user, "modified_by": user},
			update_modified=False,
		)
		created.append(doc.name)
	return created


def _clear_user_state(user: str) -> None:
	state = _load_state()
	payload = state.get(user) or {}
	for name in payload.get("events") or []:
		if frappe.db.exists("Event", name):
			frappe.delete_doc("Event", name, ignore_permissions=True, force=True)
	for name in payload.get("tasks") or []:
		if frappe.db.exists("CRM Task", name):
			frappe.delete_doc("CRM Task", name, ignore_permissions=True, force=True)
	for name in payload.get("leads") or []:
		if frappe.db.exists("CRM Lead", name):
			frappe.delete_doc("CRM Lead", name, ignore_permissions=True, force=True)


def _load_state() -> dict:
	raw = frappe.db.get_default(STATE_KEY) or "{}"
	try:
		data = json.loads(raw)
		return data if isinstance(data, dict) else {}
	except Exception:
		return {}


def _save_state(state: dict) -> None:
	frappe.db.set_default(STATE_KEY, json.dumps(state))
