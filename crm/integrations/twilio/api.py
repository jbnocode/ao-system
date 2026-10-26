from __future__ import annotations

import json

import frappe
from frappe import _
from twilio.twiml.voice_response import VoiceResponse
from werkzeug.wrappers import Response

from crm.integrations.api import get_contact_by_phone_number

from .twilio_handler import IncomingCall, Twilio, TwilioCallDetails


def validate_twilio_request(args, require_application_sid: bool = False):
	twilio = Twilio.connect()
	if not twilio:
		frappe.throw(_("Twilio configuration is missing"), frappe.PermissionError)

	account_sid = frappe.utils.cstr(args.get("AccountSid"))
	if not account_sid or account_sid != frappe.utils.cstr(twilio.account_sid):
		frappe.throw(_("Invalid Twilio account"), frappe.PermissionError)

	if require_application_sid:
		application_sid = frappe.utils.cstr(args.get("ApplicationSid"))
		if not application_sid or application_sid != frappe.utils.cstr(twilio.application_sid):
			frappe.throw(_("Invalid Twilio application"), frappe.PermissionError)

	return twilio


@frappe.whitelist()
def is_enabled():
	return frappe.db.get_single_value("CRM Twilio Settings", "enabled")


def _require_phone_manager():
	"""Assign / list numbers — System Manager or Sales Manager."""
	frappe.only_for(("System Manager", "Sales Manager"))


def _require_phone_admin():
	"""Connect Twilio / buy numbers — System Manager only."""
	frappe.only_for("System Manager")


def _require_twilio():
	twilio = Twilio.connect()
	if not twilio:
		frappe.throw(_("Twilio is not enabled. Configure it in Telephony settings."), frappe.ValidationError)
	return twilio


def _normalize_phone(phone_number: str) -> str:
	phone_number = "".join(c for c in (phone_number or "") if c.isdigit() or c == "+")
	if phone_number and not phone_number.startswith("+"):
		phone_number = f"+{phone_number}"
	return phone_number


def _assignees_by_number() -> dict[str, dict]:
	rows = frappe.get_all(
		"CRM Telephony Agent",
		filters={"twilio_number": ("is", "set")},
		fields=["name", "user", "user_name", "twilio_number"],
	)
	by_number = {}
	for row in rows:
		number = _normalize_phone(row.twilio_number)
		if not number:
			continue
		by_number.setdefault(number, []).append(
			{"user": row.user or row.name, "user_name": row.user_name or row.user or row.name}
		)
	return by_number


@frappe.whitelist()
def list_phone_numbers():
	"""List Twilio numbers on the org account with CRM assignees."""
	_require_phone_manager()
	twilio = Twilio.connect()
	if not twilio:
		return []
	assignees = _assignees_by_number()
	numbers = []
	for n in twilio.list_incoming_phone_numbers():
		phone = _normalize_phone(n["phone_number"])
		assigned = assignees.get(phone) or []
		numbers.append(
			{
				**n,
				"phone_number": phone,
				"assigned_to": assigned[0] if assigned else None,
				"assignees": assigned,
			}
		)
	return numbers


@frappe.whitelist()
def search_available_numbers(country_code: str = "US", area_code: str | None = None, limit: int = 20):
	"""Search Twilio for numbers available to purchase (managers; Twilio must already be connected)."""
	_require_phone_manager()
	twilio = _require_twilio()
	return twilio.search_available_numbers(country_code=country_code, area_code=area_code, limit=limit)


@frappe.whitelist()
def purchase_phone_number(phone_number: str, friendly_name: str | None = None, assign_to: str | None = None):
	"""Buy a Twilio number and optionally assign it to a user (managers; Twilio must already be connected)."""
	_require_phone_manager()
	return _purchase_and_maybe_assign(phone_number, friendly_name=friendly_name, assign_to=assign_to)


