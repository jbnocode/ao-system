# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import annotations

import json

import frappe
from frappe import _
from frappe.utils import get_datetime, now_datetime

from crm.integrations.api import get_contact_by_phone_number
from crm.vapi.client import get_client
from crm.vapi.prompts import catalog, script_pack, voice_payload

# Vapi call status / endedReason → CRM Call Log status
_VAPI_STATUS_MAP = {
	"queued": "Queued",
	"ringing": "Ringing",
	"in-progress": "In Progress",
	"forwarding": "In Progress",
	"ended": "Completed",
}

_VAPI_ENDED_REASON_MAP = {
	"customer-busy": "Busy",
	"customer-did-not-answer": "No Answer",
	"voicemail": "Completed",
	"silence-timed-out": "No Answer",
	"assistant-error": "Failed",
	"pipeline-error-openai": "Failed",
	"pipeline-error-eleven-labs-voice-failed": "Failed",
	"twilio-failed-to-connect-call": "Failed",
	"vonage-rejected": "Failed",
	"phone-call-provider-closed-websocket": "Failed",
	"call.in-progress.error-providerfault-outbound-sip-480-temporarily-unavailable": "No Answer",
	"call.in-progress.error-providerfault-outbound-sip-486-busy-here": "Busy",
	"call.in-progress.error-providerfault-outbound-sip-603-decline": "Canceled",
	"customer-ended-call": "Completed",
	"assistant-ended-call": "Completed",
	"assistant-ended-call-after-message-spoken": "Completed",
	"assistant-said-end-call-phrase": "Completed",
	"manually-canceled": "Canceled",
	"vonage-completed": "Completed",
	"twilio-completed-call": "Completed",
}


def _require_manager():
	frappe.only_for(("System Manager", "Sales Manager"))


def _require_admin():
	frappe.only_for("System Manager")


def _normalize_phone(number: str) -> str:
	n = (number or "").strip().replace(" ", "")
	if n and not n.startswith("+"):
		# assume US if bare 10 digits
		digits = "".join(c for c in n if c.isdigit())
		if len(digits) == 10:
			return f"+1{digits}"
		if len(digits) == 11 and digits.startswith("1"):
			return f"+{digits}"
	return n


@frappe.whitelist()
def get_vapi_settings() -> dict:
	"""Public-ish settings for UI (no private key)."""
	settings = frappe.get_single("CRM Vapi Settings")
	has_private = False
	try:
		has_private = bool(settings.get_password("private_api_key"))
	except Exception:
		has_private = False
	has_webhook_secret = False
	try:
		has_webhook_secret = bool(settings.get_password("webhook_secret"))
	except Exception:
		has_webhook_secret = False
	return {
		"enabled": bool(settings.enabled),
		"public_key": settings.public_key or "",
		"has_private_key": has_private,
		"has_webhook_secret": has_webhook_secret,
		"default_voice_id": settings.default_voice_id or "warm",
		"dashboard_url": settings.dashboard_url or "https://dashboard.vapi.ai",
		"webhook_url": _webhook_url(),
		"catalog": catalog(),
	}


@frappe.whitelist()
def save_vapi_settings(
	enabled: int | str | None = None,
	public_key: str | None = None,
	private_api_key: str | None = None,
	default_voice_id: str | None = None,
	dashboard_url: str | None = None,
	webhook_secret: str | None = None,
) -> dict:
	_require_admin()
	doc = frappe.get_single("CRM Vapi Settings")
	if enabled is not None:
		doc.enabled = 1 if int(enabled or 0) else 0
	if public_key is not None:
		doc.public_key = public_key
	if default_voice_id is not None:
		doc.default_voice_id = default_voice_id
	if dashboard_url is not None:
		doc.dashboard_url = dashboard_url
	if private_api_key:
		doc.private_api_key = private_api_key
	if webhook_secret:
		doc.webhook_secret = webhook_secret
	doc.save(ignore_permissions=True)
	frappe.db.commit()
	return get_vapi_settings()


@frappe.whitelist()
def get_my_assignment() -> dict:
	"""Agent's phone/assistant assignment for the Call wizard."""
	user = frappe.session.user
	row = _agent_row(user)
	settings = get_vapi_settings()
	# Also surface Twilio telephony agent number as a hint
	twilio_number = frappe.db.get_value("CRM Telephony Agent", user, "twilio_number") or ""
	return {
		"enabled": settings["enabled"],
		"has_private_key": settings["has_private_key"],
		"public_key": settings["public_key"],
		"catalog": settings["catalog"],
		"twilio_number": twilio_number,
		"assignment": _serialize_agent(row) if row else None,
	}


