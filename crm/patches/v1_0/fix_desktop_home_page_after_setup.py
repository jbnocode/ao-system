import frappe
from frappe.utils import cint


def execute():
	"""Sites that finished setup but still have desktop:home_page=setup-wizard
	bounce Desk users into the wizard (URL like /desk/build/setup-wizard).

	Normal setup_wizard completion sets this to workspace; recover if it was missed.
	"""
	if not cint(frappe.get_system_settings("setup_complete")):
		return

	if frappe.db.get_default("desktop:home_page") != "setup-wizard":
		return

	frappe.db.set_default("desktop:home_page", "workspace")
	frappe.db.commit()
