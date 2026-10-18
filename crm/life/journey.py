# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""Quote → Application → Policy journey helpers and suggested deal stages."""

from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import today

# Insurance record status → suggested CRM Deal status
QUOTE_STATUS_TO_DEAL = {
	"Presented": "Quoted",
	"Accepted": "Application Submitted",
}
APPLICATION_STATUS_TO_DEAL = {
	"Submitted": "Application Submitted",
	"Underwriting": "Underwriting",
	"Approved": "Approved",
	"Issued": "Policy Delivered",
	"Declined": "Declined",
}
POLICY_STATUS_TO_DEAL = {
	"Pending": "Approved",
	"In Force": "Policy Delivered",
	"Lapsed": "Lost",
	"Cancelled": "Lost",
}


def convert_quote_to_application(quote: str, *, update_deal_status: bool = True) -> dict:
	"""Create an Insurance Application from an accepted (or any) quote."""
	src = frappe.get_doc("Insurance Quote", quote)
	frappe.has_permission("Insurance Quote", "read", doc=src, throw=True)
	frappe.has_permission("Insurance Application", "create", throw=True)

	app = frappe.get_doc(
		{
			"doctype": "Insurance Application",
			"deal": src.deal,
			"source_quote": src.name,
			"carrier": src.carrier,
			"product": src.product,
			"face_amount": src.face_amount,
			"monthly_premium": src.monthly_premium,
			"status": "Draft",
			"submitted_on": today(),
			"underwriting_class": "",
		}
	)
	app.insert()

	if src.status != "Accepted":
		src.db_set("status", "Accepted", update_modified=True)

	suggested = None
	if update_deal_status and src.deal:
		suggested = _maybe_set_deal_status(src.deal, "Application Submitted")

	return {"application": app.name, "deal_status": suggested}


def convert_application_to_policy(application: str, *, update_deal_status: bool = True) -> dict:
	"""Create an Insurance Policy from an approved/issued application."""
	src = frappe.get_doc("Insurance Application", application)
	frappe.has_permission("Insurance Application", "read", doc=src, throw=True)
	frappe.has_permission("Insurance Policy", "create", throw=True)

	policy = frappe.get_doc(
		{
			"doctype": "Insurance Policy",
			"deal": src.deal,
			"source_application": src.name,
			"carrier": src.carrier,
			"product": src.product,
			"face_amount": src.face_amount,
			"monthly_premium": src.monthly_premium,
			"status": "Pending",
			"effective_date": today(),
			"policy_number": "",
		}
	)
	policy.insert()

	if src.status not in ("Approved", "Issued"):
		src.db_set("status", "Approved", update_modified=True)

	suggested = None
	if update_deal_status and src.deal:
		suggested = _maybe_set_deal_status(src.deal, "Approved")

	return {"policy": policy.name, "deal_status": suggested}


def suggest_deal_status_for_record(doctype: str, status: str) -> str | None:
	mapping = {
		"Insurance Quote": QUOTE_STATUS_TO_DEAL,
		"Insurance Application": APPLICATION_STATUS_TO_DEAL,
		"Insurance Policy": POLICY_STATUS_TO_DEAL,
	}.get(doctype, {})
	return mapping.get(status)


def apply_suggested_deal_status(deal: str, status: str) -> str | None:
	frappe.has_permission("CRM Deal", "write", throw=True)
	return _maybe_set_deal_status(deal, status)


def get_journey_snapshot(deal: str) -> dict:
	"""Counts and latest records for the deal journey strip."""
	frappe.has_permission("CRM Deal", "read", throw=True)
	if not frappe.db.exists("CRM Deal", deal):
		frappe.throw(_("Deal {0} not found").format(deal), frappe.DoesNotExistError)

	quotes = _list_insurance("Insurance Quote", deal)
	apps = _list_insurance("Insurance Application", deal)
	policies = _list_insurance("Insurance Policy", deal)
	deal_status = frappe.db.get_value("CRM Deal", deal, "status")

	next_action = _next_action(deal_status, quotes, apps, policies)

	return {
		"deal": deal,
		"deal_status": deal_status,
		"quotes": quotes,
		"applications": apps,
		"policies": policies,
		"counts": {
			"quotes": len(quotes),
			"applications": len(apps),
			"policies": len(policies),
		},
		"next_action": next_action,
	}


def _list_insurance(doctype: str, deal: str) -> list[dict]:
	if not frappe.db.exists("DocType", doctype):
		return []
	return frappe.get_all(
		doctype,
		filters={"deal": deal},
		fields=[
			"name",
			"carrier",
			"product",
			"status",
			"face_amount",
			"monthly_premium",
			"modified",
		],
		order_by="modified desc",
		limit_page_length=20,
	)


def _next_action(deal_status, quotes, apps, policies) -> dict | None:
	if not quotes:
		return {"label": "Add a quote", "tab": "Quotes"}
	accepted = [q for q in quotes if q.status == "Accepted"]
	if accepted and not apps:
		return {
			"label": "Create application from quote",
			"tab": "Quotes",
			"quote": accepted[0].name,
		}
	if apps and not any(a.status in ("Approved", "Issued") for a in apps) and deal_status == "Quoted":
		return {"label": "Move deal to Application Submitted", "set_status": "Application Submitted"}
	approved_apps = [a for a in apps if a.status in ("Approved", "Issued")]
	if approved_apps and not policies:
		return {
			"label": "Create policy from application",
			"tab": "Applications",
			"application": approved_apps[0].name,
		}
	if policies and deal_status not in ("Policy Delivered", "Lost", "Declined"):
		in_force = any(p.status == "In Force" for p in policies)
		if in_force:
			return {"label": "Mark deal Policy Delivered", "set_status": "Policy Delivered"}
	return None


def _maybe_set_deal_status(deal: str, status: str) -> str | None:
	if not frappe.db.exists("CRM Deal Status", status):
		return None
	current = frappe.db.get_value("CRM Deal", deal, "status")
	if current == status:
		return status
	# Don't overwrite Won/Lost unless moving to Declined/Lost explicitly
	current_type = frappe.db.get_value("CRM Deal Status", current, "type") if current else None
	if current_type in ("Won", "Lost") and status not in ("Lost", "Declined", "Policy Delivered"):
		return None
	frappe.db.set_value("CRM Deal", deal, "status", status)
	return status


def sync_deal_status_from_record(doctype: str, name: str) -> str | None:
	"""Optional helper: when an insurance record status changes, suggest deal stage."""
	doc = frappe.get_doc(doctype, name)
	if not doc.deal:
		return None
	suggested = suggest_deal_status_for_record(doctype, doc.status)
	if not suggested:
		return None
	return _maybe_set_deal_status(doc.deal, suggested)