@frappe.whitelist()
def list_assignments() -> list:
	_require_manager()
	rows = frappe.get_all(
		"CRM AI Caller Agent",
		fields=[
			"name",
			"user",
			"user_name",
			"phone_number",
			"vapi_phone_id",
			"vapi_assistant_id",
			"voice_id",
			"script_id",
			"setup_completed",
			"modified",
		],
		order_by="modified desc",
	)
	return rows


@frappe.whitelist()
def list_twilio_numbers_for_link() -> list:
	"""Twilio numbers from CRM + whether already linked in AO AI Caller."""
	_require_manager()
	from crm.integrations.twilio.api import list_phone_numbers

	try:
		numbers = list_phone_numbers() or []
	except Exception:
		numbers = []

	linked = {
		_normalize_phone(r.phone_number): r
		for r in frappe.get_all(
			"CRM AI Caller Agent",
			fields=["name", "user", "user_name", "phone_number", "vapi_phone_id", "vapi_assistant_id"],
			filters={"phone_number": ["is", "set"]},
		)
	}
	out = []
	for n in numbers:
		phone = _normalize_phone(n.get("phone_number") or "")
		agent = linked.get(phone)
		out.append(
			{
				**n,
				"phone_number": phone,
				"ai_linked": bool(agent and agent.get("vapi_phone_id")),
				"ai_user": agent.get("user") if agent else None,
				"ai_user_name": agent.get("user_name") if agent else None,
				"vapi_phone_id": agent.get("vapi_phone_id") if agent else None,
				"vapi_assistant_id": agent.get("vapi_assistant_id") if agent else None,
			}
		)
	return out


@frappe.whitelist()
def link_and_assign(phone_number: str, user: str) -> dict:
	"""Import Twilio number into Vapi (if needed), create/update assistant, assign to user."""
	_require_manager()
	phone_number = _normalize_phone(phone_number)
	if not phone_number or not user:
		frappe.throw(_("Phone number and user are required"))

	if not frappe.db.exists("User", user):
		frappe.throw(_("User {0} not found").format(user))

	# Ensure telephony agent has the number for human dialer consistency
	_ensure_telephony_number(user, phone_number)

	client = get_client()
	twilio = frappe.get_single("CRM Twilio Settings")
	account_sid = twilio.account_sid
	try:
		auth_token = twilio.get_password("auth_token")
	except Exception:
		auth_token = ""
	if not account_sid or not auth_token:
		frappe.throw(_("CRM Twilio Settings account SID and auth token are required to import into Vapi."))

	agent = _get_or_create_agent(user)
	assistant_id = agent.vapi_assistant_id
	if not assistant_id:
		assistant = client.create_assistant(
			_assistant_payload(
				user=user,
				voice_id=agent.voice_id or "warm",
				script_id=agent.script_id or "term",
			)
		)
		assistant_id = assistant.get("id")
		agent.vapi_assistant_id = assistant_id

	phone_id = agent.vapi_phone_id if agent.phone_number == phone_number else None
	if not phone_id:
		phone_id = _find_vapi_phone_id(client, phone_number)
	if not phone_id:
		try:
			imported = client.import_twilio_number(
				number=phone_number,
				twilio_account_sid=account_sid,
				twilio_auth_token=auth_token,
				assistant_id=assistant_id,
				name=f"AO {user}",
			)
			phone_id = imported.get("id")
		except Exception:
			# Number may already exist in Vapi under another import
			phone_id = _find_vapi_phone_id(client, phone_number)
			if not phone_id:
				raise
	if phone_id:
		try:
			client.update_phone_number(phone_id, {"assistantId": assistant_id})
		except Exception:
			frappe.log_error(title=_("Vapi phone assistant link failed"))

	agent.phone_number = phone_number
	agent.vapi_phone_id = phone_id
	agent.vapi_assistant_id = assistant_id
	agent.save(ignore_permissions=True)
	frappe.db.commit()
	return _serialize_agent(agent)


@frappe.whitelist()
def unassign_agent(user: str) -> dict:
	_require_manager()
	if frappe.db.exists("CRM AI Caller Agent", user):
		frappe.delete_doc("CRM AI Caller Agent", user, ignore_permissions=True)
		frappe.db.commit()
	return {"ok": True}


