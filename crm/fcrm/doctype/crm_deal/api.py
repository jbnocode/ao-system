import frappe
from frappe import _


@frappe.whitelist()
def get_deal_contacts(name: str):
	if not frappe.has_permission("CRM Deal", "read", name):
		frappe.throw(_("Not permitted"), frappe.PermissionError)

	fields = ["contact", "is_primary", "name"]
	if frappe.get_meta("CRM Contacts").has_field("relationship"):
		fields.append("relationship")

	contacts = frappe.get_all(
		"CRM Contacts",
		filters={"parenttype": "CRM Deal", "parent": name},
		fields=fields,
		order_by="is_primary desc, idx asc",
		distinct=True,
	)
	deal_contacts = []
	for row in contacts:
		if not row.contact:
			continue

		is_primary = row.is_primary
		contact = frappe.get_doc("Contact", row.contact).as_dict()

		_contact = {
			"name": contact.name,
			"image": contact.image,
			"full_name": contact.full_name,
			"first_name": contact.first_name,
			"email": contact.email_id,
			"mobile_no": contact.mobile_no,
			"is_primary": is_primary,
			"relationship": row.get("relationship") or ("Self" if is_primary else ""),
			"row_name": row.name,
		}
		deal_contacts.append(_contact)
	return deal_contacts