@frappe.whitelist()
def request_or_acquire_phone_number(
	country_code: str = "US",
	area_code: str | None = None,
	assign_to: str | None = None,
	phone_number: str | None = None,
	notes: str | None = None,
) -> dict:
	"""Always create a Requested record; auto-fulfill when Twilio works, else leave Requested."""
	_require_phone_manager()
	assign_to = assign_to or frappe.session.user
	if not frappe.db.exists("User", assign_to):
		frappe.throw(_("Valid user is required"))

	country_code = (country_code or "US").strip().upper() or "US"
	area_code = (area_code or "").strip() or None
	notes = (notes or "").strip() or None

	req = frappe.get_doc(
		{
			"doctype": "CRM Phone Number Request",
			"status": "Requested",
			"requested_by": frappe.session.user,
			"assign_to": assign_to,
			"country_code": country_code,
			"area_code": area_code or "",
			"notes": notes,
		}
	)
	req.insert(ignore_permissions=True)
	frappe.db.commit()

	twilio = Twilio.connect()
	if not twilio:
		return {
			"status": "Requested",
			"instant": False,
			"request": req.name,
			"assign_to": assign_to,
			"message": _("Number requested. It will be fulfilled when Twilio is available."),
		}

	try:
		result = _acquire_instant(
			twilio,
			country_code=country_code,
			area_code=area_code,
			assign_to=assign_to,
			phone_number=phone_number,
		)
		req.status = "Fulfilled"
		req.phone_number = result["phone_number"]
		req.fulfilled_on = frappe.utils.now_datetime()
		req.error_message = ""
		req.save(ignore_permissions=True)
		frappe.db.commit()
		return {
			"status": "Fulfilled",
			"instant": True,
			"phone_number": result["phone_number"],
			"assign_to": assign_to,
			"request": req.name,
			"message": _("Number {0} assigned.").format(result["phone_number"]),
		}
	except Exception as exc:
		frappe.log_error(title=_("Phone number request fulfill failed"))
		req.status = "Requested"
		req.error_message = str(exc)[:300]
		req.save(ignore_permissions=True)
		frappe.db.commit()
		return {
			"status": "Requested",
			"instant": False,
			"request": req.name,
			"assign_to": assign_to,
			"message": _("Number requested. Fulfillment will retry when Twilio is ready."),
		}


@frappe.whitelist()
def list_phone_number_requests(status: str | None = None) -> list:
	"""Pending/recent number requests for managers."""
	_require_phone_manager()
	filters = {}
	if status:
		filters["status"] = status
	# Sales Managers see all pending (team allocation); System Manager too
	return frappe.get_all(
		"CRM Phone Number Request",
		filters=filters or None,
		fields=[
			"name",
			"status",
			"requested_by",
			"requested_by_name",
			"assign_to",
			"assign_to_name",
			"country_code",
			"area_code",
			"phone_number",
			"notes",
			"creation",
			"fulfilled_on",
			"error_message",
		],
		order_by="creation desc",
		limit_page_length=50,
	)


@frappe.whitelist()
def fulfill_phone_number_request(name: str, phone_number: str | None = None) -> dict:
	"""Buy+assign for a pending request (System Manager, or any manager once Twilio is up)."""
	_require_phone_manager()
	if not name or not frappe.db.exists("CRM Phone Number Request", name):
		frappe.throw(_("Request not found"))
	req = frappe.get_doc("CRM Phone Number Request", name)
	if req.status == "Fulfilled" and req.phone_number:
		return {"status": "Fulfilled", "phone_number": req.phone_number, "request": req.name}

	twilio = Twilio.connect()
	if not twilio:
		frappe.throw(_("Twilio is not connected. Connect it in Telephony settings first."))

	try:
		result = _acquire_instant(
			twilio,
			country_code=req.country_code or "US",
			area_code=req.area_code or None,
			assign_to=req.assign_to,
			phone_number=phone_number,
		)
		req.status = "Fulfilled"
		req.phone_number = result["phone_number"]
		req.fulfilled_on = frappe.utils.now_datetime()
		req.error_message = ""
		req.save(ignore_permissions=True)
		frappe.db.commit()
		return {
			"status": "Fulfilled",
			"instant": True,
			"phone_number": result["phone_number"],
			"assign_to": req.assign_to,
			"request": req.name,
		}
	except Exception as exc:
		req.status = "Requested"
		req.error_message = str(exc)[:300]
		req.save(ignore_permissions=True)
		frappe.db.commit()
		frappe.throw(_("Could not fulfill request: {0}").format(str(exc)[:200]))


def _purchase_and_maybe_assign(
	phone_number: str, friendly_name: str | None = None, assign_to: str | None = None
) -> dict:
	twilio = _require_twilio()
	phone_number = _normalize_phone(phone_number)
	result = twilio.purchase_phone_number(phone_number, friendly_name=friendly_name)
	purchased = _normalize_phone(result.get("phone_number") or phone_number)
	if assign_to:
		assign_phone_number(phone_number=purchased, user=assign_to)
		result["assigned_to"] = assign_to
	result["phone_number"] = purchased
	return result