@frappe.whitelist()
def sync_my_setup(
	voice_id: str | None = None,
	script_id: str | None = None,
	custom_script: int | str | None = None,
	respect_dnc: int | str | None = None,
	reviewed_compliance: int | str | None = None,
	setup_completed: int | str | None = None,
) -> dict:
	"""Agent saves wizard choices and patches Vapi assistant."""
	user = frappe.session.user
	agent = _agent_row(user)
	if not agent or not agent.phone_number:
		frappe.throw(_("No phone number assigned yet. Ask your admin to assign one for AI calling."))

	if voice_id is not None:
		agent.voice_id = voice_id
	if script_id is not None:
		agent.script_id = script_id
	if custom_script is not None:
		agent.custom_script = 1 if int(custom_script or 0) else 0
	if respect_dnc is not None:
		agent.respect_dnc = 1 if int(respect_dnc or 0) else 0
	if reviewed_compliance is not None:
		agent.reviewed_compliance = 1 if int(reviewed_compliance or 0) else 0
	if setup_completed is not None:
		agent.setup_completed = 1 if int(setup_completed or 0) else 0

	# Sync to Vapi when we have credentials
	settings = frappe.get_single("CRM Vapi Settings")
	if settings.enabled and agent.vapi_assistant_id:
		try:
			client = get_client()
			client.update_assistant(
				agent.vapi_assistant_id,
				_assistant_payload(
					user=user,
					voice_id=agent.voice_id or "warm",
					script_id=agent.script_id or ("custom" if agent.custom_script else "term"),
				),
			)
		except Exception:
			frappe.log_error(title=_("Vapi assistant sync failed"))

	agent.save(ignore_permissions=True)
	frappe.db.commit()
	return _serialize_agent(agent)


@frappe.whitelist()
def get_widget_config() -> dict:
	"""Public key + assistant id for the test widget."""
	user = frappe.session.user
	settings = get_vapi_settings()
	agent = _agent_row(user)
	return {
		"enabled": settings["enabled"],
		"public_key": settings["public_key"],
		"assistant_id": (agent.vapi_assistant_id if agent else "") or "",
		"phone_number": (agent.phone_number if agent else "") or "",
	}


@frappe.whitelist()
def get_usage_dashboard(days: int | str = 30, user: str | None = None) -> dict:
	"""Manager dashboard: aggregate Vapi calls by CRM AI Caller agent."""
	_require_manager()
	days = max(1, min(int(days or 30), 90))
	from datetime import timedelta

	from frappe.utils import now_datetime

	since = now_datetime() - timedelta(days=days)
	since_iso = since.strftime("%Y-%m-%dT%H:%M:%S.000Z")

	agents = frappe.get_all(
		"CRM AI Caller Agent",
		fields=[
			"user",
			"user_name",
			"phone_number",
			"vapi_assistant_id",
			"vapi_phone_id",
			"setup_completed",
		],
		filters={"vapi_assistant_id": ["is", "set"]},
	)
	if user:
		agents = [a for a in agents if a.user == user]

	assistant_to_agent = {a.vapi_assistant_id: a for a in agents if a.vapi_assistant_id}

	client = get_client()
	raw_calls: list = []
	# Fetch per-assistant for accuracy (Vapi limit defaults to 100)
	if assistant_to_agent:
		for assistant_id in assistant_to_agent:
			try:
				batch = client.list_calls(
					{
						"assistantId": assistant_id,
						"createdAtGe": since_iso,
						"limit": 100,
					}
				)
				raw_calls.extend(batch or [])
			except Exception:
				frappe.log_error(title=_("Vapi list calls failed"))
	else:
		try:
			raw_calls = client.list_calls({"createdAtGe": since_iso, "limit": 100}) or []
		except Exception:
			frappe.throw(_("Could not load calls from Vapi. Check Settings → Vapi."))

	by_user: dict[str, dict] = {}
	for a in agents:
		by_user[a.user] = {
			"user": a.user,
			"user_name": a.user_name or a.user,
			"phone_number": a.phone_number or "",
			"setup_completed": bool(a.setup_completed),
			"calls": 0,
			"ended": 0,
			"failed": 0,
			"seconds": 0,
			"cost": 0.0,
		}

	recent = []
	for c in raw_calls:
		assistant_id = c.get("assistantId") or ""
		agent = assistant_to_agent.get(assistant_id)
		user_key = agent.user if agent else "_unassigned"
		if user_key not in by_user:
			by_user[user_key] = {
				"user": user_key,
				"user_name": _("Unassigned"),
				"phone_number": "",
				"setup_completed": False,
				"calls": 0,
				"ended": 0,
				"failed": 0,
				"seconds": 0,
				"cost": 0.0,
			}
		bucket = by_user[user_key]
		bucket["calls"] += 1
		status = (c.get("status") or "").lower()
		if status == "ended":
			bucket["ended"] += 1
		elif status in ("not-found", "deletion-failed") or (c.get("endedReason") or "").startswith(
			"call-start-error"
		):
			bucket["failed"] += 1

		secs = _call_duration_seconds(c)
		bucket["seconds"] += secs
		cost = _call_cost(c)
		bucket["cost"] += cost

		customer = ""
		cust = c.get("customer") or {}
		if isinstance(cust, dict):
			customer = cust.get("number") or cust.get("name") or ""
		recent.append(
			{
				"id": c.get("id"),
				"user": user_key if user_key != "_unassigned" else "",
				"user_name": bucket["user_name"],
				"status": c.get("status") or "",
				"type": c.get("type") or "",
				"ended_reason": c.get("endedReason") or "",
				"customer": customer,
				"seconds": secs,
				"cost": round(cost, 4),
				"created_at": c.get("createdAt") or c.get("startedAt") or "",
			}
		)

	recent.sort(key=lambda r: r.get("created_at") or "", reverse=True)
	agents_out = sorted(by_user.values(), key=lambda r: (-r["calls"], r["user_name"] or ""))
	for row in agents_out:
		row["minutes"] = round(row["seconds"] / 60.0, 1)
		row["cost"] = round(row["cost"], 4)

	totals = {
		"calls": sum(a["calls"] for a in agents_out),
		"ended": sum(a["ended"] for a in agents_out),
		"failed": sum(a["failed"] for a in agents_out),
		"minutes": round(sum(a["seconds"] for a in agents_out) / 60.0, 1),
		"cost": round(sum(a["cost"] for a in agents_out), 4),
		"agents": len([a for a in agents_out if a["user"] != "_unassigned"]),
	}

	return {
		"days": days,
		"since": since_iso,
		"totals": totals,
		"agents": [a for a in agents_out if a["user"] != "_unassigned" or a["calls"]],
		"recent": recent[:50],
	}


