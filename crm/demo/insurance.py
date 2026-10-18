# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""Seed Insurance Quote / Application / Policy rows on demo deals for AI demos."""

from __future__ import annotations

import frappe
from frappe.utils import add_days, getdate, today

DEMO_INSURANCE_KEY = "crm_demo_insurance"

# Sample "live quote" catalog used when the AI is asked to generate quotes (demo / offline).
SAMPLE_TERM_QUOTES = [
	{"carrier": "Protective", "product": "Term Essential 20", "face_amount": 500000, "monthly_premium": 48.20, "term_years": 20},
	{"carrier": "Banner Life", "product": "OPTerm 20", "face_amount": 500000, "monthly_premium": 49.75, "term_years": 20},
	{"carrier": "Pacific Life", "product": "PL Promise Term 20", "face_amount": 500000, "monthly_premium": 51.10, "term_years": 20},
	{"carrier": "Principal", "product": "Term 20", "face_amount": 500000, "monthly_premium": 52.40, "term_years": 20},
	{"carrier": "John Hancock", "product": "Protection Term 20", "face_amount": 500000, "monthly_premium": 53.85, "term_years": 20},
	{"carrier": "North American", "product": "ADDvantage Term 20", "face_amount": 500000, "monthly_premium": 54.20, "term_years": 20},
	{"carrier": "Mutual of Omaha", "product": "Term Life Answers 20", "face_amount": 500000, "monthly_premium": 55.90, "term_years": 20},
	{"carrier": "Transamerica", "product": "Trendsetter Super 20", "face_amount": 500000, "monthly_premium": 57.15, "term_years": 20},
]


def create_demo_insurance(deal_data: dict | None = None) -> dict:
	"""Attach quotes / apps / policies to demo deals. Idempotent via DEMO_INSURANCE_KEY."""
	if not frappe.db.exists("DocType", "Insurance Quote"):
		return {"quotes": [], "applications": [], "policies": []}

	existing = frappe.db.get_default(DEMO_INSURANCE_KEY)
	if existing:
		try:
			payload = frappe.parse_json(existing) or {}
			if payload.get("quotes") or payload.get("policies"):
				return payload
		except Exception:
			pass

	deals = _deal_names(deal_data)
	if len(deals) < 5:
		return {"quotes": [], "applications": [], "policies": []}

	# Index order from create_demo_deals: alice, david, henry, iris, jack, karen, leo
	d_david, d_henry, d_iris, d_jack = deals[1], deals[2], deals[3], deals[4]

	quote_names = []
	app_names = []
	policy_names = []

	# David (Proposal/Quotation) — set of presented term options
	for i, row in enumerate(SAMPLE_TERM_QUOTES[:5]):
		status = "Presented" if i < 4 else "Accepted"
		name = _insert_quote(d_david, row, status=status, days_ago=4 + i)
		quote_names.append(name)

	# Henry (Negotiation) — fewer options
	for i, row in enumerate(SAMPLE_TERM_QUOTES[5:7]):
		name = _insert_quote(d_henry, row, status="Presented", days_ago=6 + i)
		quote_names.append(name)

	# Iris (Qualification) — draft only
	name = _insert_quote(
		d_iris,
		{
			"carrier": "Prudential",
			"product": "Essential Term 20",
			"face_amount": 250000,
			"monthly_premium": 28.40,
			"term_years": 20,
		},
		status="Draft",
		days_ago=2,
	)
	quote_names.append(name)

	# Jack (Won) — accepted quote → issued app → in-force policy
	accepted = _insert_quote(
		d_jack,
		{
			"carrier": "Protective",
			"product": "Term Essential 20",
			"face_amount": 750000,
			"monthly_premium": 72.50,
			"term_years": 20,
		},
		status="Accepted",
		days_ago=20,
	)
	quote_names.append(accepted)

	app = frappe.get_doc(
		{
			"doctype": "Insurance Application",
			"deal": d_jack,
			"source_quote": accepted,
			"status": "Issued",
			"submitted_on": add_days(getdate(today()), -14),
			"underwriting_class": "Preferred Plus",
			"carrier": "Protective",
			"product": "Term Essential 20",
			"face_amount": 750000,
			"monthly_premium": 72.50,
		}
	)
	app.insert(ignore_permissions=True)
	app_names.append(app.name)

	policy = frappe.get_doc(
		{
			"doctype": "Insurance Policy",
			"deal": d_jack,
			"source_application": app.name,
			"status": "In Force",
			"effective_date": add_days(getdate(today()), -10),
			"policy_number": "PL-DEMO-1001",
			"carrier": "Protective",
			"product": "Term Essential 20",
			"face_amount": 750000,
			"monthly_premium": 72.50,
		}
	)
	policy.insert(ignore_permissions=True)
	policy_names.append(policy.name)

	# Second in-force policy on Alice for book-of-business style questions
	d_alice = deals[0]
	policy2 = frappe.get_doc(
		{
			"doctype": "Insurance Policy",
			"deal": d_alice,
			"status": "In Force",
			"effective_date": add_days(getdate(today()), -120),
			"policy_number": "NA-DEMO-2044",
			"carrier": "North American",
			"product": "Custom Guarantee WL",
			"face_amount": 250000,
			"monthly_premium": 189.00,
		}
	)
	policy2.insert(ignore_permissions=True)
	policy_names.append(policy2.name)

	payload = {
		"quotes": quote_names,
		"applications": app_names,
		"policies": policy_names,
	}
	frappe.db.set_default(DEMO_INSURANCE_KEY, frappe.as_json(payload))
	return payload


