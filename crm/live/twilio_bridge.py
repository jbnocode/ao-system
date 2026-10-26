# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""Twilio ↔ GPT-Live: Media Stream bridge URL or OpenAI SIP outbound."""

from __future__ import annotations

import html
from urllib.parse import urlencode

import frappe
from frappe import _
from frappe.utils import cint, now_datetime

from crm.live.client import get_client
from crm.live.session import build_session_payload, resolve_agent_context


def _settings():
	return frappe.get_single("CRM Live Settings")


def _normalize_phone(number: str) -> str:
	n = (number or "").strip().replace(" ", "")
	if n and not n.startswith("+"):
		digits = "".join(c for c in n if c.isdigit())
		if len(digits) == 10:
			return f"+1{digits}"
		if len(digits) == 11 and digits.startswith("1"):
			return f"+{digits}"
	return n


def _twilio_client():
	from crm.integrations.twilio.twilio_handler import Twilio

	twilio = Twilio.connect()
	if not twilio:
		frappe.throw(_("Twilio is not enabled. Configure Telephony settings."))
	return twilio


def _agent_for_phone(phone: str):
	phone = _normalize_phone(phone)
	name = frappe.db.get_value("CRM AI Caller Agent", {"phone_number": phone}, "name")
	if name:
		return frappe.get_doc("CRM AI Caller Agent", name)
	# Also match telephony agent → user
	user = frappe.db.get_value("CRM Telephony Agent", {"twilio_number": phone}, "name")
	if user and frappe.db.exists("CRM AI Caller Agent", user):
		return frappe.get_doc("CRM AI Caller Agent", user)
	return None


def media_stream_twiml(*, call_token: str, bidirectional: bool = True) -> str:
	"""TwiML that connects the call to the AO Live media bridge."""
	settings = _settings()
	base = (settings.media_stream_url or "").strip()
	if not base:
		frappe.throw(_("Media Stream URL is not configured in AI Live settings."))

	# Allow ws/wss URL; append token query
	sep = "&" if "?" in base else "?"
	stream_url = f"{base}{sep}{urlencode({'token': call_token})}"

	safe_url = html.escape(stream_url, quote=True)
	return f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Connect>
    <Stream url="{safe_url}" />
  </Connect>
</Response>"""


def mint_call_token(ctx: dict, *, direction: str, to_number: str = "", from_number: str = "") -> str:
	"""Store short-lived call context in cache; return opaque token for the bridge."""
	import secrets

	token = secrets.token_urlsafe(24)
	payload = {
		"user": ctx["user"],
		"script_id": ctx["script_id"],
		"live_voice_id": ctx.get("live_voice_id") or "",
		"builtin_voice": ctx.get("builtin_voice") or "cedar",
		"voice_prompt": ctx.get("voice_prompt") or "",
		"direction": direction,
		"to_number": to_number,
		"from_number": from_number,
		"session": build_session_payload(ctx),
	}
	frappe.cache().set_value(f"crm_live_call:{token}", payload, expires_in_sec=60 * 30)
	return token


def peek_call_token(token: str) -> dict | None:
	if not token:
		return None
	return frappe.cache().get_value(f"crm_live_call:{token}")


def start_outbound_call(
	to_number: str,
	*,
	user: str | None = None,
	reference_doctype: str | None = None,
	reference_docname: str | None = None,
) -> dict:
	settings = _settings()
	if not settings.enabled:
		frappe.throw(_("AI Live is disabled."))

	ctx = resolve_agent_context(user)
	to_number = _normalize_phone(to_number)
	from_number = _normalize_phone(ctx.get("phone_number") or "")
	if not from_number:
		frappe.throw(_("No phone number assigned. Ask a manager to assign a Twilio number."))
	if not to_number:
		frappe.throw(_("Destination number is required"))

	if ctx.get("respect_dnc"):
		_assert_not_dnc(to_number)

	_assert_calling_hours(settings)

	# Prefer OpenAI SIP when trunk is fully configured
	sip_url = (settings.sip_provider_url or "").strip()
	sip_user = (settings.sip_username or "").strip()
	try:
		sip_pass = settings.get_password("sip_password") or ""
	except Exception:
		sip_pass = ""

	call_log_name = _create_call_log(
		from_number=from_number,
		to_number=to_number,
		user=ctx["user"],
		reference_doctype=reference_doctype,
		reference_docname=reference_docname,
		direction="Outbound",
	)

	if sip_url and sip_user and sip_pass:
		return _outbound_via_sip(
			ctx,
			to_number=to_number,
			from_number=from_number,
			sip_url=sip_url,
			sip_user=sip_user,
			sip_pass=sip_pass,
			call_log_name=call_log_name,
		)

	return _outbound_via_twilio_stream(
		ctx,
		to_number=to_number,
		from_number=from_number,
		call_log_name=call_log_name,
	)


def _outbound_via_sip(
	ctx,
	*,
	to_number,
	from_number,
	sip_url,
	sip_user,
	sip_pass,
	call_log_name,
) -> dict:
	client = get_client()
	session = build_session_payload(ctx)
	result = client.create_sip_session(
		session,
		{
			"type": "sip",
			"destination": to_number,
			"trunk": {
				"provider_url": sip_url,
				"auth": {"type": "digest", "username": sip_user, "password": sip_pass},
				"caller_number": from_number,
			},
		},
	)
	session_id = (result.get("session") or {}).get("id") or ""
	if session_id:
		frappe.db.set_value("CRM Call Log", call_log_name, "id", session_id)
	frappe.db.commit()
	return {
		"ok": True,
		"mode": "sip",
		"session_id": session_id,
		"call_log": call_log_name,
		"to": to_number,
		"from": from_number,
	}


def _outbound_via_twilio_stream(ctx, *, to_number, from_number, call_log_name) -> dict:
	token = mint_call_token(ctx, direction="outbound", to_number=to_number, from_number=from_number)
	twilio = _twilio_client()
	# Absolute HTTPS URL Twilio will fetch for TwiML
	twiml_url = (
		f"{frappe.utils.get_url().rstrip('/')}"
		f"/api/method/crm.live.api.twilio_outbound_twiml?token={token}"
	)
	status_url = (
		f"{frappe.utils.get_url().rstrip('/')}"
		f"/api/method/crm.live.api.twilio_status_callback?call_log={call_log_name}"
	)

	call = twilio.client.calls.create(
		to=to_number,
		from_=from_number,
		url=twiml_url,
		method="POST",
		status_callback=status_url,
		status_callback_method="POST",
		status_callback_event=["initiated", "ringing", "answered", "completed"],
	)
	sid = getattr(call, "sid", None) or ""
	if sid:
		frappe.db.set_value("CRM Call Log", call_log_name, {"id": sid, "telephony_medium": "GPT-Live"})
	frappe.db.commit()
	return {
		"ok": True,
		"mode": "twilio_stream",
		"twilio_sid": sid,
		"call_log": call_log_name,
		"token": token,
		"to": to_number,
		"from": from_number,
	}


def inbound_twiml(from_number: str, to_number: str) -> str:
	"""Inbound call on an AI-assigned Twilio number → Live media bridge."""
	to_number = _normalize_phone(to_number)
	agent = _agent_for_phone(to_number)
	if not agent:
		return """<?xml version="1.0" encoding="UTF-8"?>
