# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from unittest.mock import MagicMock, patch

import frappe
from frappe.tests import IntegrationTestCase

from crm.utils import block_desk_for_tenants


class TestBlockDeskForTenants(IntegrationTestCase):
	def test_blocks_desk_subpaths_for_sales_manager(self):
		request = MagicMock()
		request.path = "/desk/Lead"
		with (
			patch.object(frappe.local, "request", request),
			patch("crm.utils.frappe.session") as session,
			patch("crm.utils.frappe.get_roles", return_value=["Sales Manager", "Sales User"]),
			patch("crm.utils.frappe.redirect", side_effect=frappe.Redirect) as redirect,
		):
			session.user = "sales.manager@local.dev"
			with self.assertRaises(frappe.Redirect):
				block_desk_for_tenants()
			redirect.assert_called_once_with("/crm")

	def test_allows_system_manager_on_desk(self):
		request = MagicMock()
		request.path = "/desk"
		with (
			patch.object(frappe.local, "request", request),
			patch("crm.utils.frappe.session") as session,
			patch("crm.utils.frappe.get_roles", return_value=["System Manager"]),
			patch("crm.utils.frappe.redirect") as redirect,
		):
			session.user = "system.manager@local.dev"
			block_desk_for_tenants()
			redirect.assert_not_called()

	def test_ignores_non_desk_paths(self):
		request = MagicMock()
		request.path = "/crm/leads"
		with (
			patch.object(frappe.local, "request", request),
			patch("crm.utils.frappe.redirect") as redirect,
		):
			block_desk_for_tenants()
			redirect.assert_not_called()
