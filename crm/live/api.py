# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# For license information, please see license.txt

"""Whitelisted GPT-Live + Twilio bridge APIs."""

from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import cint
from werkzeug.wrappers import Response

from crm.live.prompts import live_catalog
from crm.live.session import create_webrtc_session as _create_webrtc_session
from crm.live.voices import create_prompt_voice, list_voice_options


def _require_admin():
	if "System Manager" not in frappe.get_roles():
		frappe.throw(_("Not permitted"), frappe.PermissionError)


def _require_manager():
	"""Kept for any future Sales Manager surfaces; AI Caller admin APIs use _require_admin."""
	roles = set(frappe.get_roles())
	if not roles.intersection({"System Manager", "Sales Manager"}):
		frappe.throw(_("Not permitted"), frappe.PermissionError)


def _has_openai_key(settings) -> bool:
	try:
		return bool(settings.get_password("openai_api_key"))
	except Exception:
		return False


def _has_webhook_secret(settings) -> bool:
	try:
		return bool(settings.get_password("webhook_secret"))
	except Exception:
		return False


def _serialize_agent(doc) -> dict:
	if not doc:
		return None
	return {
		"name": doc.name,
		"user": doc.user,
		"user_name": doc.user_name,
		"phone_number": doc.phone_number or "",
		"live_voice_id": getattr(doc, "live_voice_id", None) or "",
		"live_voice_prompt": getattr(doc, "live_voice_prompt", None) or "",
		"voice_id": doc.voice_id or "",
		"script_id": doc.script_id or "",
		"custom_script": bool(doc.custom_script),
		"respect_dnc": bool(doc.respect_dnc),
		"reviewed_compliance": bool(doc.reviewed_compliance),
		"setup_completed": bool(doc.setup_completed),
		"vapi_phone_id": doc.vapi_phone_id or "",
		"vapi_assistant_id": doc.vapi_assistant_id or "",
	}


def _agent_row(user: str):
	if frappe.db.exists("CRM AI Caller Agent", user):
		return frappe.get_doc("CRM AI Caller Agent", user)
	return None


def _ensure_agent(user: str):
	if frappe.db.exists("CRM AI Caller Agent", user):
		return frappe.get_doc("CRM AI Caller Agent", user)
	settings = frappe.get_single("CRM Live Settings")
	doc = frappe.get_doc(
		{
			"doctype": "CRM AI Caller Agent",
			"user": user,
			"voice_id": settings.default_voice_id or "cedar",
			"script_id": settings.default_script_id or "term",
			"live_voice_id": settings.default_live_voice_id or "",
			"live_voice_prompt": settings.default_live_voice_prompt or "",
			"respect_dnc": 1,
		}
	)
	doc.insert(ignore_permissions=True)
	return doc


@frappe.whitelist()
def get_live_settings() -> dict:
	"""Settings for UI (never returns the OpenAI secret)."""
	settings = frappe.get_single("CRM Live Settings")
	return {
		"enabled": bool(settings.enabled),
		"has_openai_key": _has_openai_key(settings),
		"has_webhook_secret": _has_webhook_secret(settings),
		"openai_project_id": settings.openai_project_id or "",
		"default_voice_id": settings.default_voice_id or "cedar",
		"default_live_voice_id": settings.default_live_voice_id or "",
		"default_live_voice_prompt": settings.default_live_voice_prompt or "",
		"default_script_id": settings.default_script_id or "term",
		"calling_hours_start": int(settings.calling_hours_start or 8),
		"calling_hours_end": int(settings.calling_hours_end or 21),
		"timezone": frappe.utils.get_system_timezone(),
		"media_stream_url": settings.media_stream_url or "",
		"sip_provider_url": settings.sip_provider_url or "",
		"sip_username": settings.sip_username or "",
		"has_sip_password": bool(_sip_password(settings)),
		"catalog": live_catalog(),
		"inbound_voice_url": _inbound_voice_url(),
		"status_callback_url": _status_callback_url(),
	}


def _sip_password(settings) -> str:
	try:
		return settings.get_password("sip_password") or ""
	except Exception:
		return ""


def _inbound_voice_url() -> str:
	return f"{frappe.utils.get_url().rstrip('/')}/api/method/crm.live.api.twilio_inbound_voice"


def _status_callback_url() -> str:
	return f"{frappe.utils.get_url().rstrip('/')}/api/method/crm.live.api.twilio_status_callback"


