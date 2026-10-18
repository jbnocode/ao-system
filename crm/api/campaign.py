# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""CRM Campaign APIs — Campaign definition + CRM Email Campaign enrollments.

Mirrors ERPNext Campaign / Email Campaign flow for Frappe CRM.
"""

from __future__ import annotations

import json

import frappe
from frappe import _
from frappe.utils import today

from crm.fcrm.doctype.crm_email_campaign.crm_email_campaign import (
	process_email_campaigns,
)

ALLOWED_ROLES = ("System Manager", "Sales Manager", "Sales User")
ALLOWED_FOR = ("CRM Lead", "Contact", "CRM Deal", "Email Group")


def _require_role():
	if not any(role in ALLOWED_ROLES for role in frappe.get_roles()):
		frappe.throw(_("Not permitted to manage campaigns"), frappe.PermissionError)


def _parse_list(value) -> list:
	if value is None or value == "":
		return []
	if isinstance(value, list):
		return value
	if isinstance(value, str):
		try:
			parsed = json.loads(value)
			return parsed if isinstance(parsed, list) else [value]
		except json.JSONDecodeError:
			return [v.strip() for v in value.split(",") if v.strip()]
	return [value]


def _schedule_rows(steps) -> list[dict]:
	rows = []
	for step in steps or []:
		rows.append(
			{
				"channel": step.get("channel") or "Email",
				"send_after_days": int(step.get("send_after_days") or 0),
				"email_template": step.get("email_template") or "",
				"sms_body": step.get("sms_body") or "",
			}
		)
	return rows


@frappe.whitelist()
def get_campaign(name: str) -> dict:
	_require_role()
	frappe.has_permission("CRM Campaign", "read", throw=True)
	doc = frappe.get_doc("CRM Campaign", name)
	data = doc.as_dict()
	data["email_campaigns"] = frappe.get_all(
		"CRM Email Campaign",
		filters={"campaign_name": name},
		fields=[
			"name",
			"email_campaign_for",
			"recipient",
			"start_date",
			"end_date",
			"status",
			"sender",
		],
		order_by="modified desc",
	)
	data["lead_count"] = frappe.db.count("CRM Lead", {"campaign": name}) if frappe.db.has_column(
		"CRM Lead", "campaign"
	) else 0
	return data


@frappe.whitelist()
def save_campaign(doc: str | dict | None = None) -> dict:
	_require_role()
	if isinstance(doc, str):
		doc = json.loads(doc)
	if not isinstance(doc, dict):
		frappe.throw(_("Invalid campaign payload"))

	name = doc.get("name")
	schedules = _schedule_rows(doc.get("campaign_schedules") or doc.get("steps"))

	if name and frappe.db.exists("CRM Campaign", name):
		frappe.has_permission("CRM Campaign", "write", throw=True)
		existing = frappe.get_doc("CRM Campaign", name)
		existing.campaign_name = doc.get("campaign_name") or existing.campaign_name
		existing.description = doc.get("description") or ""
		existing.set("campaign_schedules", [])
		for row in schedules:
			existing.append("campaign_schedules", row)
		existing.save()
		return get_campaign(existing.name)

	frappe.has_permission("CRM Campaign", "create", throw=True)
	new_doc = frappe.get_doc(
		{
			"doctype": "CRM Campaign",
			"campaign_name": doc.get("campaign_name"),
			"description": doc.get("description") or "",
			"campaign_schedules": schedules,
		}
	)
	new_doc.insert()
	return get_campaign(new_doc.name)


@frappe.whitelist()
def create_email_campaign(
	campaign: str,
	email_campaign_for: str = "CRM Lead",
	recipient: str | None = None,
	start_date: str | None = None,
	sender: str | None = None,
) -> dict:
	"""Create one CRM Email Campaign enrollment (ERPNext Email Campaign)."""
	_require_role()
	frappe.has_permission("CRM Email Campaign", "create", throw=True)
	if email_campaign_for not in ALLOWED_FOR:
		frappe.throw(_("Unsupported recipient type: {0}").format(email_campaign_for))
	if not recipient:
		frappe.throw(_("Recipient is required"))
	if not frappe.db.exists("CRM Campaign", campaign):
		frappe.throw(_("Campaign {0} not found").format(campaign))

	doc = frappe.get_doc(
		{
			"doctype": "CRM Email Campaign",
			"campaign_name": campaign,
			"email_campaign_for": email_campaign_for,
			"recipient": recipient,
			"start_date": start_date or today(),
			"sender": sender or frappe.session.user,
		}
	)
	doc.insert()

	if email_campaign_for == "CRM Lead" and frappe.db.has_column("CRM Lead", "campaign"):
		frappe.db.set_value("CRM Lead", recipient, "campaign", campaign, update_modified=False)

	return doc.as_dict()


@frappe.whitelist()
def enroll_members(
	campaign: str,
	reference_doctype: str = "CRM Lead",
	names: str | list | None = None,
	start_date: str | None = None,
) -> dict:
	"""Bulk-create CRM Email Campaigns for many recipients."""
	_require_role()
	if reference_doctype not in ALLOWED_FOR:
		frappe.throw(_("Unsupported recipient type: {0}").format(reference_doctype))
	name_list = _parse_list(names)
	if not name_list:
		frappe.throw(_("Select at least one recipient"))

	added = 0
	errors = []
	for name in name_list:
		try:
			create_email_campaign(
				campaign=campaign,
				email_campaign_for=reference_doctype,
				recipient=name,
				start_date=start_date or today(),
			)
			added += 1
		except Exception as exc:
			errors.append(f"{name}: {exc!s}")
	return {"added": added, "errors": errors}


@frappe.whitelist()
def process_now(name: str | None = None) -> dict:
	_require_role()
	if "System Manager" not in frappe.get_roles() and "Sales Manager" not in frappe.get_roles():
		frappe.throw(_("Only managers can run campaigns now"), frappe.PermissionError)
	process_email_campaigns()
	return {"processed": "all", "campaign": name}


@frappe.whitelist()
def search_recipients(
	doctype: str = "CRM Lead",
	txt: str = "",
	limit: int = 20,
) -> list[dict]:
	_require_role()
	if doctype not in ALLOWED_FOR:
		frappe.throw(_("Unsupported recipient type: {0}").format(doctype))
	frappe.has_permission(doctype if doctype != "Email Group" else "Email Group", "read", throw=True)

	limit = min(int(limit or 20), 50)
	txt = (txt or "").strip()

	if doctype == "Email Group":
		filters = {"title": ["like", f"%{txt}%"]} if txt else None
		rows = frappe.get_list(
			"Email Group",
			filters=filters,
			fields=["name", "title"],
			limit_page_length=limit,
			order_by="modified desc",
		)
		return [{**r, "title": r.get("title") or r.get("name")} for r in rows]

	if doctype == "CRM Lead":
		or_filters = None
		if txt:
			or_filters = [
				["lead_name", "like", f"%{txt}%"],
				["email", "like", f"%{txt}%"],
				["mobile_no", "like", f"%{txt}%"],
			]
		return frappe.get_list(
			"CRM Lead",
			or_filters=or_filters,
			fields=["name", "lead_name as title", "email", "mobile_no as phone"],
			limit_page_length=limit,
			order_by="modified desc",
		)

	if doctype == "Contact":
		or_filters = None
		if txt:
			or_filters = [
				["full_name", "like", f"%{txt}%"],
				["email_id", "like", f"%{txt}%"],
				["mobile_no", "like", f"%{txt}%"],
			]
		return frappe.get_list(
			"Contact",
			or_filters=or_filters,
			fields=["name", "full_name as title", "email_id as email", "mobile_no as phone"],
			limit_page_length=limit,
			order_by="modified desc",
		)

	or_filters = None
	if txt:
		or_filters = [
			["organization", "like", f"%{txt}%"],
			["name", "like", f"%{txt}%"],
			["email", "like", f"%{txt}%"],
		]
	return frappe.get_list(
		"CRM Deal",
		or_filters=or_filters,
		fields=["name", "organization as title", "email", "mobile_no as phone"],
		limit_page_length=limit,
		order_by="modified desc",
	)


@frappe.whitelist()
def get_leads_for_campaign(campaign: str) -> list[dict]:
	"""View Leads tagged to this campaign (ERPNext Campaign → View Leads)."""
	_require_role()
	if not frappe.db.has_column("CRM Lead", "campaign"):
		return []
	frappe.has_permission("CRM Lead", "read", throw=True)
	return frappe.get_list(
		"CRM Lead",
		filters={"campaign": campaign},
		fields=["name", "lead_name", "email", "status", "mobile_no"],
		order_by="modified desc",
		limit_page_length=100,
	)