def delete_demo_insurance(payload: dict | None = None):
	"""Remove seeded insurance rows (policies → apps → quotes)."""
	if payload is None:
		raw = frappe.db.get_default(DEMO_INSURANCE_KEY)
		payload = frappe.parse_json(raw) if raw else {}
	if not isinstance(payload, dict):
		payload = {}

	for name in payload.get("policies") or []:
		_force_delete("Insurance Policy", name)
	for name in payload.get("applications") or []:
		_force_delete("Insurance Application", name)
	for name in payload.get("quotes") or []:
		_force_delete("Insurance Quote", name)

	# Also clear any leftover insurance linked to demo deals if names drifted
	deal_data = frappe.parse_json(frappe.db.get_default("crm_demo_deals") or "{}") or {}
	deal_names = deal_data.get("deals") or []
	if deal_names and frappe.db.exists("DocType", "Insurance Quote"):
		for doctype in ("Insurance Policy", "Insurance Application", "Insurance Quote"):
			if not frappe.db.exists("DocType", doctype):
				continue
			for name in frappe.get_all(doctype, filters={"deal": ["in", deal_names]}, pluck="name"):
				_force_delete(doctype, name)

	frappe.db.set_default(DEMO_INSURANCE_KEY, None)


def sample_quote_table(
	*,
	age: int = 56,
	face: int = 500000,
	term: int = 20,
	state: str = "Indiana",
	tobacco: bool = False,
) -> dict:
	"""Insurance catalog block for chat (Unlock-style generate-quote moment)."""
	tobacco_label = "tobacco" if tobacco else "non-tobacco"
	items = []
	for q in SAMPLE_TERM_QUOTES:
		premium = q["monthly_premium"]
		# Tiny adjustment so demos look scenario-aware without a real rating engine
		if age >= 55:
			premium = round(premium * 1.08, 2)
		if face != 500000:
			premium = round(premium * (face / 500000), 2)
		items.append(
			{
				"carrier": q["carrier"],
				"product": q["product"],
				"face_amount": face,
				"monthly_premium": premium,
				"term_years": term,
				"status": "Indicative",
			}
		)
	return {
		"type": "insurance",
		"kind": "Catalog",
		"tab": "quotes",
		"title": f"Term life quotes — {state}, age {age}, ${face:,.0f}, {term}yr {tobacco_label}",
		"items": items,
	}


def quotes_table_from_records(quotes: list[dict], title: str | None = None) -> dict:
	items = []
	for q in quotes:
		items.append(
			{
				"name": q.get("name"),
				"deal": q.get("deal"),
				"carrier": q.get("carrier") or "",
				"product": q.get("product") or "",
				"face_amount": float(q.get("face_amount") or 0),
				"monthly_premium": float(q.get("monthly_premium") or 0),
				"term_years": q.get("term_years"),
				"status": q.get("status") or "Draft",
				"quote_date": q.get("quote_date"),
			}
		)
	return {
		"type": "insurance",
		"kind": "Quotes",
		"tab": "quotes",
		"title": title or "Insurance quotes",
		"items": items,
	}


def policies_table_from_records(policies: list[dict], title: str | None = None) -> dict:
	items = []
	for p in policies:
		items.append(
			{
				"name": p.get("name"),
				"deal": p.get("deal"),
				"carrier": p.get("carrier") or "",
				"product": p.get("product") or "",
				"face_amount": float(p.get("face_amount") or 0),
				"monthly_premium": float(p.get("monthly_premium") or 0),
				"policy_number": p.get("policy_number") or "",
				"status": p.get("status") or "Pending",
				"effective_date": p.get("effective_date"),
			}
		)
	return {
		"type": "insurance",
		"kind": "Policies",
		"tab": "policies",
		"title": title or "Insurance policies",
		"items": items,
	}


def _deal_names(deal_data: dict | None) -> list[str]:
	if deal_data and deal_data.get("deals"):
		return list(deal_data["deals"])
	raw = frappe.db.get_default("crm_demo_deals")
	if not raw:
		return []
	parsed = frappe.parse_json(raw) or {}
	return list(parsed.get("deals") or [])


def _insert_quote(deal: str, row: dict, *, status: str, days_ago: int) -> str:
	doc = frappe.get_doc(
		{
			"doctype": "Insurance Quote",
			"deal": deal,
			"status": status,
			"quote_date": add_days(getdate(today()), -days_ago),
			"term_years": row.get("term_years") or 20,
			"carrier": row["carrier"],
			"product": row["product"],
			"face_amount": row["face_amount"],
			"monthly_premium": row["monthly_premium"],
		}
	)
	doc.insert(ignore_permissions=True)
	return doc.name


def _force_delete(doctype: str, name: str):
	if name and frappe.db.exists(doctype, name):
		frappe.delete_doc(doctype, name, ignore_permissions=True, force=True)
