# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import annotations

import frappe
from frappe import _


def get_settings():
	return frappe.get_single("CRM AI Settings")


def _require_manager():
	frappe.only_for(("System Manager", "Sales Manager"))


def _get_wallet(for_update: bool = False):
	"""Return the org team wallet singleton (creates row if missing)."""
	if not frappe.db.exists("CRM Credit Wallet", "CRM Credit Wallet"):
		frappe.get_doc({"doctype": "CRM Credit Wallet", "balance": 0}).insert(ignore_permissions=True)
		frappe.db.commit()
	return frappe.get_doc("CRM Credit Wallet", "CRM Credit Wallet", for_update=for_update)


@frappe.whitelist()
def get_team_wallet() -> dict:
	"""Team credit pool balance (managers see full; agents see balance too)."""
	wallet = _get_wallet()
	return {"balance": int(wallet.balance or 0)}


@frappe.whitelist()
def top_up_team_credits(amount: int | str) -> dict:
	"""Add credits to the shared team pool (manager purchase / top-up)."""
	_require_manager()
	amount = int(amount or 0)
	if amount <= 0:
		frappe.throw(_("Amount must be positive"))

	wallet = _get_wallet(for_update=True)
	wallet.balance = int(wallet.balance or 0) + amount
	wallet.save(ignore_permissions=True)
	frappe.db.commit()
	return get_team_wallet()


@frappe.whitelist()
def get_balance(user: str | None = None) -> dict:
	user = user or frappe.session.user
	if user != frappe.session.user:
		_require_manager()
	ensure_balance(user)
	row = frappe.db.get_value(
		"CRM AI Credit Balance", user, ["credits", "credit_limit"], as_dict=True
	) or {"credits": 0, "credit_limit": 0}
	settings = get_settings()
	return {
		"user": user,
		"credits": int(row.credits or 0),
		"credit_limit": int(row.credit_limit or 0),
		"credits_per_request": int(settings.credits_per_request or 1),
		"enabled": bool(settings.enabled),
	}


@frappe.whitelist()
def list_agent_credits() -> list[dict]:
	"""Balances and limits for CRM users (managers).

	Uses the same CRM user list as the rest of the app. Has Role / User
	queries without ignore_permissions often return empty for Sales Manager.
	"""
	_require_manager()
	from crm.api.session import get_users

	_all_users, crm_users = get_users(include_all=False)
	# Site bootstrap account — not an agency agent to fund
	crm_users = [u for u in crm_users if u.name != "Administrator"]
	if not crm_users:
		return []

	names = [u.name for u in crm_users]
	balance_fields = ["name", "user", "credits"]
	if frappe.db.has_column("CRM AI Credit Balance", "credit_limit"):
		balance_fields.append("credit_limit")

	balances = {
		r.name: r
		for r in frappe.get_all(
			"CRM AI Credit Balance",
			filters={"name": ("in", names)},
			fields=balance_fields,
			ignore_permissions=True,
		)
	}

	rows = []
	for u in sorted(crm_users, key=lambda x: (x.full_name or x.name or "").lower()):
		b = balances.get(u.name)
		rows.append(
			{
				"user": u.name,
				"user_name": u.full_name or u.name,
				"credits": int(b.credits or 0) if b else 0,
				"credit_limit": int(getattr(b, "credit_limit", None) or 0) if b else 0,
			}
		)
	return rows


@frappe.whitelist()
def set_agent_credit_limit(user: str, credit_limit: int | str) -> dict:
	"""Set max credits an agent may hold. 0 = no cap."""
	_require_manager()
	if not user or not frappe.db.exists("User", user):
		frappe.throw(_("Valid user is required"))
	credit_limit = int(credit_limit or 0)
	if credit_limit < 0:
		frappe.throw(_("Credit limit cannot be negative"))

	ensure_balance(user, grant_default=False)
	doc = frappe.get_doc("CRM AI Credit Balance", user)
	doc.credit_limit = credit_limit
	# If current balance exceeds new cap, leave balance (manager may lower over time via spend)
	doc.save(ignore_permissions=True)
	frappe.db.commit()
	return get_balance(user)


