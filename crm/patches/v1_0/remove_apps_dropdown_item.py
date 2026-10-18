import frappe

from crm.fcrm.doctype.fcrm_settings.fcrm_settings import sync_table


def execute():
	"""Drop the Apps / desk switcher from the CRM user dropdown."""
	if not frappe.db.exists("DocType", "FCRM Settings"):
		return
	sync_table("dropdown_items", "standard_dropdown_items")
