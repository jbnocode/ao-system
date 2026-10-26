# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe


def execute():
	"""Ensure CRM Live Settings single + AI Caller Agent live voice columns exist."""
	frappe.reload_doc("fcrm", "doctype", "crm_live_settings")
	frappe.reload_doc("fcrm", "doctype", "crm_ai_caller_agent")
	frappe.reload_doc("fcrm", "doctype", "crm_call_log")

	if not frappe.db.exists("CRM Live Settings"):
		doc = frappe.new_doc("CRM Live Settings")
		doc.enabled = 0
		doc.default_voice_id = "cedar"
		doc.default_script_id = "term"
		doc.calling_hours_start = 8
		doc.calling_hours_end = 21
		doc.insert(ignore_permissions=True)

	# Sync any missing columns after json reload
	frappe.db.updatedb("CRM AI Caller Agent")
	frappe.db.updatedb("CRM Live Settings")
	frappe.db.updatedb("CRM Call Log")
