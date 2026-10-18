# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""Person-first side panel + quick entry when life agency mode is on."""

from __future__ import annotations

import frappe

LIFE_SIDE_PANEL = [
	{
		"label": "Household",
		"name": "contacts_section",
		"opened": True,
		"editable": False,
		"contacts": [],
	},
	{
		"label": "Case Details",
		"name": "case_section",
		"opened": True,
		"columns": [
			{
				"name": "column_case",
				"fields": [
					"case_title",
					"primary_insured",
					"status",
					"deal_owner",
					"date_of_birth",
					"tobacco_use",
					"insured_state",
					"next_step",
					"closed_date",
					"probability",
				],
			}
		],
	},
]

LIFE_QUICK_ENTRY = [
	{
		"name": "person_section",
		"columns": [
			{"name": "col_name", "fields": ["first_name"]},
			{"name": "col_last", "fields": ["last_name"]},
		],
	},
	{
		"name": "contact_section",
		"hideBorder": True,
		"columns": [
			{"name": "col_email", "fields": ["email"]},
			{"name": "col_mobile", "fields": ["mobile_no"]},
		],
	},
	{
		"name": "deal_section",
		"columns": [
			{"name": "col_status", "fields": ["status"]},
			{"name": "col_owner", "fields": ["deal_owner"]},
		],
	},
]


def apply_life_layouts():
	"""Replace CRM Deal side panel + quick entry with person-first layouts."""
	_set_layout("CRM Deal", "Side Panel", LIFE_SIDE_PANEL)
	_set_layout("CRM Deal", "Quick Entry", LIFE_QUICK_ENTRY)


def _set_layout(doctype: str, layout_type: str, layout: list):
	if not frappe.db.exists("DocType", "CRM Fields Layout"):
		return
	name = frappe.db.get_value(
		"CRM Fields Layout",
		{"dt": doctype, "type": layout_type},
		"name",
	)
	payload = frappe.as_json(layout)
	if name:
		frappe.db.set_value("CRM Fields Layout", name, "layout", payload)
	else:
		doc = frappe.get_doc(
			{
				"doctype": "CRM Fields Layout",
				"dt": doctype,
				"type": layout_type,
				"layout": payload,
			}
		)
		doc.insert(ignore_permissions=True)