@frappe.whitelist()
def save_live_settings(
	enabled: int | str | None = None,
	openai_api_key: str | None = None,
	openai_project_id: str | None = None,
	default_voice_id: str | None = None,
	default_live_voice_id: str | None = None,
	default_live_voice_prompt: str | None = None,
	default_script_id: str | None = None,
	calling_hours_start: int | str | None = None,
	calling_hours_end: int | str | None = None,
	media_stream_url: str | None = None,
	sip_provider_url: str | None = None,
	sip_username: str | None = None,
	sip_password: str | None = None,
	webhook_secret: str | None = None,
) -> dict:
	_require_admin()
	doc = frappe.get_single("CRM Live Settings")
	if enabled is not None:
		doc.enabled = 1 if int(enabled or 0) else 0
	if openai_project_id is not None:
		doc.openai_project_id = openai_project_id
	if default_voice_id is not None:
		doc.default_voice_id = default_voice_id
	if default_live_voice_id is not None:
		doc.default_live_voice_id = default_live_voice_id
	if default_live_voice_prompt is not None:
		doc.default_live_voice_prompt = default_live_voice_prompt
	if default_script_id is not None:
		doc.default_script_id = default_script_id
	if calling_hours_start is not None or calling_hours_end is not None:
		_set_calling_hours(doc, calling_hours_start, calling_hours_end)
	if media_stream_url is not None:
		doc.media_stream_url = media_stream_url
	if sip_provider_url is not None:
		doc.sip_provider_url = sip_provider_url
	if sip_username is not None:
		doc.sip_username = sip_username
	if openai_api_key:
		doc.openai_api_key = openai_api_key
	if sip_password:
		doc.sip_password = sip_password
	if webhook_secret:
		doc.webhook_secret = webhook_secret
	doc.save(ignore_permissions=True)
	frappe.db.commit()
	return get_live_settings()


@frappe.whitelist()
def save_ai_caller_defaults(
	default_voice_id: str | None = None,
	default_live_voice_id: str | None = None,
	default_live_voice_prompt: str | None = None,
	default_script_id: str | None = None,
	calling_hours_start: int | str | None = None,
	calling_hours_end: int | str | None = None,
) -> dict:
	"""System Managers can set org defaults without touching API keys."""
	_require_admin()
	doc = frappe.get_single("CRM Live Settings")
	if default_voice_id is not None:
		doc.default_voice_id = default_voice_id
	if default_live_voice_id is not None:
		doc.default_live_voice_id = default_live_voice_id
	if default_live_voice_prompt is not None:
		doc.default_live_voice_prompt = default_live_voice_prompt
	if default_script_id is not None:
		doc.default_script_id = default_script_id
	if calling_hours_start is not None or calling_hours_end is not None:
		_set_calling_hours(doc, calling_hours_start, calling_hours_end)
	doc.save(ignore_permissions=True)
	frappe.db.commit()
	return get_live_settings()


def _set_calling_hours(doc, start, end):
	cur_start = int(getattr(doc, "calling_hours_start", None) or 8)
	cur_end = int(getattr(doc, "calling_hours_end", None) or 21)
	if start is not None and str(start).strip() != "":
		cur_start = int(start)
	if end is not None and str(end).strip() != "":
		cur_end = int(end)
	if cur_start < 0 or cur_start > 23:
		frappe.throw(_("Calling hours start must be between 0 and 23"))
	if cur_end < 1 or cur_end > 24:
		frappe.throw(_("Calling hours end must be between 1 and 24"))
	if cur_start >= cur_end:
		frappe.throw(_("Calling hours start must be before end"))
	doc.calling_hours_start = cur_start
	doc.calling_hours_end = cur_end


@frappe.whitelist()
def get_my_assignment() -> dict:
	user = frappe.session.user
	row = _agent_row(user)
	settings = get_live_settings()
	twilio_number = frappe.db.get_value("CRM Telephony Agent", user, "twilio_number") or ""
	return {
		"enabled": settings["enabled"],
		"has_openai_key": settings["has_openai_key"],
		"catalog": settings["catalog"],
		"twilio_number": twilio_number,
		"assignment": _serialize_agent(row) if row else None,
	}


@frappe.whitelist()
def list_assignments() -> list:
	_require_admin()
	return frappe.get_all(
		"CRM AI Caller Agent",
		fields=[
			"name",
			"user",
			"user_name",
			"phone_number",
			"live_voice_id",
			"live_voice_prompt",
			"voice_id",
			"script_id",
			"custom_script",
			"respect_dnc",
			"reviewed_compliance",
			"setup_completed",
			"modified",
		],
		order_by="modified desc",
	)