def _acquire_instant(
	twilio,
	country_code: str,
	area_code: str | None,
	assign_to: str,
	phone_number: str | None = None,
) -> dict:
	chosen = _normalize_phone(phone_number or "")
	if not chosen:
		available = twilio.search_available_numbers(
			country_code=country_code, area_code=area_code, limit=5
		)
		if not available:
			frappe.throw(
				_("No Twilio numbers available for {0}{1}. Try another area code.").format(
					country_code, f" / {area_code}" if area_code else ""
				)
			)
		chosen = _normalize_phone(available[0].get("phone_number") or "")
	if not chosen:
		frappe.throw(_("Could not pick a phone number to purchase"))

	friendly = f"AO {assign_to}"
	result = twilio.purchase_phone_number(chosen, friendly_name=friendly)
	purchased = _normalize_phone(result.get("phone_number") or chosen)
	assign_phone_number(phone_number=purchased, user=assign_to)
	return {"phone_number": purchased, "assigned_to": assign_to, **result}


@frappe.whitelist()
def assign_phone_number(phone_number: str, user: str):
	"""Assign a Twilio number to a CRM Telephony Agent (one primary assignee)."""
	_require_phone_manager()
	phone_number = _normalize_phone(phone_number)
	if not phone_number:
		frappe.throw(_("Phone number is required"))
	if not user or not frappe.db.exists("User", user):
		frappe.throw(_("Valid user is required"))

	# Clear this number from any other agents
	for name in frappe.get_all(
		"CRM Telephony Agent",
		filters={"twilio_number": phone_number, "name": ("!=", user)},
		pluck="name",
	):
		frappe.db.set_value("CRM Telephony Agent", name, "twilio_number", "")

	# Also clear by normalized match (legacy formatting)
	for row in frappe.get_all(
		"CRM Telephony Agent",
		filters={"twilio_number": ("is", "set"), "name": ("!=", user)},
		fields=["name", "twilio_number"],
	):
		if _normalize_phone(row.twilio_number) == phone_number:
			frappe.db.set_value("CRM Telephony Agent", row.name, "twilio_number", "")

	if frappe.db.exists("CRM Telephony Agent", user):
		frappe.db.set_value("CRM Telephony Agent", user, "twilio_number", phone_number)
	else:
		doc = frappe.get_doc(
			{
				"doctype": "CRM Telephony Agent",
				"user": user,
				"twilio_number": phone_number,
				"default_medium": "Twilio",
			}
		)
		doc.insert(ignore_permissions=True)

	frappe.db.commit()
	return {"phone_number": phone_number, "user": user}


@frappe.whitelist()
def unassign_phone_number(phone_number: str, user: str | None = None):
	"""Clear CRM assignment for a number (keeps number on Twilio account)."""
	_require_phone_manager()
	phone_number = _normalize_phone(phone_number)
	if not phone_number:
		frappe.throw(_("Phone number is required"))

	filters = {}
	if user:
		filters["name"] = user

	cleared = []
	for row in frappe.get_all(
		"CRM Telephony Agent",
		filters=filters or None,
		fields=["name", "twilio_number"],
	):
		if _normalize_phone(row.twilio_number) == phone_number:
			frappe.db.set_value("CRM Telephony Agent", row.name, "twilio_number", "")
			cleared.append(row.name)

	frappe.db.commit()
	return {"phone_number": phone_number, "cleared": cleared}


@frappe.whitelist()
def generate_access_token():
	"""Returns access token that is required to authenticate Twilio Client SDK."""
	twilio = Twilio.connect()
	if not twilio:
		return {}

	from_number = frappe.db.get_value("CRM Telephony Agent", frappe.session.user, "twilio_number")
	if not from_number:
		return {
			"ok": False,
			"error": "caller_phone_identity_missing",
			"detail": "Phone number is not mapped to the caller",
		}

	token = twilio.generate_voice_access_token(identity=frappe.session.user)
	return {"token": frappe.safe_decode(token)}