def _call_duration_seconds(call: dict) -> int:
	started = call.get("startedAt") or call.get("createdAt")
	ended = call.get("endedAt")
	if not started or not ended:
		return 0
	try:
		from frappe.utils import get_datetime

		delta = get_datetime(ended) - get_datetime(started)
		return max(0, int(delta.total_seconds()))
	except Exception:
		return 0


def _call_cost(call: dict) -> float:
	if call.get("cost") is not None:
		try:
			return float(call.get("cost") or 0)
		except Exception:
			pass
	total = 0.0
	for item in call.get("costs") or []:
		if isinstance(item, dict) and item.get("cost") is not None:
			try:
				total += float(item["cost"])
			except Exception:
				pass
	return total


def _agent_row(user: str):
	if not user or user == "Guest":
		return None
	if not frappe.db.exists("CRM AI Caller Agent", user):
		return None
	return frappe.get_doc("CRM AI Caller Agent", user)


def _get_or_create_agent(user: str):
	if frappe.db.exists("CRM AI Caller Agent", user):
		return frappe.get_doc("CRM AI Caller Agent", user)
	doc = frappe.get_doc(
		{
			"doctype": "CRM AI Caller Agent",
			"user": user,
			"voice_id": "warm",
			"script_id": "term",
			"respect_dnc": 1,
		}
	)
	doc.insert(ignore_permissions=True)
	return doc


def _serialize_agent(doc) -> dict:
	return {
		"user": doc.user,
		"user_name": doc.user_name,
		"phone_number": doc.phone_number or "",
		"vapi_phone_id": doc.vapi_phone_id or "",
		"vapi_assistant_id": doc.vapi_assistant_id or "",
		"voice_id": doc.voice_id or "",
		"script_id": doc.script_id or "",
		"custom_script": bool(doc.custom_script),
		"respect_dnc": bool(doc.respect_dnc),
		"reviewed_compliance": bool(doc.reviewed_compliance),
		"setup_completed": bool(doc.setup_completed),
	}


