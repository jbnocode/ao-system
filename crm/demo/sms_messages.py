from datetime import datetime, timedelta

import frappe

from crm.demo.users import DEMO_USERS
from crm.demo.utils import resolve_owners


def _ensure_contact(first_name, last_name, email, mobile_no, company=None):
	"""Create (or reuse) a Contact with phone + email for SMS linking."""
	existing = frappe.db.get_value("Contact Phone", {"phone": mobile_no}, "parent")
	if existing and frappe.db.exists("Contact", existing):
		return existing

	doc = frappe.get_doc(
		{
			"doctype": "Contact",
			"first_name": first_name,
			"last_name": last_name,
			"email_id": email,
			"mobile_no": mobile_no,
			"company_name": company or "",
			"email_ids": [{"email_id": email, "is_primary": 1}],
			"phone_nos": [{"phone": mobile_no, "is_primary_mobile_no": 1}],
		}
	)
	doc.insert(ignore_permissions=True)
	return doc.name


def create_demo_sms_messages(lead_names, demo_users):
	now = datetime.now()
	session_user, owner_1, owner_2, _ = resolve_owners(demo_users)

	_user_mobile = {u["email"]: u["mobile_no"] for u in DEMO_USERS}
	rep_numbers = {
		session_user: _user_mobile.get(session_user, "+1 555 100 0001"),
		owner_1: _user_mobile.get(owner_1, "+1 555 100 0002"),
		owner_2: _user_mobile.get(owner_2, "+1 555 100 0003"),
	}

	# Contact-linked thread (dedicated number, not a demo lead mobile)
	contact_mobile = "+1 555 000 7777"
	contact_name = _ensure_contact(
		"Priya",
		"Nair",
		"priya.nair@example.com",
		contact_mobile,
		company="Harbor Dental",
	)

	threads = [
		# Lead-linked: Alice Johnson
		[
			{
				"type": "Incoming",
				"status": "Received",
				"from": "+1 555 000 1234",
				"to": rep_numbers[session_user],
				"from_number": rep_numbers[session_user],
				"message": "Hi — following up on the Acme Corp quote we discussed.",
				"reference_doctype": "CRM Lead",
				"reference_name": lead_names[0],
				"creation": now - timedelta(days=4, hours=3),
				"owner": session_user,
			},
			{
				"type": "Outgoing",
				"status": "Delivered",
				"from": rep_numbers[session_user],
				"to": "+1 555 000 1234",
				"from_number": rep_numbers[session_user],
				"message": "Thanks Alice! I'll send the revised proposal this afternoon.",
				"reference_doctype": "CRM Lead",
				"reference_name": lead_names[0],
				"creation": now - timedelta(days=4, hours=2),
				"owner": session_user,
			},
			{
				"type": "Incoming",
				"status": "Received",
				"from": "+1 555 000 1234",
				"to": rep_numbers[session_user],
				"from_number": rep_numbers[session_user],
				"message": "Perfect, looking forward to it.",
				"reference_doctype": "CRM Lead",
				"reference_name": lead_names[0],
				"creation": now - timedelta(days=4, hours=1),
				"owner": session_user,
			},
		],
		# Lead-linked: Bob Martinez
		[
			{
				"type": "Outgoing",
				"status": "Delivered",
				"from": rep_numbers[owner_1],
				"to": "+1 555 000 5678",
				"from_number": rep_numbers[owner_1],
				"message": "Bob — are you free for a quick call tomorrow about Globex?",
				"reference_doctype": "CRM Lead",
				"reference_name": lead_names[1],
				"creation": now - timedelta(days=2, hours=5),
				"owner": owner_1,
			},
			{
				"type": "Incoming",
				"status": "Received",
				"from": "+1 555 000 5678",
				"to": rep_numbers[owner_1],
				"from_number": rep_numbers[owner_1],
				"message": "Yes, after 2pm works on my end.",
				"reference_doctype": "CRM Lead",
				"reference_name": lead_names[1],
				"creation": now - timedelta(days=2, hours=4),
				"owner": owner_1,
			},
		],
		# Lead-linked: Carol Smith
		[
			{
				"type": "Incoming",
				"status": "Received",
				"from": "+1 555 000 9012",
				"to": rep_numbers[owner_2],
				"from_number": rep_numbers[owner_2],
				"message": "Can you text me the BrightPath onboarding checklist?",
				"reference_doctype": "CRM Lead",
				"reference_name": lead_names[2],
				"creation": now - timedelta(days=1, hours=6),
				"owner": owner_2,
			},
			{
				"type": "Outgoing",
				"status": "Sent",
				"from": rep_numbers[owner_2],
				"to": "+1 555 000 9012",
				"from_number": rep_numbers[owner_2],
				"message": "Sent! Let me know if anything is unclear.",
				"reference_doctype": "CRM Lead",
				"reference_name": lead_names[2],
				"creation": now - timedelta(days=1, hours=5),
				"owner": owner_2,
			},
		],
		# Contact-linked: Priya Nair
		[
			{
				"type": "Incoming",
				"status": "Received",
				"from": contact_mobile,
				"to": rep_numbers[session_user],
				"from_number": rep_numbers[session_user],
				"message": "Hi, this is Priya from Harbor Dental — is the policy review still on for Friday?",
				"reference_doctype": "Contact",
				"reference_name": contact_name,
				"creation": now - timedelta(hours=8),
				"owner": session_user,
			},
			{
				"type": "Outgoing",
				"status": "Delivered",
				"from": rep_numbers[session_user],
				"to": contact_mobile,
				"from_number": rep_numbers[session_user],
				"message": "Yes Priya — Friday at 10am works. I'll send a calendar invite.",
				"reference_doctype": "Contact",
				"reference_name": contact_name,
				"creation": now - timedelta(hours=7),
				"owner": session_user,
			},
		],
		# Unlinked unknown number (no Lead/Contact) — panel still shows empty fields
		[
			{
				"type": "Incoming",
				"status": "Received",
				"from": "+1 555 000 4444",
				"to": rep_numbers[session_user],
				"from_number": rep_numbers[session_user],
				"message": "Who is this? I got a missed call earlier.",
				"creation": now - timedelta(hours=2),
				"owner": session_user,
			},
			{
				"type": "Outgoing",
				"status": "Sent",
				"from": rep_numbers[session_user],
				"to": "+1 555 000 4444",
				"from_number": rep_numbers[session_user],
				"message": "Sorry about that — this is Acme Agency. Happy to chat if you're exploring coverage.",
				"creation": now - timedelta(hours=1),
				"owner": session_user,
			},
		],
	]

	created = []
	for thread in threads:
		for data in thread:
			owner = data.pop("owner", frappe.session.user)
			creation = data.pop("creation", now)
			doc = frappe.get_doc({"doctype": "CRM SMS Message", **data}).insert(
				ignore_permissions=True
			)
			frappe.db.set_value(
				"CRM SMS Message",
				doc.name,
				{
					"owner": owner,
					"modified_by": owner,
					"creation": creation,
					"modified": creation,
				},
				update_modified=False,
			)
			created.append(doc.name)

	return {"messages": created, "contacts": [contact_name]}


def delete_demo_sms_messages(sms_payload):
	"""Accept legacy list of message names or {messages, contacts} dict."""
	if isinstance(sms_payload, dict):
		message_names = sms_payload.get("messages") or []
		contact_names = sms_payload.get("contacts") or []
	else:
		message_names = sms_payload or []
		contact_names = []

	for name in message_names:
		if frappe.db.exists("CRM SMS Message", name):
			frappe.delete_doc("CRM SMS Message", name, ignore_permissions=True, force=True)

	for name in contact_names:
		if not name or not frappe.db.exists("Contact", name):
			continue
		for child_doctype in ("Contact Email", "Contact Phone", "Dynamic Link"):
			frappe.db.delete(child_doctype, {"parent": name})
		frappe.delete_doc("Contact", name, ignore_permissions=True, force=True)
