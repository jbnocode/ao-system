# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import annotations

import frappe
from frappe import _

from crm.life import assistant, journey
from crm.life.fields import ensure_case_fields
from crm.life.flows import FLOW_TITLES, install as install_flows, uninstall as uninstall_flows
from crm.life.layouts import apply_life_layouts
from crm.life.pipeline import LIFE_STATUS_NAMES, apply_life_pipeline, list_life_statuses


@frappe.whitelist()
def get_life_pack_status() -> dict:
	"""Whether life statuses and flows are present."""
	frappe.only_for(("System Manager", "Sales Manager"))
	existing_statuses = set(frappe.get_all("CRM Deal Status", pluck="name"))
	missing = [s for s in LIFE_STATUS_NAMES if s not in existing_statuses]
	flow_rows = []
	if frappe.db.exists("DocType", "Automation Flow"):
		for title in FLOW_TITLES:
			name = frappe.db.get_value("Automation Flow", {"title": title}, ["name", "enabled"], as_dict=True)
			flow_rows.append(
				{
					"title": title,
					"name": name.name if name else None,
					"enabled": bool(name.enabled) if name else False,
					"installed": bool(name),
				}
			)
	return {
		"statuses": list_life_statuses(),
		"missing_statuses": missing,
		"pipeline_applied": not missing,
		"flows": flow_rows,
		"life_agency_mode": bool(frappe.db.get_single_value("FCRM Settings", "life_agency_mode")),
	}


@frappe.whitelist()
def apply_life_pack(
	replace_pipeline: int | str = 1,
	enable_flows: int | str = 0,
	enable_life_mode: int | str = 1,
) -> dict:
	"""Apply life pipeline, case fields, layouts (+ optional flow enable)."""
	frappe.only_for(("System Manager", "Sales Manager"))
	ensure_case_fields()
	pipeline = apply_life_pipeline(replace=bool(frappe.utils.cint(replace_pipeline)))
	install_flows(enable=frappe.utils.cint(enable_flows))
	life_on = bool(frappe.utils.cint(enable_life_mode))
	if life_on:
		frappe.db.set_single_value("FCRM Settings", "life_agency_mode", 1)
		apply_life_layouts()
	return {
		"pipeline": pipeline,
		"flows_enabled": bool(frappe.utils.cint(enable_flows)),
		"life_agency_mode": life_on,
	}


@frappe.whitelist()
def set_life_agency_mode(enabled: int | str = 1) -> dict:
	"""Toggle person-first Cases UX. Managers only."""
	frappe.only_for(("System Manager", "Sales Manager"))
	on = bool(frappe.utils.cint(enabled))
	frappe.db.set_single_value("FCRM Settings", "life_agency_mode", 1 if on else 0)
	if on:
		ensure_case_fields()
		apply_life_layouts()
	return {"life_agency_mode": on}


@frappe.whitelist()
def remove_life_flows() -> dict:
	frappe.only_for(("System Manager", "Sales Manager"))
	uninstall_flows()
	return {"ok": True}


@frappe.whitelist()
def get_journey(deal: str) -> dict:
	return journey.get_journey_snapshot(deal)


@frappe.whitelist()
def convert_quote_to_application(quote: str, update_deal_status: int | str = 1) -> dict:
	return journey.convert_quote_to_application(
		quote, update_deal_status=bool(frappe.utils.cint(update_deal_status))
	)


@frappe.whitelist()
def convert_application_to_policy(application: str, update_deal_status: int | str = 1) -> dict:
	return journey.convert_application_to_policy(
		application, update_deal_status=bool(frappe.utils.cint(update_deal_status))
	)


@frappe.whitelist()
def set_deal_status(deal: str, status: str) -> dict:
	applied = journey.apply_suggested_deal_status(deal, status)
	if not applied:
		frappe.throw(_("Could not set deal status to {0}").format(status))
	return {"status": applied}


@frappe.whitelist()
def set_contact_relationship(deal: str, contact: str, relationship: str) -> dict:
	"""Set household relationship on a CRM Contacts child row."""
	frappe.has_permission("CRM Deal", "write", throw=True)
	if not frappe.get_meta("CRM Contacts").has_field("relationship"):
		frappe.throw(_("Relationship field is not installed. Apply the life pack first."))
	doc = frappe.get_doc("CRM Deal", deal)
	updated = False
	for row in doc.contacts or []:
		if row.contact == contact:
			row.relationship = relationship or ""
			if relationship == "Self":
				row.is_primary = 1
			updated = True
			break
	if not updated:
		frappe.throw(_("Contact not on this case"))
	doc.save()
	return {"ok": True, "relationship": relationship}


@frappe.whitelist()
def assistant_overview(deal: str) -> dict:
	return assistant.build_overview(deal)


@frappe.whitelist()
def assistant_draft(deal: str, note: str | None = None) -> dict:
	return assistant.draft_follow_up(deal, note=note or "")


@frappe.whitelist()
def assistant_apply(deal: str, suggestion: str | dict) -> dict:
	if isinstance(suggestion, str):
		suggestion = frappe.parse_json(suggestion)
	return assistant.apply_suggestion(deal, suggestion)
