# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""Snapshot old CRM Campaign steps/members before DocType sync drops them."""

from __future__ import annotations

import json

import frappe


CACHE_KEY = "crm_campaign_erpnext_migrate_v1"


def execute():
	if not frappe.db.exists("DocType", "CRM Campaign"):
		return
	if not frappe.db.table_exists("tabCRM Campaign Step") and not frappe.db.table_exists(
		"tabCRM Campaign Member"
	):
		return

	cols = {c[0] for c in frappe.db.sql("show columns from `tabCRM Campaign`")}
	select = ["name", "campaign_name"]
	for optional in ("description", "start_date", "sender"):
		if optional in cols:
			select.append(optional)

	payload = []
	for row in frappe.db.sql(
		f"select {', '.join(select)} from `tabCRM Campaign`",
		as_dict=True,
	):
		name = row.name
		steps = []
		if frappe.db.table_exists("tabCRM Campaign Step"):
			steps = frappe.db.sql(
				"""
				select channel, send_after_days, email_template, sms_body
				from `tabCRM Campaign Step`
				where parent=%s
				order by idx
				""",
				name,
				as_dict=True,
			)
		members = []
		if frappe.db.table_exists("tabCRM Campaign Member"):
			members = frappe.db.sql(
				"""
				select reference_doctype, reference_name, status
				from `tabCRM Campaign Member`
				where parent=%s
				order by idx
				""",
				name,
				as_dict=True,
			)
		payload.append(
			{
				"name": name,
				"campaign_name": row.get("campaign_name"),
				"description": row.get("description") or "",
				"start_date": str(row.get("start_date") or ""),
				"sender": row.get("sender") or "",
				"steps": [
					{
						"channel": s.get("channel") or "Email",
						"send_after_days": int(s.get("send_after_days") or 0),
						"email_template": s.get("email_template") or "",
						"sms_body": s.get("sms_body") or "",
					}
					for s in steps
				],
				"members": [
					{
						"reference_doctype": m.get("reference_doctype") or "CRM Lead",
						"reference_name": m.get("reference_name"),
						"status": m.get("status") or "Enrolled",
					}
					for m in members
					if m.get("reference_name")
				],
			}
		)

	frappe.cache.set_value(CACHE_KEY, json.dumps(payload))