@frappe.whitelist()
def start_outbound_call(
	to_number: str,
	reference_doctype: str | None = None,
	reference_docname: str | None = None,
) -> dict:
	"""Create a Vapi outbound phone call and a CRM Call Log row."""
	user = frappe.session.user
	if not user or user == "Guest":
		frappe.throw(_("Login required"), frappe.PermissionError)

	to_number = _normalize_phone(to_number)
	if not to_number:
		frappe.throw(_("Phone number is required"))

	settings = frappe.get_single("CRM Vapi Settings")
	if not settings.enabled:
		frappe.throw(_("Vapi is disabled. Enable it in Settings → Vapi."))

	agent = _agent_row(user)
	if not agent or not agent.phone_number or not agent.vapi_phone_id or not agent.vapi_assistant_id:
		frappe.throw(_("AI Caller is not fully assigned. Ask your admin to link a number."))

	_assert_calling_hours()
	if agent.respect_dnc:
		_assert_not_dnc(to_number)

	client = get_client()
	# Keep assistant webhook URL current
	try:
		client.update_assistant(
			agent.vapi_assistant_id,
			_assistant_payload(
				user=user,
				voice_id=agent.voice_id or "warm",
				script_id=agent.script_id or ("custom" if agent.custom_script else "term"),
			),
		)
	except Exception:
		frappe.log_error(title=_("Vapi assistant sync before call failed"))

	payload = {
		"assistantId": agent.vapi_assistant_id,
		"phoneNumberId": agent.vapi_phone_id,
		"customer": {"number": to_number},
	}
	result = client.create_call(payload)
	call_id = result.get("id") if isinstance(result, dict) else None
	if not call_id:
		frappe.throw(_("Vapi did not return a call id"))

	call_log = frappe.get_doc(
		{
			"doctype": "CRM Call Log",
			"id": call_id,
			"from": agent.phone_number,
			"to": to_number,
			"type": "Outgoing",
			"status": _map_vapi_status(result.get("status") if isinstance(result, dict) else None),
			"caller": user,
			"medium": "Vapi",
			"telephony_medium": "Vapi",
			"start_time": now_datetime(),
			"reference_doctype": reference_doctype or None,
			"reference_docname": reference_docname or None,
		}
	)
	_link_call_log(to_number, call_log, reference_doctype, reference_docname)
	call_log.insert(ignore_permissions=True)
	frappe.db.commit()

	return {
		"call_id": call_id,
		"call_log": call_log.name,
		"status": call_log.status,
		"to": to_number,
		"from": agent.phone_number,
	}


@frappe.whitelist(allow_guest=True)  # nosemgrep: guest-whitelisted-method
def webhook(**kwargs):
	"""Vapi server URL handler — status-update + end-of-call-report → CRM Call Log."""
	_validate_webhook_auth()

	message = _parse_webhook_message(kwargs)
	msg_type = (message.get("type") or "").strip()
	call = message.get("call") if isinstance(message.get("call"), dict) else {}
	call_id = call.get("id") or message.get("callId") or message.get("id")
	if not call_id:
		return {"ok": True, "skipped": "no_call_id"}

	if msg_type in ("status-update", "end-of-call-report") or not msg_type:
		doc = _upsert_call_log_from_webhook(message, call)
		if msg_type == "end-of-call-report" and doc:
			_writeback_end_of_call(doc, message, call)
	return {"ok": True}


def _webhook_url() -> str:
	return f"{frappe.utils.get_url().rstrip('/')}/api/method/crm.vapi.api.webhook"


def _validate_webhook_auth():
	settings = frappe.get_single("CRM Vapi Settings")
	try:
		secret = settings.get_password("webhook_secret") or ""
	except Exception:
		secret = ""
	if not secret:
		return
	auth = (frappe.request.headers.get("Authorization") or "").strip()
	expected = f"Bearer {secret}"
	if auth != expected:
		frappe.throw(_("Invalid webhook authorization"), frappe.AuthenticationError)


def _parse_webhook_message(kwargs) -> dict:
	raw = None
	try:
		raw = frappe.request.get_data(as_text=True)
	except Exception:
		raw = None
	if raw:
		try:
			payload = json.loads(raw)
			if isinstance(payload, dict):
				message = payload.get("message")
				if isinstance(message, dict):
					return message
				return payload
		except Exception:
			pass
	if kwargs:
		message = kwargs.get("message")
		if isinstance(message, dict):
			return message
		if isinstance(message, str):
			try:
				return json.loads(message)
			except Exception:
				pass
		return dict(kwargs)
	return {}