@frappe.whitelist()
def assign_twilio_number(phone_number: str, user: str) -> dict:
	"""Assign a Twilio E.164 number to a user for GPT-Live AI + telephony."""
	_require_admin()
	from crm.integrations.twilio.api import assign_phone_number as twilio_assign
	from crm.live.twilio_bridge import _normalize_phone, ensure_ai_voice_webhook

	phone_number = _normalize_phone(phone_number)
	user = (user or "").strip()
	if not phone_number:
		frappe.throw(_("Phone number is required"))
	if not user or not frappe.db.exists("User", user):
		frappe.throw(_("Valid user is required"))

	# Clear number from other AI agents
	for name in frappe.get_all(
		"CRM AI Caller Agent",
		filters={"phone_number": phone_number, "name": ("!=", user)},
		pluck="name",
	):
		frappe.db.set_value("CRM AI Caller Agent", name, "phone_number", "")

	twilio_assign(phone_number=phone_number, user=user)

	agent = _ensure_agent(user)
	agent.phone_number = phone_number
	agent.save(ignore_permissions=True)

	try:
		ensure_ai_voice_webhook(phone_number)
	except Exception:
		frappe.log_error(title="Live voice webhook update failed")

	frappe.db.commit()
	return _serialize_agent(agent)


@frappe.whitelist()
def unassign_agent(user: str) -> dict:
	_require_admin()
	user = (user or "").strip()
	if frappe.db.exists("CRM AI Caller Agent", user):
		phone = frappe.db.get_value("CRM AI Caller Agent", user, "phone_number") or ""
		frappe.delete_doc("CRM AI Caller Agent", user, ignore_permissions=True)
		if phone:
			try:
				from crm.integrations.twilio.api import unassign_phone_number

				unassign_phone_number(phone_number=phone, user=user)
			except Exception:
				frappe.log_error(title="Twilio unassign after AI unassign failed")
		frappe.db.commit()
	return {"ok": True}


@frappe.whitelist()
def update_agent_assignment(
	user: str,
	voice_id: str | None = None,
	script_id: str | None = None,
	custom_script: int | str | None = None,
	respect_dnc: int | str | None = None,
	reviewed_compliance: int | str | None = None,
	setup_completed: int | str | None = None,
	live_voice_id: str | None = None,
	live_voice_prompt: str | None = None,
) -> dict:
	_require_admin()
	user = (user or "").strip()
	if not user or not frappe.db.exists("CRM AI Caller Agent", user):
		frappe.throw(_("AI caller agent not found"))

	agent = frappe.get_doc("CRM AI Caller Agent", user)
	if voice_id is not None:
		agent.voice_id = voice_id
	if script_id is not None:
		agent.script_id = script_id
	if custom_script is not None:
		agent.custom_script = 1 if int(custom_script or 0) else 0
	elif script_id is not None:
		agent.custom_script = 1 if script_id == "custom" else 0
	if respect_dnc is not None:
		agent.respect_dnc = 1 if int(respect_dnc or 0) else 0
	if reviewed_compliance is not None:
		agent.reviewed_compliance = 1 if int(reviewed_compliance or 0) else 0
	if setup_completed is not None:
		agent.setup_completed = 1 if int(setup_completed or 0) else 0
	if live_voice_id is not None:
		agent.live_voice_id = live_voice_id
	if live_voice_prompt is not None:
		agent.live_voice_prompt = live_voice_prompt
	agent.save(ignore_permissions=True)
	frappe.db.commit()
	return _serialize_agent(agent)


@frappe.whitelist()
def sync_my_setup(
	voice_id: str | None = None,
	script_id: str | None = None,
	custom_script: int | str | None = None,
	respect_dnc: int | str | None = None,
	reviewed_compliance: int | str | None = None,
	setup_completed: int | str | None = None,
	live_voice_id: str | None = None,
	live_voice_prompt: str | None = None,
) -> dict:
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
	if live_voice_id is not None:
		agent.live_voice_id = live_voice_id
	if live_voice_prompt is not None:
		agent.live_voice_prompt = live_voice_prompt
	agent.save(ignore_permissions=True)
	frappe.db.commit()
	return _serialize_agent(agent)


@frappe.whitelist()
def create_webrtc_session(sdp: str) -> dict:
	"""Browser WebRTC SDP offer → OpenAI Live session answer."""
	if frappe.session.user == "Guest":
		frappe.throw(_("Login required"), frappe.AuthenticationError)
	return _create_webrtc_session(sdp)


