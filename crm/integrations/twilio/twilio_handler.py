from __future__ import annotations

import frappe
from frappe import _
from frappe.utils.password import get_decrypted_password
from twilio.jwt.access_token import AccessToken
from twilio.jwt.access_token.grants import VoiceGrant
from twilio.rest import Client as TwilioClient
from twilio.twiml.voice_response import Dial, VoiceResponse

from .utils import get_public_url, merge_dicts


def _capability_enabled(capabilities, key: str) -> bool:
	if not capabilities:
		return False
	if isinstance(capabilities, dict):
		return bool(capabilities.get(key))
	return bool(getattr(capabilities, key, False))


class Twilio:
	"""Twilio connector over TwilioClient."""

	def __init__(self, settings):
		"""
		:param settings: `CRM Twilio Settings` doctype
		"""
		self.settings = settings
		self.account_sid = settings.account_sid
		self.application_sid = settings.twiml_sid
		self.api_key = settings.api_key
		self.api_secret = settings.get_password("api_secret")
		self.twilio_client = self.get_twilio_client()

	@classmethod
	def connect(cls):
		"""Read CRM Twilio Settings and return a configured Twilio instance, or None if not enabled."""
		settings = frappe.get_doc("CRM Twilio Settings")
		if not (settings and settings.enabled):
			return
		return Twilio(settings=settings)

	def get_phone_numbers(self):
		"""Get account's twilio phone numbers (E.164 strings)."""
		return [n["phone_number"] for n in self.list_incoming_phone_numbers()]

	def list_incoming_phone_numbers(self):
		"""List owned Twilio numbers with metadata."""
		numbers = self.twilio_client.incoming_phone_numbers.list(limit=200)
		return [
			{
				"sid": n.sid,
				"phone_number": n.phone_number,
				"friendly_name": n.friendly_name or n.phone_number,
				"capabilities": {
					"voice": _capability_enabled(n.capabilities, "voice"),
					"sms": _capability_enabled(n.capabilities, "sms"),
				},
			}
			for n in numbers
		]

	def search_available_numbers(self, country_code: str = "US", area_code: str | None = None, limit: int = 20):
		"""Search Twilio inventory for local numbers available to buy."""
		country_code = (country_code or "US").upper().strip()
		limit = min(max(int(limit or 20), 1), 50)
		params = {"limit": limit, "voice_enabled": True}
		if area_code:
			params["area_code"] = str(area_code).strip()

		try:
			available = self.twilio_client.available_phone_numbers(country_code).local.list(**params)
		except Exception as exc:
			frappe.throw(_("Could not search Twilio numbers: {0}").format(str(exc)))

		return [
			{
				"phone_number": n.phone_number,
				"friendly_name": n.friendly_name or n.phone_number,
				"locality": getattr(n, "locality", None) or "",
				"region": getattr(n, "region", None) or "",
				"iso_country": getattr(n, "iso_country", None) or country_code,
				"capabilities": {
					"voice": _capability_enabled(n.capabilities, "voice"),
					"sms": _capability_enabled(n.capabilities, "sms"),
				},
			}
			for n in available
		]

	def get_incoming_voice_url(self):
		return get_public_url("/api/method/crm.integrations.twilio.api.twilio_incoming_call_handler")

	def get_incoming_sms_url(self):
		return get_public_url("/api/method/crm.integrations.twilio.api.twilio_incoming_sms_handler")

	def get_incoming_sms_status_url(self):
		return get_public_url("/api/method/crm.integrations.twilio.api.twilio_sms_status_handler")

	def purchase_phone_number(self, phone_number: str, friendly_name: str | None = None):
		"""Buy a number and point inbound voice + SMS at CRM webhooks / TwiML app."""
		phone_number = (phone_number or "").strip()
		if not phone_number:
			frappe.throw(_("Phone number is required"))

		# Inbound voice must hit twilio_incoming_call_handler — do not set
		# voice_application_sid here (that app URL is for Client SDK outbound).
		create_kwargs = {
			"phone_number": phone_number,
			"voice_method": "POST",
			"voice_url": self.get_incoming_voice_url(),
			"sms_method": "POST",
			"sms_url": self.get_incoming_sms_url(),
		}
		if friendly_name:
			create_kwargs["friendly_name"] = friendly_name

		try:
			number = self.twilio_client.incoming_phone_numbers.create(**create_kwargs)
		except Exception as exc:
			frappe.throw(_("Could not purchase Twilio number: {0}").format(str(exc)))

		return {
			"sid": number.sid,
			"phone_number": number.phone_number,
			"friendly_name": number.friendly_name or number.phone_number,
		}

	def configure_sms_webhooks(self, phone_number_sid: str | None = None):
		"""Point SMS webhooks at CRM for one number (or all owned numbers)."""
		sms_url = self.get_incoming_sms_url()
		updated = []
		numbers = (
			[self.twilio_client.incoming_phone_numbers(phone_number_sid).fetch()]
			if phone_number_sid
			else self.twilio_client.incoming_phone_numbers.list(limit=200)
		)
		for number in numbers:
			try:
				number.update(sms_method="POST", sms_url=sms_url)
				updated.append(number.phone_number)
			except Exception:
				frappe.log_error(
					title=_("Failed to set SMS webhook for {0}").format(number.phone_number)
				)
		return updated

	def generate_voice_access_token(self, identity: str, ttl=60 * 60):
		"""Generates a token required to make voice calls from the browser."""
		# identity is used by twilio to identify the user uniqueness at browser(or any endpoints).
		identity = self.safe_identity(identity)

		# Create access token with credentials
		token = AccessToken(self.account_sid, self.api_key, self.api_secret, identity=identity, ttl=ttl)

		# Create a Voice grant and add to token
		voice_grant = VoiceGrant(
			outgoing_application_sid=self.application_sid,
			incoming_allow=True,  # Allow incoming calls
		)
		token.add_grant(voice_grant)
		return token.to_jwt()

	@classmethod
	def safe_identity(cls, identity: str):
		"""Create a safe identity by replacing unsupported special characters `@` with (at)).
		Twilio Client JS fails to make a call connection if identity has special characters like @, [, / etc)
		https://www.twilio.com/docs/voice/client/errors (#31105)
		"""
		return identity.replace("@", "(at)")

	@classmethod
	def emailid_from_identity(cls, identity: str):
		"""Convert safe identity string into emailID."""
		return identity.replace("(at)", "@")

	def get_recording_status_callback_url(self):
		url_path = "/api/method/crm.integrations.twilio.api.update_recording_info"
		return get_public_url(url_path)

	def get_update_call_status_callback_url(self):
		url_path = "/api/method/crm.integrations.twilio.api.update_call_status_info"
		return get_public_url(url_path)

	def generate_twilio_dial_response(self, from_number: str, to_number: str):
		"""Generates voice call instructions to forward the call to agents Phone."""
		resp = VoiceResponse()
		dial = Dial(
			caller_id=from_number,
			record=self.settings.record_calls,
			recording_status_callback=self.get_recording_status_callback_url(),
			recording_status_callback_event="completed",
		)
		dial.number(
			to_number,
			status_callback_event="initiated ringing answered completed",
			status_callback=self.get_update_call_status_callback_url(),
			status_callback_method="POST",
		)
		resp.append(dial)
		return resp

	def get_call_info(self, call_sid):
		return self.twilio_client.calls(call_sid).fetch()

	def generate_twilio_client_response(self, client, ring_tone="at"):
		"""Generates voice call instructions to forward the call to agents computer."""
		resp = VoiceResponse()
		dial = Dial(
			ring_tone=ring_tone,
			record=self.settings.record_calls,
			recording_status_callback=self.get_recording_status_callback_url(),
			recording_status_callback_event="completed",
		)
		dial.client(
			client,
			status_callback_event="initiated ringing answered completed",
			status_callback=self.get_update_call_status_callback_url(),
			status_callback_method="POST",
		)
		resp.append(dial)
		return resp

	@classmethod
	def get_twilio_client(self):
		twilio_settings = frappe.get_doc("CRM Twilio Settings")
		if not twilio_settings.enabled:
			frappe.throw(_("Please enable twilio settings before making a call."))

		auth_token = get_decrypted_password("CRM Twilio Settings", "CRM Twilio Settings", "auth_token")
		client = TwilioClient(twilio_settings.account_sid, auth_token)

		return client