def _upsert_call_log_from_webhook(message: dict, call: dict):
	call_id = call.get("id") or message.get("callId")
	if not call_id:
		return

	status = _map_vapi_status(
		message.get("status") or call.get("status"),
		ended_reason=message.get("endedReason") or call.get("endedReason"),
	)
	duration = _extract_duration(message, call)
	recording = (
		message.get("recordingUrl")
		or (message.get("artifact") or {}).get("recordingUrl")
		or call.get("recordingUrl")
		or ""
	)
	started = call.get("startedAt") or message.get("startedAt")
	ended = call.get("endedAt") or message.get("endedAt")
	customer = call.get("customer") if isinstance(call.get("customer"), dict) else {}
	phone_number_obj = call.get("phoneNumber") if isinstance(call.get("phoneNumber"), dict) else {}
	to_number = _normalize_phone(customer.get("number") or "")
	from_number = _normalize_phone(phone_number_obj.get("number") or "")

	assistant_id = call.get("assistantId")
	if not assistant_id and isinstance(call.get("assistant"), dict):
		assistant_id = call.get("assistant").get("id")
	caller = None
	if assistant_id:
		caller = frappe.db.get_value("CRM AI Caller Agent", {"vapi_assistant_id": assistant_id}, "user")

	if frappe.db.exists("CRM Call Log", call_id):
		doc = frappe.get_doc("CRM Call Log", call_id)
		doc.status = status or doc.status
		if duration:
			doc.duration = duration
		if recording:
			doc.recording_url = recording
		if started:
			doc.start_time = _parse_iso_dt(started) or doc.start_time
		if ended:
			doc.end_time = _parse_iso_dt(ended) or doc.end_time
		doc.telephony_medium = "Vapi"
		doc.medium = "Vapi"
		doc.save(ignore_permissions=True)
		frappe.db.commit()
		return doc

	# Create if we somehow missed start_outbound_call (e.g. inbound via same assistant)
	direction = (call.get("type") or "outboundPhoneCall").lower()
	call_type = "Incoming" if "inbound" in direction else "Outgoing"
	if not from_number and caller:
		from_number = frappe.db.get_value("CRM AI Caller Agent", caller, "phone_number") or "unknown"
	if not to_number:
		to_number = "unknown"
	if call_type == "Incoming":
		# swap typical inbound: customer is from
		if customer.get("number"):
			from_number = _normalize_phone(customer.get("number"))
		if phone_number_obj.get("number"):
			to_number = _normalize_phone(phone_number_obj.get("number"))

	doc = frappe.get_doc(
		{
			"doctype": "CRM Call Log",
			"id": call_id,
			"from": from_number or "unknown",
			"to": to_number or "unknown",
			"type": call_type,
			"status": status or "Queued",
			"caller": caller if call_type == "Outgoing" else None,
			"receiver": caller if call_type == "Incoming" else None,
			"medium": "Vapi",
			"telephony_medium": "Vapi",
			"duration": duration or None,
			"recording_url": recording or None,
			"start_time": _parse_iso_dt(started) or now_datetime(),
			"end_time": _parse_iso_dt(ended),
		}
	)
	contact_number = from_number if call_type == "Incoming" else to_number
	_link_call_log(contact_number, doc, None, None)
	doc.insert(ignore_permissions=True)
	frappe.db.commit()
	return doc


def _writeback_end_of_call(call_log, message: dict, call: dict):
	"""Persist summary/transcript on the Call Log and as an FCRM Note on the Lead/Deal."""
	summary, transcript = _extract_summary_and_transcript(message, call)
	if not summary and not transcript:
		return

	try:
		if summary:
			call_log.ai_summary = summary
		if transcript:
			call_log.ai_transcript = transcript
		call_log.telephony_medium = "Vapi"
		call_log.medium = "Vapi"

		note = _upsert_ai_call_note(call_log, summary, transcript)
		if note:
			call_log.note = note.name
			call_log.link_with_reference_doc("FCRM Note", note.name)

		call_log.save(ignore_permissions=True)
		frappe.db.commit()
	except Exception:
		frappe.log_error(title=_("Vapi end-of-call writeback failed"))


