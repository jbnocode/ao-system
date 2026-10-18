# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import annotations

import re

import frappe
from frappe import _

from crm.api.doc import get_assigned_users
from crm.fcrm.doctype.crm_notification.crm_notification import notify_user
from crm.integrations.api import get_contact_lead_or_deal_from_number

ALLOWED_SMS_ROLES = ["System Manager", "Sales Manager", "Sales User"]

# Map Twilio MessageStatus → CRM SMS Message status
TWILIO_STATUS_MAP = {
	"queued": "Queued",
	"accepted": "Queued",
	"sending": "Queued",
	"sent": "Sent",
	"delivered": "Delivered",
	"undelivered": "Failed",
	"failed": "Failed",
	"received": "Received",
}


def _normalize_phone(phone_number: str) -> str:
	phone_number = "".join(c for c in (phone_number or "") if c.isdigit() or c == "+")
	if phone_number and not phone_number.startswith("+"):
		phone_number = f"+{phone_number}"
	return phone_number


def _phone_digits(phone_number: str) -> str:
	return re.sub(r"\D", "", phone_number or "")


def _phones_match(a: str, b: str) -> bool:
	da, db = _phone_digits(a), _phone_digits(b)
	if not da or not db:
		return False
	return da == db or da.endswith(db) or db.endswith(da)


def _require_sms_role():
	if not any(role in ALLOWED_SMS_ROLES for role in frappe.get_roles()):
		frappe.throw(_("Only sales users can access SMS features."), frappe.PermissionError)


def _agency_numbers() -> set[str]:
	rows = frappe.get_all(
		"CRM Telephony Agent",
		filters={"twilio_number": ("is", "set")},
		pluck="twilio_number",
	)
	return {_normalize_phone(n) for n in rows if n}


def _counterparty(row, agency: set[str]) -> str:
	"""Return the non-agency phone for a message row."""
	frm = _normalize_phone(row.get("from"))
	to = _normalize_phone(row.get("to"))
	if any(_phones_match(frm, a) for a in agency):
		return to
	if any(_phones_match(to, a) for a in agency):
		return frm
	# Fallback: Incoming → from is counterparty; Outgoing → to
	return frm if row.get("type") == "Incoming" else to


def _reference_title(doctype: str | None, name: str | None) -> str | None:
	if not doctype or not name or not frappe.db.exists(doctype, name):
		return None
	try:
		if doctype == "CRM Lead":
			return frappe.db.get_value("CRM Lead", name, "lead_name") or name
		if doctype == "CRM Deal":
			return frappe.db.get_value("CRM Deal", name, "organization") or name
		if doctype == "Contact":
			return frappe.db.get_value("Contact", name, "full_name") or name
	except Exception:
		return name
	return name


def validate(doc, method=None):
	"""Resolve Lead/Deal/Contact from the counterparty phone."""
	if doc.reference_doctype and doc.reference_name:
		return
	phone = doc.get("from") if doc.type == "Incoming" else doc.get("to")
	if not phone:
		return
	try:
		name, doctype = get_contact_lead_or_deal_from_number(phone)
		if doctype and name:
			doc.reference_doctype = doctype
			doc.reference_name = name
	except Exception:
		frappe.log_error(frappe.get_traceback(), "CRM SMS: failed to resolve contact from number")


def on_update(doc, method=None):
	frappe.publish_realtime(
		"sms_message",
		{
			"phone": _normalize_phone(doc.get("from") if doc.type == "Incoming" else doc.get("to")),
			"reference_doctype": doc.reference_doctype,
			"reference_name": doc.reference_name,
		},
	)
	notify_agent(doc)


def notify_agent(doc):
	if doc.type != "Incoming":
		return
	if not doc.reference_doctype or not doc.reference_name:
		return

	doctype = doc.reference_doctype
	if doctype and doctype.startswith("CRM "):
		doctype = doctype[4:].lower()
	safe_name = frappe.utils.escape_html(doc.reference_name)
	notification_text = f"""
		<div class="mb-2 leading-5 text-ink-gray-5">
			<span class="font-medium text-ink-gray-9">{_("You")}</span>
			<span>{_("received an SMS in {0}").format(doctype)}</span>
			<span class="font-medium text-ink-gray-9">{safe_name}</span>
		</div>
	"""
	assigned_users = get_assigned_users(doc.reference_doctype, doc.reference_name)
	for user in assigned_users:
		notify_user(
			{
				"owner": doc.owner,
				"assigned_to": user,
				"notification_type": "SMS",
				"message": doc.message,
				"notification_text": notification_text,
				"reference_doctype": "CRM SMS Message",
				"reference_docname": doc.name,
				"redirect_to_doctype": doc.reference_doctype,
				"redirect_to_docname": doc.reference_name,
			}
		)