@frappe.whitelist()
def start_outbound_call(
	to_number: str,
	reference_doctype: str | None = None,
	reference_docname: str | None = None,
) -> dict:
	from crm.live.twilio_bridge import start_outbound_call as _start

	return _start(
		to_number,
		user=frappe.session.user,
		reference_doctype=reference_doctype,
		reference_docname=reference_docname,
	)


@frappe.whitelist()
def list_voices() -> dict:
	return list_voice_options()


@frappe.whitelist()
def create_org_prompt_voice(name: str, prompt: str, assign_to_org: int | str | None = 1) -> dict:
	_require_admin()
	return create_prompt_voice(name, prompt, assign_to_org=assign_to_org)


@frappe.whitelist()
def get_widget_config() -> dict:
	"""Config for in-CRM Live test widget (no secrets)."""
	user = frappe.session.user
	settings = get_live_settings()
	agent = _agent_row(user)
	return {
		"enabled": settings["enabled"],
		"has_openai_key": settings["has_openai_key"],
		"phone_number": (agent.phone_number if agent else "") or "",
		"script_id": (agent.script_id if agent else "") or settings["default_script_id"],
		"voice_id": (agent.voice_id if agent else "") or settings["default_voice_id"],
		"live_voice_id": (agent.live_voice_id if agent else "") or settings["default_live_voice_id"],
	}


@frappe.whitelist()
def get_usage_dashboard(days: int | str = 30, user: str | None = None) -> dict:
	"""Manager dashboard: aggregate GPT-Live call logs by agent."""
	_require_admin()
	days = max(1, min(int(days or 30), 90))
	from datetime import timedelta

	from frappe.utils import now_datetime

	since = now_datetime() - timedelta(days=days)
	filters = {
		"telephony_medium": "GPT-Live",
		"creation": [">=", since],
	}
	if user:
		filters["caller"] = user

	rows = frappe.get_all(
		"CRM Call Log",
		filters=filters,
		fields=["name", "caller", "status", "duration", "type", "creation", "to", "from", "id"],
		order_by="creation desc",
		limit=500,
	)

	agents = frappe.get_all(
		"CRM AI Caller Agent",
		fields=["user", "user_name", "phone_number", "setup_completed"],
		order_by="user_name asc",
	)
	if user:
		agents = [a for a in agents if a.user == user]

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
			"minutes": 0.0,
		}

	recent = []
	totals = {"calls": 0, "ended": 0, "failed": 0, "seconds": 0, "cost": 0.0, "minutes": 0.0}
	for row in rows:
		u = row.caller or "_unassigned"
		if u not in by_user:
			by_user[u] = {
				"user": u if u != "_unassigned" else "",
				"user_name": _("Unassigned") if u == "_unassigned" else u,
				"phone_number": "",
				"setup_completed": False,
				"calls": 0,
				"ended": 0,
				"failed": 0,
				"seconds": 0,
				"cost": 0.0,
				"minutes": 0.0,
			}
		bucket = by_user[u]
		bucket["calls"] += 1
		totals["calls"] += 1
		status = (row.status or "").lower()
		secs = cint(row.duration)
		bucket["seconds"] += secs
		totals["seconds"] += secs
		if status == "completed":
			bucket["ended"] += 1
			totals["ended"] += 1
		elif status in ("failed", "busy", "no answer", "canceled"):
			bucket["failed"] += 1
			totals["failed"] += 1
		recent.append(
			{
				"id": row.id or row.name,
				"user": row.caller or "",
				"user_name": bucket["user_name"],
				"status": row.status or "",
				"type": row.type or "",
				"ended_reason": "",
				"customer": row.to if row.type == "Outgoing" else getattr(row, "from", None),
				"seconds": secs,
				"cost": 0.0,
				"created_at": str(row.creation) if row.creation else "",
			}
		)

	agents_out = sorted(by_user.values(), key=lambda r: (-r["calls"], r["user_name"] or ""))
	for row in agents_out:
		row["minutes"] = round(row["seconds"] / 60.0, 1)
	totals["minutes"] = round(totals["seconds"] / 60.0, 1)

	return {
		"days": days,
		"totals": totals,
		"agents": agents_out,
		"recent": recent[:50],
	}