# webhook authenticity is enforced by validate_twilio_request(); guest access itself is unchanged
@frappe.whitelist(allow_guest=True)  # nosemgrep: guest-whitelisted-method
def voice(**kwargs):
	"""This is a webhook called by twilio to get instructions when the voice call request comes to twilio server."""

	def _get_caller_number(caller):
		identity = caller.replace("client:", "").strip()
		user = Twilio.emailid_from_identity(identity)
		return frappe.db.get_value("CRM Telephony Agent", user, "twilio_number")

	args = frappe._dict(kwargs)
	twilio = validate_twilio_request(args, require_application_sid=True)

	# Generate TwiML instructions to make a call
	from_number = _get_caller_number(args.Caller)
	if not from_number:
		resp = VoiceResponse()
		resp.say(_("Your account is not configured with a phone number. Please contact your administrator."))
		return Response(resp.to_xml(), mimetype="text/xml")

	call_details = TwilioCallDetails(args, call_from=from_number)
	try:
		create_call_log(call_details)
	except Exception:
		frappe.db.rollback()
		frappe.log_error(title="Error while creating Twilio call log")
		frappe.db.commit()
		return Response(_call_failed_response().to_xml(), mimetype="text/xml")

	resp = twilio.generate_twilio_dial_response(from_number, args.To)
	return Response(resp.to_xml(), mimetype="text/xml")


# webhook authenticity is enforced by validate_twilio_request(); guest access itself is unchanged
@frappe.whitelist(allow_guest=True)  # nosemgrep: guest-whitelisted-method
def twilio_incoming_call_handler(**kwargs):
	args = frappe._dict(kwargs)
	validate_twilio_request(args)

	# GPT-Live path when the dialed number is assigned to an AI Caller Agent
	try:
		if frappe.db.get_single_value("CRM Live Settings", "enabled"):
			from crm.live.twilio_bridge import _agent_for_phone, inbound_twiml

			if _agent_for_phone(args.To):
				return Response(inbound_twiml(args.From, args.To), mimetype="text/xml")
	except Exception:
		frappe.log_error(title="Live inbound routing check failed")

	call_details = TwilioCallDetails(args)
	try:
		create_call_log(call_details)
	except Exception:
		frappe.db.rollback()
		frappe.log_error(title="Error while creating Twilio call log")
		frappe.db.commit()
		return Response(_call_failed_response().to_xml(), mimetype="text/xml")

	resp = IncomingCall(args.From, args.To).process()
	return Response(resp.to_xml(), mimetype="text/xml")


@frappe.whitelist(allow_guest=True)  # nosemgrep: guest-whitelisted-method
def twilio_incoming_sms_handler(**kwargs):
	"""Inbound SMS from Twilio — persist CRM SMS Message and ack with empty TwiML."""
	from twilio.twiml.messaging_response import MessagingResponse

	args = frappe._dict(kwargs)
	validate_twilio_request(args)

	from crm.api.sms import _normalize_phone

	message_sid = frappe.utils.cstr(args.get("MessageSid") or args.get("SmsSid"))
	body = frappe.utils.cstr(args.get("Body") or "")
	from_number = _normalize_phone(frappe.utils.cstr(args.get("From")))
	to_number = _normalize_phone(frappe.utils.cstr(args.get("To")))

	if message_sid and frappe.db.exists("CRM SMS Message", {"twilio_sid": message_sid}):
		return Response(MessagingResponse().to_xml(), mimetype="text/xml")

	try:
		doc = frappe.get_doc(
			{
				"doctype": "CRM SMS Message",
				"from": from_number,
				"to": to_number,
				"from_number": to_number,
				"message": body or _("(empty message)"),
				"type": "Incoming",
				"status": "Received",
				"twilio_sid": message_sid or None,
			}
		)
		doc.insert(ignore_permissions=True)
		frappe.db.commit()
	except Exception:
		frappe.db.rollback()
		frappe.log_error(title="Error while creating Twilio SMS message")
		frappe.db.commit()

	return Response(MessagingResponse().to_xml(), mimetype="text/xml")


@frappe.whitelist(allow_guest=True)  # nosemgrep: guest-whitelisted-method
def twilio_sms_status_handler(**kwargs):
	"""Twilio status callback — update CRM SMS Message status by SID."""
	from twilio.twiml.messaging_response import MessagingResponse

	from crm.api.sms import map_twilio_status

	args = frappe._dict(kwargs)
	validate_twilio_request(args)

	message_sid = frappe.utils.cstr(args.get("MessageSid") or args.get("SmsSid"))
	message_status = frappe.utils.cstr(args.get("MessageStatus") or args.get("SmsStatus"))
	if message_sid and frappe.db.exists("CRM SMS Message", {"twilio_sid": message_sid}):
		try:
			name = frappe.db.get_value("CRM SMS Message", {"twilio_sid": message_sid}, "name")
			frappe.db.set_value(
				"CRM SMS Message",
				name,
				"status",
				map_twilio_status(message_status),
				update_modified=True,
			)
			frappe.db.commit()
		except Exception:
			frappe.log_error(title="Error while updating Twilio SMS status")
			frappe.db.commit()

	return Response(MessagingResponse().to_xml(), mimetype="text/xml")


