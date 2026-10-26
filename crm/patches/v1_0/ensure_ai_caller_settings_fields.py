import frappe


def execute():
	"""Reload AI caller settings so voice quality + calling hours fields exist."""
	if frappe.db.exists("DocType", "CRM Vapi Settings"):
		frappe.reload_doctype("CRM Vapi Settings", force=True)