def _extract_summary_and_transcript(message: dict, call: dict) -> tuple[str, str]:
	artifact = message.get("artifact") if isinstance(message.get("artifact"), dict) else {}
	analysis = message.get("analysis") if isinstance(message.get("analysis"), dict) else {}

	summary = (
		message.get("summary")
		or analysis.get("summary")
		or artifact.get("summary")
		or call.get("summary")
		or ""
	)
	transcript = (
		message.get("transcript")
		or artifact.get("transcript")
		or call.get("transcript")
		or ""
	)
	# Prefer joined messages if transcript missing
	if not transcript:
		messages = artifact.get("messages") or message.get("messages") or []
		lines = []
		for row in messages:
			if not isinstance(row, dict):
				continue
			role = (row.get("role") or row.get("speaker") or "").strip()
			text = (row.get("message") or row.get("content") or "").strip()
			if text:
				lines.append(f"{role}: {text}" if role else text)
		transcript = "\n".join(lines)

	# Structured data as appendix to summary
	structured = (
		message.get("structuredData")
		or analysis.get("structuredData")
		or artifact.get("structuredData")
	)
	if structured and isinstance(structured, dict) and structured:
		try:
			blob = json.dumps(structured, indent=2, default=str)
			summary = (summary + "\n\nStructured data:\n" + blob).strip() if summary else f"Structured data:\n{blob}"
		except Exception:
			pass

	return (str(summary).strip(), str(transcript).strip())


def _upsert_ai_call_note(call_log, summary: str, transcript: str):
	title = _("AI Call Summary")
	content = _format_ai_note_html(summary, transcript, call_log)
	ref_dt = call_log.reference_doctype
	ref_dn = call_log.reference_docname
	if not ref_dt or not ref_dn:
		# Prefer linked lead/deal from Dynamic Link table
		for link in call_log.get("links") or []:
			if link.link_doctype in ("CRM Lead", "CRM Deal") and link.link_name:
				ref_dt, ref_dn = link.link_doctype, link.link_name
				break

	existing = call_log.note
	if existing and frappe.db.exists("FCRM Note", existing):
		frappe.db.set_value(
			"FCRM Note",
			existing,
			{
				"title": title,
				"content": content,
				"reference_doctype": ref_dt or None,
				"reference_docname": ref_dn or None,
			},
			update_modified=True,
		)
		return frappe.get_doc("FCRM Note", existing)

	note = frappe.get_doc(
		{
			"doctype": "FCRM Note",
			"title": title,
			"content": content,
			"reference_doctype": ref_dt or None,
			"reference_docname": ref_dn or None,
		}
	)
	note.insert(ignore_permissions=True)
	return note


def _format_ai_note_html(summary: str, transcript: str, call_log) -> str:
	parts = [
		f"<p><strong>{_('AI call')}</strong> · {frappe.utils.escape_html(call_log.get('to') or '')}</p>"
	]
	if summary:
		parts.append(f"<p><strong>{_('Summary')}</strong></p>")
		parts.append(f"<p>{frappe.utils.escape_html(summary).replace(chr(10), '<br>')}</p>")
	if transcript:
		parts.append(f"<p><strong>{_('Transcript')}</strong></p>")
		parts.append(
			f"<pre style='white-space:pre-wrap;font-size:12px'>{frappe.utils.escape_html(transcript)}</pre>"
		)
	if call_log.get("recording_url"):
		url = frappe.utils.escape_html(call_log.recording_url)
		parts.append(f"<p><a href=\"{url}\" target=\"_blank\">{_('Recording')}</a></p>")
	return "\n".join(parts)


def _map_vapi_status(status: str | None, ended_reason: str | None = None) -> str:
	if ended_reason:
		mapped = _VAPI_ENDED_REASON_MAP.get(ended_reason)
		if mapped:
			return mapped
		# generic failures
		if "error" in ended_reason or "failed" in ended_reason:
			return "Failed"
		if "busy" in ended_reason:
			return "Busy"
		if "did-not-answer" in ended_reason or "no-answer" in ended_reason:
			return "No Answer"
		if "cancel" in ended_reason:
			return "Canceled"
	if not status:
		return "Initiated"
	return _VAPI_STATUS_MAP.get(str(status).lower(), "Initiated")


def _extract_duration(message: dict, call: dict) -> int | None:
	for key in ("durationSeconds", "duration"):
		for src in (message, call, message.get("artifact") or {}):
			if not isinstance(src, dict):
				continue
			val = src.get(key)
			if val is None:
				continue
			try:
				return max(0, int(float(val)))
			except Exception:
				pass
	started = call.get("startedAt") or message.get("startedAt")
	ended = call.get("endedAt") or message.get("endedAt")
	if started and ended:
		try:
			delta = get_datetime(ended) - get_datetime(started)
			return max(0, int(delta.total_seconds()))
		except Exception:
			pass
	return None


def _parse_iso_dt(value):
	if not value:
		return None
	try:
		return get_datetime(value)
	except Exception:
		return None


