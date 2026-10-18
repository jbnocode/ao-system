import frappe

# One user per CRM-allowed role (see crm.api.session.CRM_ALLOWED_ROLES).
USERS = [
	{
		"email": "sales.user@local.dev",
		"first_name": "Sales",
		"last_name": "User",
		"roles": ["Sales User"],
		"password": "SalesUser1!",
	},
	{
		"email": "sales.manager@local.dev",
		"first_name": "Sales",
		"last_name": "Manager",
		"roles": ["Sales Manager", "Sales User"],
		"password": "SalesManager1!",
	},
	{
		"email": "system.manager@local.dev",
		"first_name": "System",
		"last_name": "Manager",
		# Desk-only admin — no Sales roles so they do not land in CRM.
		"roles": ["System Manager"],
		"password": "SystemManager1!",
	},
]


def execute():
	"""Create or update one local user for each CRM role."""
	frappe.set_user("Administrator")
	results = []

	for spec in USERS:
		email = spec["email"]
		if frappe.db.exists("User", email):
			user = frappe.get_doc("User", email)
			user.enabled = 1
			user.first_name = spec["first_name"]
			user.last_name = spec["last_name"]
			action = "updated"
		else:
			user = frappe.get_doc(
				{
					"doctype": "User",
					"email": email,
					"first_name": spec["first_name"],
					"last_name": spec["last_name"],
					"send_welcome_email": 0,
					"user_type": "System User",
				}
			)
			user.flags.ignore_permissions = True
			user.insert()
			action = "created"

		user.flags.ignore_permissions = True
		user.set("roles", [])
		for role in spec["roles"]:
			user.append("roles", {"role": role})
		user.new_password = spec["password"]

		# Do not set default_workspace — Frappe would override home_page to Desk.
		# System Managers log into /crm; open Desk manually when needed.

		user.save()

		roles = [d.role for d in frappe.get_doc("User", email).roles]
		results.append(
			{
				"email": email,
				"action": action,
				"roles": roles,
				"password": spec["password"],
			}
		)

	frappe.db.commit()
	return results


DEMO_PHONE = "+15551234567"
DEMO_PHONE_USER = "sales.manager@local.dev"


def seed_demo_phone(user: str | None = None, phone: str | None = None):
	"""Assign a fake Twilio + AI Caller number so Call page UI unlocks locally."""
	frappe.set_user("Administrator")
	user = user or DEMO_PHONE_USER
	phone = phone or DEMO_PHONE

	if not frappe.db.exists("User", user):
		frappe.throw(f"User {user} does not exist — run crm.seed_role_users.execute first")

	# Human dialer / SMS from-number
	if frappe.db.exists("CRM Telephony Agent", user):
		frappe.db.set_value(
			"CRM Telephony Agent",
			user,
			{"twilio_number": phone, "default_medium": "Twilio"},
		)
		telephony = "updated"
	else:
		doc = frappe.get_doc(
			{
				"doctype": "CRM Telephony Agent",
				"user": user,
				"twilio_number": phone,
				"default_medium": "Twilio",
			}
		)
		doc.flags.ignore_permissions = True
		doc.insert()
		telephony = "created"

	# AI Call / Dialer setup wizard (needs phone + vapi_assistant_id)
	if frappe.db.exists("CRM AI Caller Agent", user):
		frappe.db.set_value(
			"CRM AI Caller Agent",
			user,
			{
				"phone_number": phone,
				"vapi_phone_id": "demo_phone_local",
				"vapi_assistant_id": "demo_assistant_local",
				"setup_completed": 1,
				"reviewed_compliance": 1,
			},
		)
		ai_caller = "updated"
	else:
		doc = frappe.get_doc(
			{
				"doctype": "CRM AI Caller Agent",
				"user": user,
				"phone_number": phone,
				"vapi_phone_id": "demo_phone_local",
				"vapi_assistant_id": "demo_assistant_local",
				"setup_completed": 1,
				"reviewed_compliance": 1,
			}
		)
		doc.flags.ignore_permissions = True
		doc.insert()
		ai_caller = "created"

	frappe.db.commit()
	return {
		"user": user,
		"phone": phone,
		"telephony_agent": telephony,
		"ai_caller_agent": ai_caller,
	}
