# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""Stage-tied Automation Flows for the life pipeline.

	bench --site <site> execute crm.life.flows.install
	bench --site <site> execute crm.life.flows.install --kwargs "{'enable': 1}"
	bench --site <site> execute crm.life.flows.uninstall
"""

from __future__ import annotations

import frappe

FLOW_TITLES = [
	"Life: Quote follow-up",
	"Life: Schedule exam after application",
	"Life: Exam reminder",
	"Life: Underwriting check-in",
	"Life: Policy delivery welcome",
]


def install(enable: int = 0):
	"""Create or replace life automation recipes. Disabled by default."""
	from crm.life.pipeline import ensure_life_statuses

	ensure_life_statuses()
	if not frappe.db.exists("DocType", "Automation Flow"):
		print("skipped flows: Automation Flow DocType not installed")
		return
	for build in builders():
		payload = build()
		payload["enabled"] = frappe.utils.cint(enable)
		print("installed:", replace_flow(payload))


def uninstall():
	if not frappe.db.exists("DocType", "Automation Flow"):
		return
	for title in FLOW_TITLES:
		name = frappe.db.get_value("Automation Flow", {"title": title}, "name")
		if not name:
			continue
		frappe.delete_doc("Automation Flow", name, force=True, ignore_permissions=True)
		print("removed:", title)


def builders() -> tuple:
	return (
		quoted_follow_up,
		application_exam_task,
		exam_reminder,
		underwriting_check_in,
		policy_delivered_welcome,
	)


def replace_flow(payload: dict) -> str:
	existing = frappe.db.get_value("Automation Flow", {"title": payload["title"]}, "name")
	if existing:
		frappe.delete_doc("Automation Flow", existing, force=True, ignore_permissions=True)
	return frappe.get_doc(payload).insert(ignore_permissions=True).title


def quoted_follow_up() -> dict:
	return {
		**flow("Life: Quote follow-up", "CRM Deal", "Field Value Changed"),
		"trigger_field": "status",
		"to_value": "Quoted",
		"actions": [
			deal_task(
				1,
				"quote_follow_up",
				"Follow up on quote — {{ doc.organization or doc.name }}",
				days=3,
				priority="High",
			),
		],
	}


def application_exam_task() -> dict:
	return {
		**flow("Life: Schedule exam after application", "CRM Deal", "Field Value Changed"),
		"trigger_field": "status",
		"to_value": "Application Submitted",
		"actions": [
			deal_task(
				1,
				"schedule_exam",
				"Schedule medical exam — {{ doc.organization or doc.name }}",
				days=2,
				priority="High",
			),
		],
	}


def exam_reminder() -> dict:
	return {
		**flow("Life: Exam reminder", "CRM Deal", "Field Value Changed"),
		"trigger_field": "status",
		"to_value": "Exam Scheduled",
		"actions": [
			deal_task(
				1,
				"confirm_exam",
				"Confirm exam appointment — {{ doc.organization or doc.name }}",
				days=1,
				priority="High",
			),
		],
	}


def underwriting_check_in() -> dict:
	return {
		**flow("Life: Underwriting check-in", "CRM Deal", "Field Value Changed"),
		"trigger_field": "status",
		"to_value": "Underwriting",
		"actions": [
			deal_task(
				1,
				"uw_start",
				"Track underwriting — {{ doc.organization or doc.name }}",
				days=1,
				priority="Medium",
			),
			step(2, "wait_week", "Wait", params={"value": 7, "unit": "Days"}),
			still_underwriting(3, "still_uw"),
			deal_task(
				4,
				"uw_stale",
				"Underwriting still open after 7 days — {{ doc.organization or doc.name }}",
				days=0,
				priority="High",
				parent=3,
				branch="If",
			),
		],
	}


def policy_delivered_welcome() -> dict:
	return {
		**flow("Life: Policy delivery welcome", "CRM Deal", "Field Value Changed"),
		"trigger_field": "status",
		"to_value": "Policy Delivered",
		"actions": [
			deal_task(
				1,
				"welcome_call",
				"Welcome / policy review call — {{ doc.organization or doc.name }}",
				days=7,
				priority="Medium",
			),
			step(2, "wait_month", "Wait", params={"value": 30, "unit": "Days"}),
			deal_task(
				3,
				"service_check",
				"30-day service check-in — {{ doc.organization or doc.name }}",
				days=0,
				priority="Medium",
			),
		],
	}


def flow(title: str, document_type: str, trigger_type: str) -> dict:
	return {
		"doctype": "Automation Flow",
		"title": title,
		"document_type": document_type,
		"trigger_type": trigger_type,
		"enabled": 0,
		"run_as": "Automation User",
		"automation_user": "Administrator",
		"stop_on_error": 1,
	}


def step(idx, key, step_type, params=None, condition=None, parent=0, branch="", **extra) -> dict:
	return {
		"doctype": "Automation Action",
		"idx": idx,
		"step_key": key,
		"step_type": step_type,
		"target": "trigger",
		"params": frappe.as_json(params or {}),
		"step_condition": condition,
		"parent_step": parent,
		"branch": branch,
		**extra,
	}


def action(idx, key, action_type, params, **extra) -> dict:
	row = step(idx, key, "Action", params=params, **extra)
	row.update({"action_type": action_type, "target": "trigger"})
	return row


def deal_task(idx, key, title, days, priority="Medium", **extra) -> dict:
	values = {
		"title": title,
		"status": "Todo",
		"priority": priority,
		"assigned_to": "{{ doc.deal_owner or '' }}",
		"reference_doctype": "CRM Deal",
		"reference_docname": "{{ doc.name }}",
		"due_date": f"{{{{ frappe.utils.add_days(frappe.utils.nowdate(), {days}) }}}}",
	}
	return action(idx, key, "CreateDocument", {"doctype": "CRM Task", "values": values}, **extra)


def still_underwriting(idx, key) -> dict:
	row = step(idx, key, "If", condition='doc.status == "Underwriting"')
	return row
