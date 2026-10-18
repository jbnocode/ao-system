# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe


def execute():
	"""Ensure life statuses + case fields. Life mode / flows stay opt-in via Settings."""
	from crm.life.fields import ensure_case_fields
	from crm.life.pipeline import ensure_life_statuses

	ensure_life_statuses()
	ensure_case_fields()
	frappe.db.commit()
