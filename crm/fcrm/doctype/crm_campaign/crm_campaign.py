# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""CRM Campaign — marketing campaign definition (ERPNext Campaign structure).

Schedules live here. Per-recipient runs are CRM Email Campaign documents.
"""

from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document


class CRMCampaign(Document):
	def validate(self):
		self._validate_schedules()

	def _validate_schedules(self):
		seen: set[tuple[str, int]] = set()
		for row in self.campaign_schedules or []:
			channel = row.channel or "Email"
			days = int(row.send_after_days or 0)
			if days < 0:
				frappe.throw(_("Send After (days) cannot be negative"))
			key = (channel, days)
			if key in seen:
				frappe.throw(_("Duplicate schedule for {0} on day {1}").format(channel, days))
			seen.add(key)
			if channel == "Email" and not row.email_template:
				frappe.throw(_("Email schedule rows need an Email Template"))
			if channel == "Email" and row.email_template:
				if not frappe.db.exists("Email Template", row.email_template):
					frappe.throw(
						_("Email Template {0} not found").format(row.email_template)
					)
			if channel == "SMS" and not (row.sms_body or "").strip():
				frappe.throw(_("SMS schedule rows need a message body"))