@frappe.whitelist()
def configure_sms_webhooks(phone_number_sid: str | None = None):
	"""Point SMS webhooks at CRM for existing Twilio numbers (System Manager)."""
	_require_phone_admin()
	twilio = _require_twilio()
	return {"updated": twilio.configure_sms_webhooks(phone_number_sid)}


def _call_failed_response():
	resp = VoiceResponse()
	resp.say(_("We're unable to connect your call right now. Please try again later."))
	return resp


def create_call_log(call_details: TwilioCallDetails):
	details = call_details.to_dict()

	call_log = frappe.get_doc({**details, "doctype": "CRM Call Log", "telephony_medium": "Twilio"})

	# link call log with lead/deal
	contact_number = details.get("from") if details.get("type") == "Incoming" else details.get("to")
	link(contact_number, call_log)

	call_log.save(ignore_permissions=True)
	frappe.db.commit()
	return call_log


def link(contact_number, call_log):
	contact = get_contact_by_phone_number(contact_number)
	if contact.get("name"):
		doctype = "Contact"
		docname = contact.get("name")
		if contact.get("lead"):
			doctype = "CRM Lead"
			docname = contact.get("lead")
		elif contact.get("deal"):
			doctype = "CRM Deal"
			docname = contact.get("deal")
		call_log.link_with_reference_doc(doctype, docname)


def update_call_log(call_sid, status=None):
	"""Update call log status."""
	twilio = Twilio.connect()
	if not (twilio and frappe.db.exists("CRM Call Log", call_sid)):
		return

	try:
		call_details = twilio.get_call_info(call_sid)
		call_log = frappe.get_doc("CRM Call Log", call_sid)
		call_log.status = TwilioCallDetails.get_call_status(status or call_details.status)
		call_log.duration = call_details.duration
		call_log.start_time = get_datetime_from_timestamp(call_details.start_time)
		call_log.end_time = get_datetime_from_timestamp(call_details.end_time)
		call_log.save(ignore_permissions=True)
		frappe.db.commit()
		return call_log
	except Exception:
		frappe.log_error(title="Error while updating call record")
		frappe.db.commit()


def get_twilio_settings():
	return frappe.get_single("CRM Twilio Settings")


@frappe.whitelist(allow_guest=True)
def update_recording_info(**kwargs):
	args = frappe._dict(kwargs)
	validate_twilio_request(args)

	recording_url = args.RecordingUrl
	call_sid = args.CallSid
	call_log = update_call_log(call_sid)
	if not call_log:
		frappe.throw(_("Call log not found"), frappe.DoesNotExistError)

	try:
		frappe.db.set_value("CRM Call Log", call_sid, "recording_url", recording_url)
		frappe.db.commit()
	except Exception as exc:
		frappe.log_error(title=_("Failed to capture Twilio recording"))
		raise exc


@frappe.whitelist(allow_guest=True)
def update_call_status_info(**kwargs):
	args = frappe._dict(kwargs)
	validate_twilio_request(args)

	parent_call_sid = args.ParentCallSid
	call_log = update_call_log(parent_call_sid, status=args.CallStatus)
	if not call_log:
		frappe.throw(_("Call log not found"), frappe.DoesNotExistError)

	call_info = {
		"ParentCallSid": args.ParentCallSid,
		"CallSid": args.CallSid,
		"CallStatus": args.CallStatus,
		"CallDuration": args.CallDuration,
		"From": args.From,
		"To": args.To,
	}

	try:
		client = Twilio.get_twilio_client()
		client.calls(args.ParentCallSid).user_defined_messages.create(content=json.dumps(call_info))
	except Exception as exc:
		frappe.log_error(title=_("Failed to update Twilio call status"))
		raise exc


def get_datetime_from_timestamp(timestamp):
	from datetime import datetime
	from zoneinfo import ZoneInfo

	if not timestamp:
		return None

	datetime_utc_tz_str = timestamp.strftime("%Y-%m-%d %H:%M:%S%z")
	datetime_utc_tz = datetime.strptime(datetime_utc_tz_str, "%Y-%m-%d %H:%M:%S%z")
	system_timezone = frappe.utils.get_system_timezone()
	converted_datetime = datetime_utc_tz.astimezone(ZoneInfo(system_timezone))
	return frappe.utils.format_datetime(converted_datetime, "yyyy-MM-dd HH:mm:ss")
