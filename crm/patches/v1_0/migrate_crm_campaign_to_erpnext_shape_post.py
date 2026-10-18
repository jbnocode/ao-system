# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""Restore schedules + CRM Email Campaigns after DocType sync."""

from __future__ import annotations

import json

import frappe
from frappe.utils import today

from crm.patches.v1_0.migrate_crm_campaign_to_erpnext_shape_pre import CACHE_KEY


def execute():
	raw = frappe.cache.get_value(CACHE_KEY)
	if not raw:
		return
	try:
		payload = json.loads(raw)
	except (TypeError, json.JSONDecodeError):
		return

	if not frappe.db.exists("DocType", "CRM Campaign"):
		return

	for row in payload:
		name = row.get("name")
		if not name or not frappe.db.exists("CRM Campaign", name):
			continue
		doc = frappe.get_doc("CRM Campaign", name)
		doc.flags.ignore_validate = True
		doc.set("campaign_schedules", [])
		for step in row.get("steps") or []:
			channel = step.get("channel") or "Email"
			entry = {
				"channel": channel,
				"send_after_days": int(step.get("send_after_days") or 0),
				"email_template": step.get("email_template") or "",
				"sms_body": step.get("sms_body") or "",
			}
			# Soften missing email templates → SMS so save succeeds
			if channel == "Email" and not entry["email_template"]:
				entry["channel"] = "SMS"
				entry["sms_body"] = entry["sms_body"] or "Follow-up"
			if entry["channel"] == "SMS" and not entry["sms_body"]:
				continue
			if entry["channel"] == "Email" and not frappe.db.exists(
				"Email Template", entry["email_template"]
			):
				entry["channel"] = "SMS"
				entry["sms_body"] = entry["sms_body"] or "Follow-up"
				entry["email_template"] = ""
			doc.append("campaign_schedules", entry)
		doc.description = row.get("description") or doc.description
		doc.save(ignore_permissions=True)

		if not frappe.db.exists("DocType", "CRM Email Campaign"):
			continue
		start = row.get("start_date") or today()
		sender = row.get("sender") or "Administrator"
		for member in row.get("members") or []:
			ref_dt = member.get("reference_doctype") or "CRM Lead"
			ref_name = member.get("reference_name")
			if not ref_name or not frappe.db.exists(ref_dt, ref_name):
				continue
			if frappe.db.exists(
				"CRM Email Campaign",
				{"campaign_name": name, "recipient": ref_name, "status": ("!=", "Completed")},
			):
				continue
			try:
				ec = frappe.get_doc(
					{
						"doctype": "CRM Email Campaign",
						"campaign_name": name,
						"email_campaign_for": ref_dt
						if ref_dt in ("CRM Lead", "Contact", "CRM Deal", "Email Group")
						else "CRM Lead",
						"recipient": ref_name,
						"start_date": start,
						"sender": sender,
					}
				)
				ec.flags.ignore_start_date_check = True
				ec.insert(ignore_permissions=True)
			except Exception:
				frappe.log_error(title=f"Migrate email campaign failed: {name}/{ref_name}")

	frappe.cache.delete_value(CACHE_KEY)

	# Drop obsolete child DocTypes if present
	for obsolete in ("CRM Campaign Step", "CRM Campaign Member"):
		if frappe.db.exists("DocType", obsolete):
			try:
				frappe.delete_doc("DocType", obsolete, force=True, ignore_permissions=True)
			except Exception:
				pass
