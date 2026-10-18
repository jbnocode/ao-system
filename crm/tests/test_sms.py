# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

from unittest.mock import MagicMock, patch

import frappe

from crm.api.sms import (
	_normalize_phone,
	_phones_match,
	list_conversations,
	map_twilio_status,
	notify_agent,
	validate,
)
from crm.tests import CRMTestCase as FrappeTestCase


class TestSMSHelpers(FrappeTestCase):
	def test_normalize_phone(self):
		self.assertEqual(_normalize_phone("15551234567"), "+15551234567")
		self.assertEqual(_normalize_phone("+1 555 123 4567"), "+15551234567")

	def test_phones_match(self):
		self.assertTrue(_phones_match("+1 555 000 1234", "+15550001234"))
		self.assertFalse(_phones_match("+15550001234", "+15550009999"))

	def test_map_twilio_status(self):
		self.assertEqual(map_twilio_status("delivered"), "Delivered")
		self.assertEqual(map_twilio_status("failed"), "Failed")
		self.assertEqual(map_twilio_status("unknown"), "Queued")


class TestSMSHooks(FrappeTestCase):
	def tearDown(self):
		frappe.db.rollback()

	def test_validate_sets_reference_when_contact_found(self):
		doc = MagicMock()
		doc.type = "Incoming"
		doc.reference_doctype = None
		doc.reference_name = None
		doc.get.return_value = "+15551234567"

		with patch(
			"crm.api.sms.get_contact_lead_or_deal_from_number",
			return_value=("LEAD-0001", "CRM Lead"),
		):
			validate(doc, None)

		self.assertEqual(doc.reference_doctype, "CRM Lead")
		self.assertEqual(doc.reference_name, "LEAD-0001")

	def test_validate_skips_when_reference_already_set(self):
		doc = MagicMock()
		doc.type = "Incoming"
		doc.reference_doctype = "CRM Lead"
		doc.reference_name = "LEAD-EXISTING"

		with patch("crm.api.sms.get_contact_lead_or_deal_from_number") as mock_lookup:
			validate(doc, None)

		mock_lookup.assert_not_called()

	def test_notify_agent_returns_early_when_no_reference(self):
		doc = MagicMock()
		doc.type = "Incoming"
		doc.reference_doctype = None
		doc.reference_name = None

		with patch("crm.api.sms.get_assigned_users") as mock_users:
			notify_agent(doc)

		mock_users.assert_not_called()


class TestSMSMessageDoc(FrappeTestCase):
	def tearDown(self):
		frappe.db.rollback()

	def test_insert_incoming_and_list_conversations(self):
		if not frappe.db.exists("DocType", "CRM SMS Message"):
			self.skipTest("CRM SMS Message DocType not installed")

		doc = frappe.get_doc(
			{
				"doctype": "CRM SMS Message",
				"from": "+15550001234",
				"to": "+15551000001",
				"from_number": "+15551000001",
				"message": "Hello from test",
				"type": "Incoming",
				"status": "Received",
			}
		).insert(ignore_permissions=True)

		self.assertTrue(frappe.db.exists("CRM SMS Message", doc.name))

		with patch("crm.api.sms._require_sms_role"):
			conversations = list_conversations(limit=20)

		phones = [c["phone"] for c in conversations]
		self.assertTrue(any(_phones_match(p, "+15550001234") for p in phones))


class TestTwilioSMSWebhook(FrappeTestCase):
	def tearDown(self):
		frappe.db.rollback()

	def test_incoming_sms_handler_creates_message(self):
		if not frappe.db.exists("DocType", "CRM SMS Message"):
			self.skipTest("CRM SMS Message DocType not installed")

		from crm.integrations.twilio import api as twilio_api

		with patch.object(twilio_api, "validate_twilio_request", return_value=MagicMock()):
			resp = twilio_api.twilio_incoming_sms_handler(
				MessageSid="SMtest123",
				Body="Inbound hello",
				From="+15550009999",
				To="+15551000001",
				AccountSid="ACtest",
			)

		self.assertEqual(resp.mimetype, "text/xml")
		self.assertTrue(
			frappe.db.exists("CRM SMS Message", {"twilio_sid": "SMtest123"})
		)
		row = frappe.db.get_value(
			"CRM SMS Message",
			{"twilio_sid": "SMtest123"},
			["message", "type", "status"],
			as_dict=True,
		)
		self.assertEqual(row.message, "Inbound hello")
		self.assertEqual(row.type, "Incoming")
		self.assertEqual(row.status, "Received")

	def test_incoming_sms_handler_is_idempotent(self):
		if not frappe.db.exists("DocType", "CRM SMS Message"):
			self.skipTest("CRM SMS Message DocType not installed")

		from crm.integrations.twilio import api as twilio_api

		kwargs = dict(
			MessageSid="SMdup999",
			Body="Once",
			From="+15550008888",
			To="+15551000001",
			AccountSid="ACtest",
		)
		with patch.object(twilio_api, "validate_twilio_request", return_value=MagicMock()):
			twilio_api.twilio_incoming_sms_handler(**kwargs)
			twilio_api.twilio_incoming_sms_handler(**kwargs)

		count = frappe.db.count("CRM SMS Message", {"twilio_sid": "SMdup999"})
		self.assertEqual(count, 1)

	def test_status_handler_updates_status(self):
		if not frappe.db.exists("DocType", "CRM SMS Message"):
			self.skipTest("CRM SMS Message DocType not installed")

		from crm.integrations.twilio import api as twilio_api

		frappe.get_doc(
			{
				"doctype": "CRM SMS Message",
				"from": "+15551000001",
				"to": "+15550007777",
				"from_number": "+15551000001",
				"message": "Outbound",
				"type": "Outgoing",
				"status": "Queued",
				"twilio_sid": "SMstatus1",
			}
		).insert(ignore_permissions=True)

		with patch.object(twilio_api, "validate_twilio_request", return_value=MagicMock()):
			twilio_api.twilio_sms_status_handler(
				MessageSid="SMstatus1",
				MessageStatus="delivered",
				AccountSid="ACtest",
			)

		status = frappe.db.get_value("CRM SMS Message", {"twilio_sid": "SMstatus1"}, "status")
		self.assertEqual(status, "Delivered")
