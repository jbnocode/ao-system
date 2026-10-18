# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""Case / household custom fields for life agency mode."""

from __future__ import annotations

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

CUSTOM_FIELDS = {
	"CRM Deal": [
		{
			"fieldname": "primary_insured",
			"label": "Primary Insured",
			"fieldtype": "Link",
			"options": "Contact",
			"insert_after": "contact",
			"in_standard_filter": 1,
		},
		{
			"fieldname": "case_title",
			"label": "Case Title",
			"fieldtype": "Data",
			"insert_after": "primary_insured",
			"in_list_view": 1,
			"in_standard_filter": 1,
		},
		{
			"fieldname": "date_of_birth",
			"label": "Date of Birth",
			"fieldtype": "Date",
			"insert_after": "case_title",
		},
		{
			"fieldname": "tobacco_use",
			"label": "Tobacco Use",
			"fieldtype": "Select",
			"options": "\nUnknown\nNever\nFormer\nCurrent",
			"insert_after": "date_of_birth",
		},
		{
			"fieldname": "insured_state",
			"label": "State",
			"fieldtype": "Data",
			"insert_after": "tobacco_use",
		},
	],
	"CRM Contacts": [
		{
			"fieldname": "relationship",
			"label": "Relationship",
			"fieldtype": "Select",
			"options": "\nSelf\nSpouse\nChild\nParent\nOther",
			"insert_after": "is_primary",
			"in_list_view": 1,
		},
	],
}


def ensure_case_fields():
	create_custom_fields(CUSTOM_FIELDS, ignore_validate=True)
	frappe.clear_cache(doctype="CRM Deal")
	frappe.clear_cache(doctype="CRM Contacts")