@frappe.whitelist()
def disburse_credits(user: str, amount: int | str) -> dict:
	"""Move credits from the team pool to an agent."""
	_require_manager()
	amount = int(amount or 0)
	if amount <= 0:
		frappe.throw(_("Amount must be positive"))
	if not user or not frappe.db.exists("User", user):
		frappe.throw(_("Valid user is required"))

	wallet = _get_wallet(for_update=True)
	team = int(wallet.balance or 0)
	if team < amount:
		frappe.throw(
			_("Not enough team credits ({0} left, {1} needed). Top up the team pool first.").format(
				team, amount
			),
			frappe.ValidationError,
		)

	ensure_balance(user, grant_default=False)
	doc = frappe.get_doc("CRM AI Credit Balance", user, for_update=True)
	balance = int(doc.credits or 0)

	wallet.balance = team - amount
	wallet.save(ignore_permissions=True)
	doc.credits = balance + amount
	doc.save(ignore_permissions=True)
	frappe.db.commit()

	return {
		"user": user,
		"credits": int(doc.credits or 0),
		"team_balance": int(wallet.balance or 0),
	}


@frappe.whitelist()
def grant_credits(user: str, amount: int | str) -> dict:
	"""Backward-compatible alias: disburse from the team pool."""
	return disburse_credits(user=user, amount=amount)


@frappe.whitelist()
def list_credit_usage(user: str | None = None, limit: int | str = 50) -> list[dict]:
	"""Recent credit spend logs for managers (optionally filtered by user)."""
	_require_manager()
	limit = min(max(int(limit or 50), 1), 200)
	filters = {}
	if user:
		if not frappe.db.exists("User", user):
			frappe.throw(_("Valid user is required"))
		filters["user"] = user

	rows = frappe.get_all(
		"CRM AI Usage Log",
		filters=filters or None,
		fields=[
			"name",
			"user",
			"context_type",
			"credits_spent",
			"status",
			"tokens_in",
			"tokens_out",
			"message_preview",
			"creation",
		],
		order_by="creation desc",
		limit_page_length=limit,
		ignore_permissions=True,
	)
	if not rows:
		return []

	names = list({r.user for r in rows if r.user})
	full_names = {
		r.name: r.full_name
		for r in frappe.get_all(
			"User",
			filters={"name": ("in", names)},
			fields=["name", "full_name"],
			ignore_permissions=True,
		)
	}
	return [
		{
			"name": r.name,
			"user": r.user,
			"user_name": full_names.get(r.user) or r.user,
			"context_type": r.context_type or "",
			"credits_spent": int(r.credits_spent or 0),
			"status": r.status or "",
			"tokens_in": r.tokens_in,
			"tokens_out": r.tokens_out,
			"message_preview": r.message_preview or "",
			"creation": str(r.creation) if r.creation else "",
		}
		for r in rows
	]


def ensure_balance(user: str, grant_default: bool = True) -> int:
	if frappe.db.exists("CRM AI Credit Balance", user):
		return int(frappe.db.get_value("CRM AI Credit Balance", user, "credits") or 0)

	settings = get_settings()
	initial = int(settings.default_grant or 0) if grant_default else 0
	# Bootstrap from team wallet when possible so default grants don't invent credits
	if initial > 0:
		wallet = _get_wallet(for_update=True)
		team = int(wallet.balance or 0)
		if team >= initial:
			wallet.balance = team - initial
			wallet.save(ignore_permissions=True)
		else:
			initial = 0

	frappe.get_doc(
		{
			"doctype": "CRM AI Credit Balance",
			"user": user,
			"credits": initial,
			"credit_limit": 0,
		}
	).insert(ignore_permissions=True)
	frappe.db.commit()
	return initial


def consume(
	user: str,
	amount: int,
	*,
	context_type: str,
	message_preview: str,
	status: str = "Success",
	tokens_in=None,
	tokens_out=None,
) -> int:
	"""Debit agent credits and write a usage log. Raises if balance is insufficient."""
	amount = int(amount or 0)
	ensure_balance(user)
	doc = frappe.get_doc("CRM AI Credit Balance", user, for_update=True)
	balance = int(doc.credits or 0)
	if amount > 0 and balance < amount:
		frappe.throw(
			_("Not enough credits ({0} left, {1} needed). Ask a manager to disburse credits.").format(
				balance, amount
			),
			frappe.ValidationError,
		)
	if amount > 0:
		doc.credits = balance - amount
		doc.save(ignore_permissions=True)

	frappe.get_doc(
		{
			"doctype": "CRM AI Usage Log",
			"user": user,
			"context_type": context_type or "general",
			"credits_spent": amount,
			"status": status,
			"tokens_in": tokens_in,
			"tokens_out": tokens_out,
			"message_preview": (message_preview or "")[:140],
		}
	).insert(ignore_permissions=True)
	frappe.db.commit()
	return int(doc.credits or 0)
