# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""CRM Email Campaign — ERPNext Email Campaign structure, adapted for Frappe CRM.

Campaign definition (schedules) lives on CRM Campaign. This DocType enrolls one
recipient (or Email Group) and drives daily sends from the parent schedule.
"""

from __future__ import annotations

from datetime import date

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import add_days, getdate, today


class CRMEmailCampaign(Document):
	def validate(self):
		self.set_date()
		self.validate_recipient()
		self.validate_not_duplicate()
		self.update_status()

	def set_date(self):
		start_changed = self.is_new() or self.has_value_changed("start_date")
		if (
			start_changed
			and not self.flags.get("ignore_start_date_check")
			and getdate(self.start_date) < getdate(today())
		):
			frappe.throw(_("Start Date cannot be before the current date"))

		self.end_date = self.get_end_date()
		if not self.end_date:
			frappe.throw(
				_("Set up Campaign Schedules on Campaign {0}").format(
					frappe.bold(self.campaign_name)
				)
			)

	def get_end_date(self) -> date | None:
		campaign = frappe.get_cached_doc("CRM Campaign", self.campaign_name)
		days = [int(row.send_after_days or 0) for row in (campaign.campaign_schedules or [])]
		if days:
			return add_days(getdate(self.start_date), max(days))
		return None

	def refresh_end_date(self):
		end_date = self.get_end_date()
		if end_date and end_date != getdate(self.end_date):
			self.db_set("end_date", end_date, update_modified=False)

	def validate_recipient(self):
		if not self.recipient:
			return
		if self.email_campaign_for == "Email Group":
			return
		if not frappe.db.exists(self.email_campaign_for, self.recipient):
			frappe.throw(
				_("{0} {1} does not exist").format(self.email_campaign_for, self.recipient)
			)
		email, phone, unsubscribed = _contact_bits(self.email_campaign_for, self.recipient)
		has_email_step = _campaign_has_channel(self.campaign_name, "Email")
		has_sms_step = _campaign_has_channel(self.campaign_name, "SMS")
		if has_email_step and not email:
			frappe.throw(_("Set an email on {0}").format(self.recipient))
		if has_sms_step and not phone:
			frappe.throw(_("Set a phone on {0}").format(self.recipient))
		if unsubscribed:
			frappe.throw(
				_("{0} {1} has unsubscribed from emails").format(
					_(self.email_campaign_for), frappe.bold(self.recipient)
				)
			)

	def validate_not_duplicate(self):
		exists = frappe.db.exists(
			"CRM Email Campaign",
			{
				"campaign_name": self.campaign_name,
				"recipient": self.recipient,
				"status": ("in", ["In Progress", "Scheduled"]),
				"name": ("!=", self.name),
			},
		)
		if exists:
			frappe.throw(
				_("Campaign {0} already running for {1}").format(
					self.campaign_name, self.recipient
				)
			)

	def update_status(self):
		"""ERPNext Email Campaign status: Scheduled → In Progress → Completed."""
		if self.status == "Unsubscribed":
			return
		start_date = getdate(self.start_date)
		end_date = getdate(self.end_date)
		today_date = getdate(today())
		if start_date > today_date:
			new_status = "Scheduled"
		elif end_date >= today_date:
			new_status = "In Progress"
		else:
			new_status = "Completed"
		if self.status != new_status:
			self.status = new_status


def _campaign_has_channel(campaign: str, channel: str) -> bool:
	return any(
		(row.channel or "Email") == channel
		for row in frappe.get_cached_doc("CRM Campaign", campaign).campaign_schedules or []
	)


def _contact_bits(doctype: str, name: str) -> tuple[str | None, str | None, int]:
	email = phone = None
	unsubscribed = 0
	if doctype == "CRM Lead":
		row = frappe.db.get_value(
			"CRM Lead",
			name,
			["email", "mobile_no", "phone"],
			as_dict=True,
		)
		if row:
			email = row.email
			phone = row.mobile_no or row.phone
	elif doctype == "Contact":
		row = frappe.db.get_value(
			"Contact",
			name,
			["email_id", "mobile_no", "phone", "unsubscribed"],
			as_dict=True,
		)
		if row:
			email = row.email_id
			phone = row.mobile_no or row.phone
			unsubscribed = int(row.unsubscribed or 0)
	elif doctype == "CRM Deal":
		row = frappe.db.get_value(
			"CRM Deal",
			name,
			["email", "mobile_no", "phone", "contact"],
			as_dict=True,
		)
		if row:
			email = row.email
			phone = row.mobile_no or row.phone
			if (not email or not phone) and row.contact:
				c = frappe.db.get_value(
					"Contact",
					row.contact,
					["email_id", "mobile_no", "phone"],
					as_dict=True,
				)
				if c:
					email = email or c.email_id
					phone = phone or c.mobile_no or c.phone
	return email, phone, unsubscribed


def process_email_campaigns():
	"""Daily: send due schedule rows for In Progress / Scheduled email campaigns."""
	set_email_campaign_status()
	today_date = getdate(today())
	rows = frappe.get_all(
		"CRM Email Campaign",
		filters={
			"status": ("!=", "Unsubscribed"),
			"start_date": ("<=", today_date),
			"end_date": (">=", today_date),
		},
		fields=[
			"name",
			"campaign_name",
			"email_campaign_for",
			"recipient",
			"start_date",
			"sender",
		],
	)
	for email_campaign in rows:
		try:
			_process_one(email_campaign, today_date)
		except Exception:
			frappe.log_error(title=f"CRM Email Campaign failed: {email_campaign.name}")


def set_email_campaign_status():
	for name in frappe.get_all(
		"CRM Email Campaign",
		filters={"status": ("!=", "Unsubscribed")},
		pluck="name",
	):
		doc = frappe.get_doc("CRM Email Campaign", name)
		doc.refresh_end_date()
		before = doc.status
		doc.update_status()
		if doc.status != before:
			doc.db_set("status", doc.status, update_modified=False)


def _process_one(email_campaign, today_date: date):
	try:
		campaign = frappe.get_cached_doc("CRM Campaign", email_campaign.campaign_name)
	except frappe.DoesNotExistError:
		return

	for entry in campaign.campaign_schedules or []:
		scheduled = add_days(getdate(email_campaign.start_date), int(entry.send_after_days or 0))
		if scheduled != today_date:
			continue
		if _step_already_sent(email_campaign.name, entry, today_date):
			continue
		_send_schedule_entry(entry, email_campaign)


def _step_already_sent(email_campaign: str, entry, on_date: date) -> bool:
	filters = {
		"reference_doctype": "CRM Email Campaign",
		"reference_name": email_campaign,
		"communication_date": (">=", on_date),
	}
	channel = entry.channel or "Email"
	if channel == "Email" and entry.email_template:
		filters["email_template"] = entry.email_template
		return bool(frappe.db.exists("Communication", filters))
	if channel == "SMS":
		# SMS tracked on CRM SMS Message linked to email campaign
		return bool(
			frappe.db.exists(
				"CRM SMS Message",
				{
					"reference_doctype": "CRM Email Campaign",
					"reference_name": email_campaign,
					"creation": (">=", f"{on_date} 00:00:00"),
					"message": ("like", f"%{(entry.sms_body or '')[:40]}%"),
				},
			)
		)
	return False


def _send_schedule_entry(entry, email_campaign):
	channel = entry.channel or "Email"
	if channel == "Email":
		_send_email(entry, email_campaign)
	elif channel == "SMS":
		_send_sms(entry, email_campaign)
	else:
		frappe.throw(_("Unsupported channel: {0}").format(channel))


def _recipient_list(email_campaign) -> list[tuple[str | None, str | None, dict]]:
	"""Return list of (email, phone, context_doc_dict)."""
	campaign_for = email_campaign.email_campaign_for
	recipient = email_campaign.recipient
	out: list[tuple[str | None, str | None, dict]] = []

	if campaign_for == "Email Group":
		emails = frappe.get_all(
			"Email Group Member",
			filters={"email_group": recipient, "unsubscribed": 0},
			pluck="email",
		)
		for email in emails:
			out.append((email, None, {"email": email, "doc": {"email": email}}))
		return out

	doc = frappe.get_doc(campaign_for, recipient)
	ctx = {**doc.as_dict(), "doc": doc}
	email, phone, _ = _contact_bits(campaign_for, recipient)
	out.append((email, phone, ctx))
	return out


def _send_email(entry, email_campaign):
	"""Send one schedule Email Template — same flow as ERPNext Email Campaign."""
	from frappe.core.doctype.communication.email import make

	if not entry.email_template:
		frappe.throw(_("Schedule row is missing Email Template"))

	template = frappe.get_cached_doc("Email Template", entry.email_template)
	sender = None
	if email_campaign.sender:
		sender = frappe.db.get_value("User", email_campaign.sender, "email")

	for email, _phone, ctx in _recipient_list(email_campaign):
		if not email:
			continue
		# Support both {{ doc.field }} and {{ field }}, as Email Template help shows
		subject = frappe.render_template(
			template.subject or "", ctx, restrict_globals=True
		)
		body = template.response_() if hasattr(template, "response_") else (
			template.response_html
			if getattr(template, "use_html", 0) and template.response_html
			else (template.response or template.response_html or "")
		)
		content = frappe.render_template(body or "", ctx, restrict_globals=True)

		frappe.db.savepoint("crm_email_campaign_send")
		try:
			comm = make(
				doctype="CRM Email Campaign",
				name=email_campaign.name,
				subject=subject,
				content=content,
				sender=sender,
				recipients=[email],
				communication_medium="Email",
				sent_or_received="Sent",
				send_email=False,
				email_template=template.name,
			)
			frappe.sendmail(
				recipients=[email],
				subject=subject,
				content=content,
				sender=sender,
				communication=comm["name"],
				queue_separately=True,
				reference_doctype="CRM Email Campaign",
				reference_name=email_campaign.name,
				unsubscribe_message=_("Unsubscribe from this campaign"),
			)
		except Exception:
			frappe.db.rollback(save_point="crm_email_campaign_send")
			frappe.log_error(title="CRM Email Campaign send failed")
			continue

		if email_campaign.email_campaign_for == "CRM Lead" and frappe.db.has_column(
			"CRM Lead", "campaign"
		):
			frappe.db.set_value(
				"CRM Lead",
				email_campaign.recipient,
				"campaign",
				email_campaign.campaign_name,
				update_modified=False,
			)


def _send_sms(entry, email_campaign):
	"""CRM extension: send schedule SMS via Twilio (ERPNext Campaign is email-only)."""
	from crm.api import sms as sms_api
	from crm.integrations.twilio.twilio_handler import Twilio

	twilio = Twilio.connect()
	if not twilio:
		frappe.throw(_("Twilio is not enabled"))

	sender = sms_api._agent_from_number(None)
	status_callback = twilio.get_incoming_sms_status_url()

	for _email, phone, ctx in _recipient_list(email_campaign):
		if not phone:
			continue
		body = frappe.render_template(
			(entry.sms_body or "").strip(), ctx, restrict_globals=True
		)
		to = sms_api._normalize_phone(phone)
		try:
			twilio_msg = twilio.twilio_client.messages.create(
				body=body,
				from_=sender,
				to=to,
				status_callback=status_callback,
			)
		except Exception as exc:
			frappe.log_error(title="CRM Email Campaign SMS failed", message=str(exc))
			continue

		frappe.get_doc(
			{
				"doctype": "CRM SMS Message",
				"from": sender,
				"to": to,
				"from_number": sender,
				"message": body,
				"type": "Outgoing",
				"status": sms_api.TWILIO_STATUS_MAP.get(
					(twilio_msg.status or "").lower(), "Queued"
				),
				"twilio_sid": twilio_msg.sid,
				"reference_doctype": "CRM Email Campaign",
				"reference_name": email_campaign.name,
			}
		).insert(ignore_permissions=True)


def unsubscribe_recipient(unsubscribe, method=None):
	"""Hook target for Email Unsubscribe → mark CRM Email Campaign Unsubscribed."""
	if getattr(unsubscribe, "reference_doctype", None) != "CRM Email Campaign":
		return
	if not frappe.db.exists("CRM Email Campaign", unsubscribe.reference_name):
		return
	doc = frappe.get_doc("CRM Email Campaign", unsubscribe.reference_name)
	if doc.email_campaign_for == "Email Group" and unsubscribe.email:
		frappe.db.set_value(
			"Email Group Member",
			{"email_group": doc.recipient, "email": unsubscribe.email},
			"unsubscribed",
			1,
		)
	else:
		frappe.db.set_value("CRM Email Campaign", doc.name, "status", "Unsubscribed")
