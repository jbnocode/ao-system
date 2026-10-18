# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""Insurance snapshot for AI chat prompts + table helpers."""

from __future__ import annotations

import frappe

from crm.demo.insurance import (
	policies_table_from_records,
	quotes_table_from_records,
	sample_quote_table,
)


def get_insurance_snapshot(limit: int = 24) -> dict:
	"""Recent quotes + policies the current user can read."""
	quotes = _list_doctype(
		"Insurance Quote",
		fields=[
			"name",
			"deal",
			"status",
			"carrier",
			"product",
			"face_amount",
			"monthly_premium",
			"term_years",
			"quote_date",
		],
		limit=limit,
	)
	policies = _list_doctype(
		"Insurance Policy",
		fields=[
			"name",
			"deal",
			"status",
			"carrier",
			"product",
			"face_amount",
			"monthly_premium",
			"policy_number",
			"effective_date",
		],
		limit=limit,
	)
	return {
		"quotes": quotes,
		"policies": policies,
		"quote_count": len(quotes),
		"policy_count": len(policies),
	}


def insurance_reply_for_prompt(prompt: str, snapshot: dict | None = None) -> dict | None:
	"""
	If the user asks about quotes/policies (or to generate quotes),
	return a chat payload with a table block. Otherwise None.
	"""
	text = (prompt or "").lower()
	snapshot = snapshot or get_insurance_snapshot()

	wants_generate = any(
		k in text
		for k in (
			"generate",
			"run a quote",
			"run quote",
			"quote me",
			"get quotes",
			"pull quotes",
			"term life",
			"term quote",
		)
	) and ("quote" in text or "quotes" in text)

	# Explicit generate / Unlock-style ask
	if wants_generate or (
		"quote" in text
		and any(k in text for k in ("56", "500", "500000", "500,000", "indiana", "non-tobacco", "non tobacco"))
	):
		block = sample_quote_table()
		n = len(block.get("items") or block.get("rows") or [])
		return {
			"reply": (
				f"Here are {n} indicative term options "
				"(demo catalog — not live carrier rates). "
				"Ask to show quotes already on your cases, then open one on the deal."
			),
			"ops": [],
			"blocks": [block],
		}

	wants_list_policies = any(
		k in text
		for k in (
			"show my polic",
			"list my polic",
			"list polic",
			"my policies",
			"show policies",
			"book of business",
		)
	)
	if wants_list_policies or (text.strip() in ("policies", "my policies")):
		policies = snapshot.get("policies") or []
		if not policies:
			return {
				"reply": "No insurance policies on file yet. Seed demo data or add a policy on a deal.",
				"ops": [],
				"blocks": [],
			}
		return {
			"reply": f"You have {len(policies)} polic{'y' if len(policies) == 1 else 'ies'} on file:",
			"ops": [],
			"blocks": [policies_table_from_records(policies, title="Policies on file")],
		}

	wants_list_quotes = any(
		k in text
		for k in (
			"show my quote",
			"list my quote",
			"list quote",
			"my quotes",
			"show quotes",
			"quotes on file",
		)
	)
	if wants_list_quotes or (text.strip() in ("quotes", "my quotes")):
		quotes = snapshot.get("quotes") or []
		if not quotes:
			return {
				"reply": (
					"No insurance quotes on file yet. Try “generate quotes for a 56-year-old "
					"in Indiana” for a demo table, or seed demo insurance data."
				),
				"ops": [],
				"blocks": [],
			}
		return {
			"reply": f"You have {len(quotes)} quote(s) on file:",
			"ops": [],
			"blocks": [quotes_table_from_records(quotes, title="Quotes on file")],
		}

	return None


def _list_doctype(doctype: str, *, fields: list[str], limit: int) -> list[dict]:
	if not frappe.db.exists("DocType", doctype):
		return []
	if not frappe.has_permission(doctype, "read"):
		return []
	return frappe.get_all(
		doctype,
		fields=fields,
		order_by="modified desc",
		limit_page_length=limit,
	)
