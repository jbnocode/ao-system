import frappe


def execute():
	"""Ensure CRM Phone Number Request exists; rename Pending → Requested."""
	if frappe.db.exists("DocType", "CRM Phone Number Request"):
		frappe.reload_doctype("CRM Phone Number Request", force=True)
	if frappe.db.has_table("tabCRM Phone Number Request"):
		frappe.db.sql(
			"""
			UPDATE `tabCRM Phone Number Request`
			SET status = 'Requested'
			WHERE status = 'Pending'
			"""
		)
