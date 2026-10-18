# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""AI home briefing: greeting, suggestion chips, tasks, meetings."""

from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import formatdate, get_datetime, getdate, now_datetime

from crm.ai.credits import get_settings


@frappe.whitelist()
def get_home_briefing() -> dict:
	"""Snapshot for /crm/ai home: chips + tasks + today's meetings."""
	user = frappe.session.user
	if user == "Guest":
		frappe.throw(_("Login required"), frappe.PermissionError)

	first_name = _first_name(user)
	greeting = _greeting(first_name)
	tasks = _open_tasks(user)
	overdue = [t for t in tasks if t.get("overdue")]
	meetings = _meetings_today(user)
	cold_leads = _cold_lead_count(user)
	settings = get_settings()

	suggestions = _suggestions(
		overdue_count=len(overdue),
		cold_leads=cold_leads,
		next_meeting=meetings[0] if meetings else None,
		open_tasks=len(tasks),
	)

	return {
		"greeting": greeting,
		"first_name": first_name,
		"model": settings.model or "gpt-4o-mini",
		"ai_enabled": bool(settings.enabled),
		"suggestions": suggestions,
		"tasks": tasks[:8],
		"meetings": meetings[:8],
		"stats": {
			"overdue_tasks": len(overdue),
			"open_tasks": len(tasks),
			"cold_leads": cold_leads,
			"meetings_today": len(meetings),
		},
		"today_label": formatdate(getdate(), "MMM d"),
	}


def _first_name(user: str) -> str:
	full = frappe.db.get_value("User", user, "first_name") or frappe.db.get_value(
		"User", user, "full_name"
	)
	if not full:
		return user.split("@")[0].title()
	return str(full).strip().split()[0]


def _greeting(first_name: str) -> str:
	hour = now_datetime().hour
	if hour < 12:
		period = _("Good morning")
	elif hour < 17:
		period = _("Good afternoon")
	else:
		period = _("Good evening")
	return f"{period}, {first_name}."


def _open_tasks(user: str) -> list[dict]:
	if not frappe.has_permission("CRM Task", "read"):
		return []

	rows = frappe.get_all(
		"CRM Task",
		filters={
			"assigned_to": user,
			"status": ["not in", ["Done", "Canceled"]],
		},
		fields=["name", "title", "priority", "status", "due_date", "reference_doctype", "reference_docname"],
		order_by="due_date asc, modified desc",
		limit=20,
	)
	now = now_datetime()
	out = []
	for r in rows:
		due = get_datetime(r.due_date) if r.due_date else None
		overdue = bool(due and due < now)
		out.append(
			{
				"name": r.name,
				"title": r.title,
				"priority": r.priority or "Medium",
				"status": r.status,
				"due_date": r.due_date,
				"due_label": _due_label(due, now),
				"overdue": overdue,
				"reference_doctype": r.reference_doctype,
				"reference_docname": r.reference_docname,
			}
		)
	# Overdue / high priority first
	out.sort(key=lambda t: (0 if t["overdue"] else 1, _priority_rank(t["priority"]), t.get("due_date") or "9999"))
	return out


def _priority_rank(priority: str) -> int:
	return {"High": 0, "Medium": 1, "Low": 2}.get(priority or "Medium", 1)


def _due_label(due, now) -> str:
	if not due:
		return _("No due date")
	delta = due.date() - now.date()
	days = delta.days
	if days < 0:
		n = abs(days)
		return _("{0}d overdue").format(n)
	if days == 0:
		return _("Due today")
	if days == 1:
		return _("Due tomorrow")
	return _("Due {0}").format(formatdate(due, "MMM d"))


def _cold_lead_count(user: str) -> int:
	if not frappe.has_permission("CRM Lead", "read"):
		return 0
	try:
		return int(
			frappe.db.count(
				"CRM Lead",
				filters={
					"lead_owner": user,
					"lead_temperature": "Cold",
					"converted": 0,
				},
			)
		)
	except Exception:
		# converted / temperature may differ by site
		return int(
			frappe.db.count(
				"CRM Lead",
				filters={"lead_owner": user, "lead_temperature": "Cold"},
			)
		)