<Response><Say>This number is not configured for AI calling.</Say><Hangup/></Response>"""

	ctx = resolve_agent_context(agent.user)
	token = mint_call_token(
		ctx,
		direction="inbound",
		to_number=to_number,
		from_number=_normalize_phone(from_number),
	)
	_create_call_log(
		from_number=_normalize_phone(from_number),
		to_number=to_number,
		user=agent.user,
		direction="Inbound",
	)
	return media_stream_twiml(call_token=token)


def ensure_ai_voice_webhook(phone_number: str):
	"""Point Twilio inbound voice for this number at the Live inbound handler."""
	from crm.integrations.twilio.twilio_handler import Twilio

	twilio = Twilio.connect()
	if not twilio:
		return
	voice_url = (
		f"{frappe.utils.get_url().rstrip('/')}/api/method/crm.live.api.twilio_inbound_voice"
	)
	phone_number = _normalize_phone(phone_number)
	for n in twilio.twilio_client.incoming_phone_numbers.list(phone_number=phone_number, limit=5):
		n.update(voice_method="POST", voice_url=voice_url)


def _create_call_log(
	*,
	from_number: str,
	to_number: str,
	user: str,
	direction: str = "Outbound",
	reference_doctype: str | None = None,
	reference_docname: str | None = None,
) -> str:
	call_type = "Incoming" if direction == "Inbound" else "Outgoing"
	doc = frappe.get_doc(
		{
			"doctype": "CRM Call Log",
			"from": from_number or "Unknown",
			"to": to_number or "Unknown",
			"type": call_type,
			"status": "Queued",
			"medium": "GPT-Live",
			"telephony_medium": "GPT-Live",
			"caller": user if call_type == "Outgoing" else "",
			"receiver": user if call_type == "Incoming" else "",
			"start_time": now_datetime(),
			"reference_doctype": reference_doctype,
			"reference_docname": reference_docname,
		}
	)
	_link_call_log(to_number if call_type == "Outgoing" else from_number, doc, reference_doctype, reference_docname)
	doc.insert(ignore_permissions=True)
	return doc.name


def _link_call_log(contact_number, call_log, reference_doctype, reference_docname):
	if reference_doctype and reference_docname:
		call_log.reference_doctype = reference_doctype
		call_log.reference_docname = reference_docname
		return
	if not contact_number:
		return
	variants = _phone_match_variants(contact_number)
	if not variants:
		return
	lead = frappe.db.get_value("CRM Lead", {"mobile_no": ["in", variants], "converted": 0}, "name")
	if not lead:
		lead = frappe.db.get_value("CRM Lead", {"phone": ["in", variants], "converted": 0}, "name")
	if lead:
		call_log.reference_doctype = "CRM Lead"
		call_log.reference_docname = lead
		return
	deal = frappe.db.get_value("CRM Deal", {"mobile_no": ["in", variants]}, "name")
	if deal:
		call_log.reference_doctype = "CRM Deal"
		call_log.reference_docname = deal


def _assert_not_dnc(number: str):
	variants = _phone_match_variants(number)
	if not variants:
		return
	leads = frappe.get_all(
		"CRM Lead",
		filters={"mobile_no": ["in", variants], "converted": 0},
		fields=["name", "status", "communication_status", "lost_reason"],
		limit=20,
	)
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


def _assert_calling_hours(settings):
	from datetime import datetime

	try:
		import pytz

		tz_name = frappe.utils.get_system_timezone()
		tz = pytz.timezone(tz_name)
		hour = datetime.now(tz).hour
	except Exception:
		hour = now_datetime().hour

	start = cint(settings.calling_hours_start or 8)
	end = cint(settings.calling_hours_end or 21)
	if start < end:
		ok = start <= hour < end
	else:
		ok = hour >= start or hour < end
	if not ok:
		frappe.throw(
			_("Outbound AI calls are only allowed between {0}:00 and {1}:00 ({2}).").format(
				start, end, frappe.utils.get_system_timezone()
			)
		)
