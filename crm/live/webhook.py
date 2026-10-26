# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""Status / end-of-call updates for GPT-Live phone calls."""

from __future__ import annotations

import frappe
from frappe import _


_TWILIO_STATUS_MAP = {
	"queued": "Queued",
	"initiated": "Queued",
	"ringing": "Ringing",
	"in-progress": "In Progress",
	"answered": "In Progress",
	"completed": "Completed",
	"busy": "Busy",
	"no-answer": "No Answer",
	"failed": "Failed",
	"canceled": "Canceled",
}


def validate_live_webhook_auth():
	settings = frappe.get_single("CRM Live Settings")
	try:
		secret = settings.get_password("webhook_secret") or ""
	except Exception:
		secret = ""
	headers = frappe.request.headers
	provided = (headers.get("X-CRM-Live-Secret") or "").strip()
	if not provided:
		auth = (headers.get("Authorization") or "").strip()
		if auth.lower().startswith("bearer "):
			provided = auth[7:].strip()
	# Token resolve returns OpenAI key — require a configured secret match
	if not secret:
		frappe.throw(
			_("Live webhook secret is not configured in CRM Live Settings"),
			frappe.AuthenticationError,
		)
	if provided != secret:
		frappe.throw(_("Invalid Live webhook authorization"), frappe.AuthenticationError)


def apply_twilio_status(call_log: str, call_status: str, call_sid: str | None = None, duration: str | None = None):
	if not call_log or not frappe.db.exists("CRM Call Log", call_log):
		return
	status = _TWILIO_STATUS_MAP.get((call_status or "").lower(), None)
	updates = {}
	if status:
		updates["status"] = status
	if call_sid:
		updates["id"] = call_sid
	if duration not in (None, ""):
		try:
			updates["duration"] = int(float(duration))
		except Exception:
			pass
	if updates:
		frappe.db.set_value("CRM Call Log", call_log, updates)
		frappe.db.commit()


def bridge_session_ended(token: str, *, transcript: str | None = None, duration: int | None = None):
	"""Optional callback from media bridge when Live session closes."""
	from crm.live.twilio_bridge import peek_call_token

	ctx = peek_call_token(token) or {}
	# Find latest matching call log for this user/direction
	filters = {"telephony_medium": "GPT-Live", "caller": ctx.get("user")}
	name = frappe.db.get_value(
		"CRM Call Log",
		filters,
		"name",
		order_by="creation desc",
	)
	if not name:
		return
	updates = {"status": "Completed"}
	if duration is not None:
		updates["duration"] = int(duration)
	frappe.db.set_value("CRM Call Log", name, updates)
	if transcript:
		try:
			note = frappe.get_doc(
				{
					"doctype": "FCRM Note",
					"title": "AI call summary",
					"content": transcript[:4000],
					"reference_doctype": "CRM Call Log",
					"reference_docname": name,
				}
			)
			note.insert(ignore_permissions=True)
		except Exception:
			frappe.log_error(title="Live call note failed")
	frappe.db.commit()
