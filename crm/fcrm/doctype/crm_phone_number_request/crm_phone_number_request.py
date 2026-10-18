# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class CRMPhoneNumberRequest(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		area_code: DF.Data | None
		assign_to: DF.Link
		assign_to_name: DF.Data | None
		country_code: DF.Data
		error_message: DF.SmallText | None
		fulfilled_on: DF.Datetime | None
		notes: DF.SmallText | None
		phone_number: DF.Data | None
		requested_by: DF.Link
		requested_by_name: DF.Data | None
		status: DF.Literal["Requested", "Fulfilled", "Cancelled", "Failed"]
	# end: auto-generated types

	pass