def _assert_calling_hours():
	"""TCPA-style window: 8:00–21:00 in the site timezone."""
	now = now_datetime()
	hour = now.hour
	if hour < 8 or hour >= 21:
		frappe.throw(
			_("Outbound AI calls are only allowed between 8:00 AM and 9:00 PM ({0}).").format(
				frappe.utils.get_system_timezone()
			)
		)


def _assert_not_dnc(phone: str):
	"""Block if a matching Lead is marked Lost with DNC-like reason, or communication_status is Do Not Contact."""
	variants = _phone_match_variants(phone)
	if not variants:
		return
	leads = frappe.get_all(
		"CRM Lead",
		filters={"mobile_no": ["in", variants], "converted": 0},
		fields=["name", "status", "communication_status", "lost_reason"],
		limit=20,
	)
	# also match phone field
	leads += frappe.get_all(
		"CRM Lead",
		filters={"phone": ["in", variants], "converted": 0},
		fields=["name", "status", "communication_status", "lost_reason"],
		limit=20,
	)
	seen = set()
	for lead in leads:
		if lead.name in seen:
			continue
		seen.add(lead.name)
		comm = (lead.communication_status or "").lower()
		lost = (lead.lost_reason or "").lower()
		if "do not contact" in comm or "dnc" in comm or "do not call" in comm:
			frappe.throw(_("This number is marked Do Not Contact ({0}).").format(lead.name))
		if lead.status == "Lost" and ("dnc" in lost or "do not call" in lost or "do not contact" in lost):
			frappe.throw(_("This number is on a Lost / DNC lead ({0}).").format(lead.name))


def _phone_match_variants(phone: str) -> list[str]:
	n = _normalize_phone(phone)
	if not n:
		return []
	digits = "".join(c for c in n if c.isdigit())
	out = {n, digits}
	if digits.startswith("1") and len(digits) == 11:
		out.add(digits[1:])
		out.add(f"+{digits}")
	elif len(digits) == 10:
		out.add(f"+1{digits}")
		out.add(f"1{digits}")
	return [v for v in out if v]


def _link_call_log(contact_number, call_log, reference_doctype, reference_docname):
	if reference_doctype and reference_docname:
		try:
			call_log.link_with_reference_doc(reference_doctype, reference_docname)
			return
		except Exception:
			pass
	if not contact_number:
		return
	contact = get_contact_by_phone_number(contact_number)
	if not contact.get("name"):
		return
	doctype = "Contact"
	docname = contact.get("name")
	if contact.get("lead"):
		doctype = "CRM Lead"
		docname = contact.get("lead")
	elif contact.get("deal"):
		doctype = "CRM Deal"
		docname = contact.get("deal")
	try:
		call_log.link_with_reference_doc(doctype, docname)
	except Exception:
		pass


def _assistant_payload(user: str, voice_id: str, script_id: str) -> dict:
	pack = script_pack(script_id)
	full_name = frappe.db.get_value("User", user, "full_name") or user.split("@")[0]
	agent_name = (full_name or "your agent").split()[0]
	first = (pack.get("first_message") or "").format(agent_name=agent_name)
	server = {
		"url": _webhook_url(),
		"timeoutSeconds": 20,
	}
	try:
		secret = frappe.get_single("CRM Vapi Settings").get_password("webhook_secret") or ""
	except Exception:
		secret = ""
	if secret:
		server["headers"] = {"Authorization": f"Bearer {secret}"}
	return {
		"name": f"AO {full_name}",
		"firstMessage": first,
		"model": {
			"provider": "openai",
			"model": "gpt-4o-mini",
			"messages": [{"role": "system", "content": pack["system"]}],
		},
		"voice": voice_payload(voice_id),
		"server": server,
		"serverMessages": ["status-update", "end-of-call-report"],
	}


def _find_vapi_phone_id(client, phone_number: str) -> str | None:
	try:
		for row in client.list_phone_numbers():
			num = _normalize_phone(row.get("number") or row.get("phoneNumber") or "")
			if num == phone_number:
				return row.get("id")
	except Exception:
		return None
	return None


def _ensure_telephony_number(user: str, phone_number: str):
	"""Keep CRM Telephony Agent in sync when assigning for AI."""
	if frappe.db.exists("CRM Telephony Agent", user):
		frappe.db.set_value("CRM Telephony Agent", user, "twilio_number", phone_number)
		return
	doc = frappe.get_doc(
		{
			"doctype": "CRM Telephony Agent",
			"user": user,
			"twilio_number": phone_number,
			"default_medium": "Twilio",
		}
	)
	doc.insert(ignore_permissions=True)
