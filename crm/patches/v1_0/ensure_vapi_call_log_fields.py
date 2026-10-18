import frappe


def execute():
	"""Reload Call Log + Vapi DocTypes so AI summary/transcript and Vapi medium exist."""
	for dt in ("CRM Call Log", "CRM Vapi Settings", "CRM AI Caller Agent"):
		if frappe.db.exists("DocType", dt):
			frappe.reload_doctype(dt, force=True)