class IncomingCall:
	def __init__(self, from_number, to_number, meta=None):
		self.from_number = from_number
		self.to_number = to_number
		self.meta = meta

	def process(self):
		"""Process the incoming call
		* Figure out who is going to pick the call (call attender)
		* Check call attender settings and forward the call to Phone
		"""
		twilio = Twilio.connect()
		owners = get_twilio_number_owners(self.to_number)
		attender = get_the_call_attender(owners, self.from_number)

		if not attender:
			resp = VoiceResponse()
			resp.say(_("Agent is unavailable to take the call, please call after some time."))
			return resp

		if attender["call_receiving_device"] == "Phone":
			return twilio.generate_twilio_dial_response(self.from_number, attender["mobile_no"])
		else:
			return twilio.generate_twilio_client_response(twilio.safe_identity(attender["name"]))


def get_twilio_number_owners(phone_number):
	"""Get list of users who is using the phone_number.
	>>> get_twilio_number_owners("+11234567890")
	{
		'owner1': {'name': '..', 'mobile_no': '..', 'call_receiving_device': '...'},
		'owner2': {....}
	}
	"""
	# remove special characters from phone number and get only digits also remove white spaces
	# keep + sign in the number at start of the number
	phone_number = "".join([c for c in phone_number if c.isdigit() or c == "+"])
	user_voice_settings = frappe.get_all(
		"CRM Telephony Agent",
		filters={"twilio_number": phone_number},
		fields=["name", "call_receiving_device"],
	)
	user_wise_voice_settings = {user["name"]: user for user in user_voice_settings}

	user_general_settings = frappe.get_all(
		"User", filters=[["name", "IN", user_wise_voice_settings.keys()]], fields=["name", "mobile_no"]
	)
	user_wise_general_settings = {user["name"]: user for user in user_general_settings}

	return merge_dicts(user_wise_general_settings, user_wise_voice_settings)