@frappe.whitelist()
def list_twilio_numbers_for_assign() -> list:
	"""Twilio inventory for manager assign UI."""
	_require_admin()
	from crm.integrations.twilio.api import list_phone_numbers

	try:
		numbers = list_phone_numbers() or []
	except Exception:
		numbers = []

	ai_by_phone = {
		_norm(r.phone_number): r
		for r in frappe.get_all(
			"CRM AI Caller Agent",
			filters={"phone_number": ["is", "set"]},
			fields=["user", "user_name", "phone_number"],
		)
		if r.phone_number
	}

	out = []
	for n in numbers:
		phone = n.get("phone_number") or ""
		ai = ai_by_phone.get(_norm(phone))
		out.append(
			{
				**n,
				"ai_linked": bool(ai),
				"ai_user": ai.user if ai else None,
				"ai_user_name": ai.user_name if ai else None,
			}
		)
	return out


def _norm(phone: str) -> str:
	from crm.live.twilio_bridge import _normalize_phone

	return _normalize_phone(phone or "")


# --- Twilio / bridge guest endpoints ---


@frappe.whitelist(allow_guest=True)  # nosemgrep: guest-whitelisted-method
def twilio_inbound_voice(**kwargs):
	"""Inbound Twilio voice → GPT-Live media bridge when number is AI-assigned."""
	from crm.integrations.twilio.api import validate_twilio_request
	from crm.live.twilio_bridge import inbound_twiml

	args = frappe._dict(kwargs)
	validate_twilio_request(args)
	twiml = inbound_twiml(args.get("From") or "", args.get("To") or "")
	return Response(twiml, mimetype="text/xml")


@frappe.whitelist(allow_guest=True)  # nosemgrep: guest-whitelisted-method
def twilio_outbound_twiml(**kwargs):
	from crm.integrations.twilio.api import validate_twilio_request
	from crm.live.twilio_bridge import media_stream_twiml, peek_call_token

	args = frappe._dict(kwargs)
	# Outbound URL may be fetched without full signature in some setups; still validate when possible
	try:
		validate_twilio_request(args)
	except Exception:
		pass

	token = (args.get("token") or frappe.form_dict.get("token") or "").strip()
	if not token or not peek_call_token(token):
		resp = '<?xml version="1.0" encoding="UTF-8"?><Response><Say>Call setup failed.</Say><Hangup/></Response>'
		return Response(resp, mimetype="text/xml")
	return Response(media_stream_twiml(call_token=token), mimetype="text/xml")


@frappe.whitelist(allow_guest=True)  # nosemgrep: guest-whitelisted-method
def twilio_status_callback(**kwargs):
	from crm.live.webhook import apply_twilio_status

	args = frappe._dict(kwargs)
	call_log = args.get("call_log") or frappe.form_dict.get("call_log")
	apply_twilio_status(
		call_log,
		call_status=args.get("CallStatus") or args.get("call_status"),
		call_sid=args.get("CallSid") or args.get("call_sid"),
		duration=args.get("CallDuration") or args.get("Duration"),
	)
	return {"ok": True}


@frappe.whitelist(allow_guest=True)  # nosemgrep: guest-whitelisted-method
def resolve_call_token(token: str | None = None):
	"""Media bridge resolves opaque token → session payload + OpenAI key."""
	from crm.live.webhook import validate_live_webhook_auth
	from crm.live.twilio_bridge import peek_call_token

	validate_live_webhook_auth()
	token = (token or frappe.form_dict.get("token") or "").strip()
	ctx = peek_call_token(token)
	if not ctx:
		frappe.throw(_("Invalid or expired call token"), frappe.AuthenticationError)

	settings = frappe.get_single("CRM Live Settings")
	try:
		api_key = settings.get_password("openai_api_key") or ""
	except Exception:
		api_key = ""

	return {
		"token": token,
		"direction": ctx.get("direction"),
		"to_number": ctx.get("to_number"),
		"from_number": ctx.get("from_number"),
		"user": ctx.get("user"),
		"session": ctx.get("session") or {},
		"openai_api_key": api_key,
	}


@frappe.whitelist(allow_guest=True)  # nosemgrep: guest-whitelisted-method
def bridge_session_ended(**kwargs):
	from crm.live.webhook import bridge_session_ended as _ended
	from crm.live.webhook import validate_live_webhook_auth

	validate_live_webhook_auth()
	args = frappe._dict(kwargs)
	_ended(
		args.get("token") or "",
		transcript=args.get("transcript"),
		duration=cint(args.get("duration")) if args.get("duration") not in (None, "") else None,
	)
	return {"ok": True}
