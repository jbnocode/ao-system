# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def execute():
	"""Attribution link from CRM Lead → CRM Campaign."""
	if not frappe.db.exists("DocType", "CRM Campaign"):
		return
	create_custom_fields(
		{
			"CRM Lead": [
				{
					"fieldname": "campaign",
					"label": "Campaign",
					"fieldtype": "Link",
					"options": "CRM Campaign",
					"insert_after": "source",
					"in_standard_filter": 1,
				}
			]
		},
		ignore_validate=True,
	)
	frappe.clear_cache(doctype="CRM Lead")
