import frappe


def execute():
	"""Ensure the team credit wallet singleton exists after DocType install."""
	if frappe.db.exists("DocType", "CRM Credit Wallet") and not frappe.db.exists(
		"CRM Credit Wallet", "CRM Credit Wallet"
	):
		frappe.get_doc({"doctype": "CRM Credit Wallet", "balance": 0}).insert(ignore_permissions=True)
