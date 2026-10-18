# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""Deal-scoped life assistant: summarize, draft follow-up, suggest next steps.

Rule-based so demos work without an LLM. Optional LLM hook later via frappe.conf.
"""

from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import format_datetime

from crm.life.journey import get_journey_snapshot
from crm.life.pipeline import LIFE_STATUS_NAMES


def build_overview(deal: str) -> dict:
	frappe.has_permission("CRM Deal", "read", throw=True)
	doc = frappe.get_doc("CRM Deal", deal)
	journey = get_journey_snapshot(deal)
	contacts = _deal_contacts(deal)
	tasks = _open_tasks(deal)
	recent = _recent_activity(deal)

	case_label = getattr(doc, "case_title", None) or doc.organization or doc.name
	summary_lines = [
		f"Case **{case_label}** ({doc.name}) is in **{doc.status or 'no status'}**.",
	]
	if contacts:
		primary = next((c for c in contacts if c.get("is_primary")), contacts[0])
		rel = primary.get("relationship") or "Self"
		summary_lines.append(
			f"Primary insured: {primary.get('full_name') or primary.get('name')}"
			+ (f" ({rel})" if rel else "")
			+ (f" — {primary.get('email')}" if primary.get("email") else "")
			+ "."
		)
	else:
		summary_lines.append("No household contacts linked yet — add a primary insured.")

	qc, ac, pc = (
		journey["counts"]["quotes"],
		journey["counts"]["applications"],
		journey["counts"]["policies"],
	)
	summary_lines.append(f"Journey: {qc} quote(s), {ac} application(s), {pc} policy(ies).")

	if journey.get("next_action"):
		summary_lines.append(f"Suggested next: {journey['next_action']['label']}.")

	if tasks:
		summary_lines.append(f"{len(tasks)} open task(s), next due: {tasks[0].get('due_date') or 'unscheduled'}.")

	draft = draft_follow_up(deal, note="")
	suggestions = suggest_next(deal, journey=journey, tasks=tasks)

	return {
		"summary": "\n".join(summary_lines),
		"draft": draft,
		"suggestions": suggestions,
		"context": {
			"status": doc.status,
			"organization": doc.organization,
			"contacts": contacts,
			"journey": journey,
			"open_tasks": tasks,
			"recent_activity": recent,
			"pipeline": LIFE_STATUS_NAMES,
		},
	}


def draft_follow_up(deal: str, note: str = "") -> dict:
	"""Stage-aware email/SMS draft. Human must send."""
	frappe.has_permission("CRM Deal", "read", throw=True)
	doc = frappe.get_doc("CRM Deal", deal)
	contacts = _deal_contacts(deal)
	primary = next((c for c in contacts if c.get("is_primary")), contacts[0] if contacts else {})
	first = (primary.get("first_name") or primary.get("full_name") or "there").split()[0]
	status = doc.status or "Contacted"
	org = doc.organization or "your family"

	templates = {
		"Contacted": (
			f"Quick hello, {first}",
			f"Hi {first},\n\nThanks for connecting. I'd like to learn a bit about {org}'s "
			f"protection goals and put together a few life options.\n\n"
			f"When is a good time for a short call this week?\n\nBest regards",
			f"Hi {first}, thanks for connecting — when works for a quick call about life coverage?",
		),
		"Needs Analysis": (
			f"Following up on our conversation, {first}",
			f"Hi {first},\n\nBased on what we discussed for {org}, I'm preparing a needs summary "
			f"and a few carrier options.\n\n"
			f"Reply with any health or budget updates and I'll lock the quote set.\n\nBest regards",
			f"Hi {first}, gathering a few more details so I can finalize your life quote options.",
		),
		"Quoted": (
			f"Your life quote options, {first}",
			f"Hi {first},\n\nI've put quotes on your file for {org}. Happy to walk through "
			f"premiums, term length, and underwriting class whenever you're ready.\n\n"
			f"Want to book 15 minutes to decide next steps?\n\nBest regards",
			f"Hi {first}, your life quotes are ready — want a quick walkthrough?",
		),
		"Application Submitted": (
			f"Next step: medical exam, {first}",
			f"Hi {first},\n\nYour application is in. The next step is usually the medical exam / "
			f"labs. I'll send scheduling options shortly.\n\n"
			f"Please keep an eye out for the exam vendor text/email.\n\nBest regards",
			f"Hi {first}, application is submitted — I'll help schedule the exam next.",
		),
		"Exam Scheduled": (
			f"Exam reminder, {first}",
			f"Hi {first},\n\nJust confirming your exam appointment is on the calendar. "
			f"Bring a photo ID and list of current medications.\n\n"
			f"Text me if you need to reschedule.\n\nBest regards",
			f"Hi {first}, reminder about your upcoming exam — reply if you need to reschedule.",
		),
		"Underwriting": (
			f"Underwriting update, {first}",
			f"Hi {first},\n\nYour case is with underwriting. I'll update you as soon as we hear "
			f"back from the carrier — sometimes they ask for an APS or a quick clarification.\n\n"
			f"No action needed from you unless I ping you.\n\nBest regards",
			f"Hi {first}, still in underwriting — I'll text when we have a carrier update.",
		),
		"Approved": (
			f"Great news — approved, {first}",
			f"Hi {first},\n\nYou're approved. Next we deliver the policy and confirm beneficiaries "
			f"and payment. I'll send the delivery packet shortly.\n\nBest regards",
			f"Hi {first}, great news — approved! I'll send delivery next steps.",
		),
		"Policy Delivered": (
			f"Welcome, {first} — policy is in force",
			f"Hi {first},\n\nYour policy is delivered. Keep this confirmation with your records. "
			f"I'm here for beneficiary changes, reviews, and family cross-sell whenever you need.\n\n"
			f"Congratulations,\n",
			f"Hi {first}, your policy is delivered — congrats! Reach out anytime for reviews.",
		),
	}

	subject, email_body, sms = templates.get(status, templates["Contacted"])
	if note:
		email_body = email_body.rstrip() + f"\n\n---\nNote: {note}\n"

	return {
		"channel": "email",
		"to": primary.get("email") or doc.get("email") or "",
		"subject": subject,
		"body": email_body,
		"sms": sms,
		"status": status,
	}


def suggest_next(deal: str, journey: dict | None = None, tasks: list | None = None) -> list[dict]:
	frappe.has_permission("CRM Deal", "read", throw=True)
	doc = frappe.get_doc("CRM Deal", deal)
	journey = journey or get_journey_snapshot(deal)
	tasks = tasks if tasks is not None else _open_tasks(deal)
	suggestions: list[dict] = []

	na = journey.get("next_action") or {}
	if na.get("set_status"):
		suggestions.append(
			{
				"type": "set_status",
				"label": na["label"],
				"value": na["set_status"],
			}
		)
	if na.get("quote"):
		suggestions.append(
			{
				"type": "convert_quote",
				"label": na["label"],
				"quote": na["quote"],
			}
		)
	if na.get("application"):
		suggestions.append(
			{
				"type": "convert_application",
				"label": na["label"],
				"application": na["application"],
			}
		)
	if na.get("tab") and not (na.get("quote") or na.get("application") or na.get("set_status")):
		suggestions.append({"type": "open_tab", "label": na["label"], "tab": na["tab"]})

	# Advance one stage along the life path when no stronger journey action
	if not suggestions and doc.status in LIFE_STATUS_NAMES:
		idx = LIFE_STATUS_NAMES.index(doc.status)
		if idx + 1 < len(LIFE_STATUS_NAMES) and LIFE_STATUS_NAMES[idx + 1] not in ("Lost", "Declined"):
			nxt = LIFE_STATUS_NAMES[idx + 1]
			suggestions.append(
				{
					"type": "set_status",
					"label": f"Advance to {nxt}",
					"value": nxt,
				}
			)

	if not tasks:
		suggestions.append(
			{
				"type": "create_task",
				"label": "Create follow-up task (3 days)",
				"title": f"Follow up — {doc.organization or doc.name}",
				"days": 3,
			}
		)

	suggestions.append({"type": "draft", "label": "Use stage follow-up draft"})
	return suggestions


def apply_suggestion(deal: str, suggestion: dict) -> dict:
	"""Execute a confirmed suggestion. Returns result payload."""
	frappe.has_permission("CRM Deal", "write", throw=True)
	stype = suggestion.get("type")

	if stype == "set_status":
		status = suggestion.get("value")
		if not status or not frappe.db.exists("CRM Deal Status", status):
			frappe.throw(_("Invalid status"))
		frappe.db.set_value("CRM Deal", deal, "status", status)
		return {"ok": True, "status": status}

	if stype == "convert_quote":
		from crm.life.journey import convert_quote_to_application

		return convert_quote_to_application(suggestion["quote"])

	if stype == "convert_application":
		from crm.life.journey import convert_application_to_policy

		return convert_application_to_policy(suggestion["application"])

	if stype == "create_task":
		from frappe.utils import add_days, nowdate

		days = int(suggestion.get("days") or 3)
		task = frappe.get_doc(
			{
				"doctype": "CRM Task",
				"title": suggestion.get("title") or f"Follow up — {deal}",
				"status": "Todo",
				"priority": "Medium",
				"assigned_to": frappe.db.get_value("CRM Deal", deal, "deal_owner") or frappe.session.user,
				"reference_doctype": "CRM Deal",
				"reference_docname": deal,
				"due_date": add_days(nowdate(), days),
			}
		)
		task.insert()
		return {"ok": True, "task": task.name}

	if stype == "draft":
		return {"ok": True, "draft": draft_follow_up(deal)}

	frappe.throw(_("Unknown suggestion type: {0}").format(stype))


def _deal_contacts(deal: str) -> list[dict]:
	try:
		from crm.fcrm.doctype.crm_deal.api import get_deal_contacts

		return get_deal_contacts(deal) or []
	except Exception:
		return []


def _open_tasks(deal: str) -> list[dict]:
	return frappe.get_all(
		"CRM Task",
		filters={
			"reference_doctype": "CRM Deal",
			"reference_docname": deal,
			"status": ("not in", ["Done", "Canceled"]),
		},
		fields=["name", "title", "status", "due_date", "priority"],
		order_by="due_date asc",
		limit_page_length=10,
	)


def _recent_activity(deal: str) -> list[dict]:
	if not frappe.db.exists("DocType", "CRM Status Change Log"):
		return []
	try:
		rows = frappe.db.sql(
			"""
			select `from`, `to`, creation
			from `tabCRM Status Change Log`
			where parenttype = %s and parent = %s
			order by creation desc
			limit 5
			""",
			("CRM Deal", deal),
			as_dict=True,
		)
	except Exception:
		return []
	return [
		{
			"type": "status",
			"from": r.get("from"),
			"to": r.get("to"),
			"when": format_datetime(r.creation) if r.creation else "",
		}
		for r in rows
	]