@frappe.whitelist()
def is_sms_enabled() -> bool:
	"""Twilio enabled and current user (or any agent) has an SMS-capable number assigned."""
	if not frappe.db.get_single_value("CRM Twilio Settings", "enabled"):
		return False
	user = frappe.session.user
	own = frappe.db.get_value("CRM Telephony Agent", user, "twilio_number")
	if own:
		return True
	# Managers can send from any assigned org number
	if "System Manager" in frappe.get_roles() or "Sales Manager" in frappe.get_roles():
		return bool(
			frappe.db.exists("CRM Telephony Agent", {"twilio_number": ("is", "set")})
		)
	return False


@frappe.whitelist()
def list_conversations(limit: int | str = 50) -> list[dict]:
	"""Group SMS messages by counterparty phone (newest first)."""
	_require_sms_role()
	limit = min(max(int(limit or 50), 1), 200)
	agency = _agency_numbers()
	rows = frappe.get_all(
		"CRM SMS Message",
		fields=[
			"name",
			"from",
			"to",
			"message",
			"type",
			"status",
			"creation",
			"reference_doctype",
			"reference_name",
		],
		order_by="creation desc",
		limit=500,
	)

	conversations: dict[str, dict] = {}
	for row in rows:
		phone = _counterparty(row, agency)
		if not phone:
			continue
		key = _phone_digits(phone) or phone
		if key in conversations:
			continue
		title = _reference_title(row.reference_doctype, row.reference_name)
		conversations[key] = {
			"phone": phone,
			"title": title or phone,
			"preview": (row.message or "")[:120],
			"type": row.type,
			"status": row.status,
			"creation": row.creation,
			"reference_doctype": row.reference_doctype,
			"reference_name": row.reference_name,
		}
		if len(conversations) >= limit:
			break

	return list(conversations.values())


@frappe.whitelist()
def get_party(phone: str) -> dict:
	"""Profile for the Text inbox right panel: linked Lead/Deal/Contact + contact fields."""
	_require_sms_role()
	phone = _normalize_phone(phone)
	if not phone:
		frappe.throw(_("Phone number is required"))

	party = {
		"phone": phone,
		"title": phone,
		"email": None,
		"mobile_no": phone,
		"image": None,
		"organization": None,
		"status": None,
		"owner": None,
		"owner_name": None,
		"job_title": None,
		"website": None,
		"reference_doctype": None,
		"reference_name": None,
	}

	# Prefer an SMS row's linked reference, else resolve from phone
	ref_doctype = None
	ref_name = None
	for row in frappe.get_all(
		"CRM SMS Message",
		fields=["from", "to", "reference_doctype", "reference_name"],
		order_by="creation desc",
		limit=100,
	):
		if _phones_match(row.get("from"), phone) or _phones_match(row.get("to"), phone):
			if row.reference_doctype and row.reference_name:
				ref_doctype, ref_name = row.reference_doctype, row.reference_name
				break

	if not ref_doctype:
		try:
			ref_name, ref_doctype = get_contact_lead_or_deal_from_number(phone)
		except Exception:
			ref_name, ref_doctype = None, None

	party["reference_doctype"] = ref_doctype
	party["reference_name"] = ref_name

	if ref_doctype == "CRM Lead" and ref_name and frappe.db.exists("CRM Lead", ref_name):
		lead = frappe.db.get_value(
			"CRM Lead",
			ref_name,
			[
				"lead_name",
				"email",
				"mobile_no",
				"image",
				"organization",
				"status",
				"lead_owner",
				"job_title",
				"website",
			],
			as_dict=True,
		)
		if lead:
			party.update(
				{
					"title": lead.lead_name or ref_name,
					"email": lead.email,
					"mobile_no": lead.mobile_no or phone,
					"image": lead.image,
					"organization": lead.organization,
					"status": lead.status,
					"owner": lead.lead_owner,
					"job_title": lead.job_title,
					"website": lead.website,
				}
			)
	elif ref_doctype == "CRM Deal" and ref_name and frappe.db.exists("CRM Deal", ref_name):
		deal = frappe.db.get_value(
			"CRM Deal",
			ref_name,
			[
				"organization",
				"email",
				"mobile_no",
				"deal_owner",
				"status",
				"website",
			],
			as_dict=True,
		)
		if deal:
			party.update(
				{
					"title": deal.organization or ref_name,
					"email": deal.email,
					"mobile_no": deal.mobile_no or phone,
					"organization": deal.organization,
					"status": deal.status,
					"owner": deal.deal_owner,
					"website": deal.website,
				}
			)
	elif ref_doctype == "Contact" and ref_name and frappe.db.exists("Contact", ref_name):
		contact = frappe.db.get_value(
			"Contact",
			ref_name,
			["full_name", "email_id", "mobile_no", "image", "company_name", "user"],
			as_dict=True,
		)
		if contact:
			party.update(
				{
					"title": contact.full_name or ref_name,
					"email": contact.email_id,
					"mobile_no": contact.mobile_no or phone,
					"image": contact.image,
					"organization": contact.company_name,
					"owner": contact.user,
				}
			)

	if party.get("owner"):
		party["owner_name"] = (
			frappe.db.get_value("User", party["owner"], "full_name") or party["owner"]
		)

	return party