def get_active_loggedin_users(users):
	"""Filter the current loggedin users from the given users list"""
	rows = frappe.db.sql(
		"""
		SELECT `user`
		FROM `tabSessions`
		WHERE `user` IN %(users)s
		""",
		{"users": users},
	)
	return [row[0] for row in set(rows)]


def get_the_call_attender(owners, caller=None):
	"""Get attender details from list of owners"""
	if not owners:
		return
	current_loggedin_users = get_active_loggedin_users(list(owners.keys()))

	if len(current_loggedin_users) > 1 and caller:
		deal_owner = frappe.db.get_value("CRM Deal", {"mobile_no": caller}, "deal_owner")
		if not deal_owner:
			deal_owner = frappe.db.get_value(
				"CRM Lead", {"mobile_no": caller, "converted": False}, "lead_owner"
			)
		for user in current_loggedin_users:
			if user == deal_owner:
				current_loggedin_users = [user]

	for name, details in owners.items():
		if (details["call_receiving_device"] == "Phone" and details["mobile_no"]) or (
			details["call_receiving_device"] == "Computer" and name in current_loggedin_users
		):
			return details


class TwilioCallDetails:
	def __init__(self, call_info, call_from=None, call_to=None):
		self.call_info = call_info
		self.account_sid = call_info.get("AccountSid")
		self.application_sid = call_info.get("ApplicationSid")
		self.call_sid = call_info.get("CallSid")
		self.call_status = self.get_call_status(call_info.get("CallStatus"))
		self._call_from = call_from or call_info.get("From")
		self._call_to = call_to or call_info.get("To")

	def get_direction(self):
		if self.call_info.get("Caller").lower().startswith("client"):
			return "Outgoing"
		return "Incoming"

	def get_from_number(self):
		return self._call_from or self.call_info.get("From")

	def get_to_number(self):
		return self._call_to or self.call_info.get("To")

	@classmethod
	def get_call_status(cls, twilio_status):
		"""Convert Twilio given status into system status."""
		twilio_status = twilio_status or ""
		return " ".join(twilio_status.split("-")).title()

	def to_dict(self):
		"""Convert call details into dict."""
		direction = self.get_direction()
		from_number = self.get_from_number()
		to_number = self.get_to_number()
		caller = ""
		receiver = ""

		if direction == "Outgoing":
			caller = self.call_info.get("Caller")
			identity = caller.replace("client:", "").strip()
			caller = Twilio.emailid_from_identity(identity) if identity else ""
		else:
			owners = get_twilio_number_owners(to_number)
			attender = get_the_call_attender(owners, from_number)
			receiver = attender["name"] if attender else ""

		return {
			"type": direction,
			"status": self.call_status,
			"id": self.call_sid,
			"from": from_number,
			"to": to_number,
			"receiver": receiver,
			"caller": caller,
		}