def _meetings_today(user: str) -> list[dict]:
	"""Best-effort: Frappe Event participants for today."""
	if not frappe.db.exists("DocType", "Event"):
		return []
	if not frappe.has_permission("Event", "read"):
		return []

	today = getdate()
	start = f"{today} 00:00:00"
	end = f"{today} 23:59:59"

	# Events where user is owner or listed as participant
	owned = frappe.get_all(
		"Event",
		filters={
			"starts_on": ["between", [start, end]],
			"owner": user,
			"status": ["!=", "Cancelled"],
		},
		fields=["name", "subject", "starts_on", "ends_on", "status", "event_type"],
		order_by="starts_on asc",
		limit=10,
	)

	participating = []
	try:
		participant_names = frappe.get_all(
			"Event Participants",
			filters={"reference_doctype": "User", "reference_docname": user},
			pluck="parent",
		)
		# Fallback: some sites store the user email on the participant row
		if not participant_names:
			participant_names = frappe.get_all(
				"Event Participants",
				filters={"email": user},
				pluck="parent",
			)
		if participant_names:
			participating = frappe.get_all(
				"Event",
				filters={
					"name": ["in", participant_names],
					"starts_on": ["between", [start, end]],
					"status": ["!=", "Cancelled"],
				},
				fields=["name", "subject", "starts_on", "ends_on", "status", "event_type"],
				order_by="starts_on asc",
				limit=10,
			)
	except Exception:
		participating = []

	seen = set()
	out = []
	for r in list(owned) + list(participating):
		if r.name in seen:
			continue
		seen.add(r.name)
		out.append(
			{
				"name": r.name,
				"subject": r.subject or _("Untitled meeting"),
				"starts_on": r.starts_on,
				"ends_on": r.ends_on,
				"status": r.status,
				"event_type": r.event_type,
			}
		)
	out.sort(key=lambda m: m.get("starts_on") or "")
	return out


def _suggestions(
	overdue_count: int,
	cold_leads: int,
	next_meeting: dict | None,
	open_tasks: int,
) -> list[dict]:
	chips = []
	if overdue_count:
		chips.append(
			{
				"id": "overdue_tasks",
				"label": _("{0} overdue tasks").format(overdue_count),
				"icon": "alert",
				"prompt": _(
					"I have {0} overdue tasks. Help me prioritize them and suggest what to do next."
				).format(overdue_count),
			}
		)
	elif open_tasks:
		chips.append(
			{
				"id": "open_tasks",
				"label": _("{0} open tasks").format(open_tasks),
				"icon": "list",
				"prompt": _("Review my open tasks and suggest a plan for today."),
			}
		)

	if cold_leads:
		chips.append(
			{
				"id": "cold_leads",
				"label": _("Follow up with {0} cold leads").format(cold_leads),
				"icon": "users",
				"prompt": _(
					"I have {0} cold leads. Suggest a practical follow-up plan for the top ones."
				).format(cold_leads),
			}
		)
	else:
		chips.append(
			{
				"id": "pipeline",
				"label": _("Review my pipeline"),
				"icon": "users",
				"prompt": _("Summarize what I should focus on in my leads and deals today."),
			}
		)

	if next_meeting:
		chips.append(
			{
				"id": "prep_meeting",
				"label": _("Prep for next meeting"),
				"icon": "sparkles",
				"prompt": _(
					"Help me prep for my next meeting: {0}. What should I review beforehand?"
				).format(next_meeting.get("subject") or _("upcoming meeting")),
			}
		)
	else:
		chips.append(
			{
				"id": "prep_day",
				"label": _("Plan my day"),
				"icon": "sparkles",
				"prompt": _("Help me plan my CRM day — tasks, follow-ups, and priorities."),
			}
		)

	# Prefer a quote demo chip when insurance doctypes exist
	if frappe.db.exists("DocType", "Insurance Quote"):
		chips.insert(
			0,
			{
				"id": "generate_quotes",
				"label": _("Generate term quotes"),
				"icon": "sparkles",
				"prompt": _(
					"Generate quotes for a 56-year-old male, $500,000 term, 20 years, non-tobacco, Indiana"
				),
			},
		)

	return chips[:3]
