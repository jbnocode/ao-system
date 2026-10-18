# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from frappe.model.document import Document


class CRMSMSMessage(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from_number: DF.Data | None
		message: DF.Text
		reference_doctype: DF.Link | None
		reference_name: DF.DynamicLink | None
		status: DF.Literal["Queued", "Sent", "Delivered", "Failed", "Received"]
		to: DF.Data
		twilio_sid: DF.Data | None
		type: DF.Literal["Incoming", "Outgoing"]
	# end: auto-generated types

	pass