@frappe.whitelist()
def get_messages(phone: str, limit: int | str = 100) -> list[dict]:
	"""Return SMS thread for a counterparty phone (oldest first)."""
	_require_sms_role()
	phone = _normalize_phone(phone)
	if not phone:
		frappe.throw(_("Phone number is required"))
	limit = min(max(int(limit or 100), 1), 500)

	rows = frappe.get_all(
		"CRM SMS Message",
		fields=[
			"name",
			"from",
			"to",
			"message",
			"type",
			"status",
			"creation",
			"twilio_sid",
			"from_number",
			"reference_doctype",
			"reference_name",
		],
		order_by="creation asc",
		limit=2000,
	)
	messages = []
	for row in rows:
		if _phones_match(row.get("from"), phone) or _phones_match(row.get("to"), phone):
			messages.append(row)
		if len(messages) >= limit:
			break
	return messages


def _agent_from_number(from_number: str | None = None) -> str:
	"""Resolve which Twilio number to send from."""
	user = frappe.session.user
	own = frappe.db.get_value("CRM Telephony Agent", user, "twilio_number")
	if from_number:
		from_number = _normalize_phone(from_number)
		# Allow own number always; managers may use any assigned number
		if own and _phones_match(own, from_number):
			return from_number
		if "System Manager" in frappe.get_roles() or "Sales Manager" in frappe.get_roles():
			agency = _agency_numbers()
			if any(_phones_match(from_number, a) for a in agency):
				return from_number
		frappe.throw(_("Not allowed to send from that number"))
	if own:
		return _normalize_phone(own)
	if "System Manager" in frappe.get_roles() or "Sales Manager" in frappe.get_roles():
		agency = list(_agency_numbers())
		if agency:
			return agency[0]
	frappe.throw(_("No Twilio number assigned. Ask a manager to assign one in Telephony settings."))


@frappe.whitelist()
def send_sms(to: str, message: str, from_number: str | None = None) -> dict:
	"""Send an SMS via Twilio and store an Outgoing CRM SMS Message."""
	_require_sms_role()
	to = _normalize_phone(to)
	message = (message or "").strip()
	if not to:
		frappe.throw(_("Recipient phone is required"))
	if not message:
		frappe.throw(_("Message is required"))

	from crm.integrations.twilio.twilio_handler import Twilio

	twilio = Twilio.connect()
	if not twilio:
		frappe.throw(_("Twilio is not enabled. Configure it in Telephony settings."))

	sender = _agent_from_number(from_number)
	status_callback = twilio.get_incoming_sms_status_url()

	try:
		twilio_msg = twilio.twilio_client.messages.create(
			body=message,
			from_=sender,
			to=to,
			status_callback=status_callback,
		)
	except Exception as exc:
		frappe.throw(_("Could not send SMS: {0}").format(str(exc)))

	doc = frappe.get_doc(
		{
			"doctype": "CRM SMS Message",
			"from": sender,
			"to": to,
			"from_number": sender,
			"message": message,
			"type": "Outgoing",
			"status": TWILIO_STATUS_MAP.get((twilio_msg.status or "").lower(), "Queued"),
			"twilio_sid": twilio_msg.sid,
		}
	)
	doc.insert(ignore_permissions=True)
	frappe.db.commit()
	return {
		"name": doc.name,
		"twilio_sid": doc.twilio_sid,
		"status": doc.status,
	}


def map_twilio_status(status: str | None) -> str:
	return TWILIO_STATUS_MAP.get((status or "").lower(), "Queued")
