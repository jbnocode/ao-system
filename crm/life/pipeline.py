# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""Life underwriting deal-status template."""

from __future__ import annotations

import frappe

# Ordered underwriting path for a life agency. Agencies can still rename/reorder
# via CRM Deal Status after applying.
LIFE_DEAL_STATUSES = [
	{"deal_status": "Contacted", "color": "gray", "type": "Open", "probability": 10, "position": 1},
	{
		"deal_status": "Needs Analysis",
		"color": "orange",
		"type": "Ongoing",
		"probability": 20,
		"position": 2,
	},
	{"deal_status": "Quoted", "color": "blue", "type": "Ongoing", "probability": 40, "position": 3},
	{
		"deal_status": "Application Submitted",
		"color": "cyan",
		"type": "Ongoing",
		"probability": 55,
		"position": 4,
	},
	{
		"deal_status": "Exam Scheduled",
		"color": "teal",
		"type": "Ongoing",
		"probability": 60,
		"position": 5,
	},
	{
		"deal_status": "Underwriting",
		"color": "violet",
		"type": "Ongoing",
		"probability": 70,
		"position": 6,
	},
	{"deal_status": "Approved", "color": "purple", "type": "Ongoing", "probability": 85, "position": 7},
	{
		"deal_status": "Policy Delivered",
		"color": "green",
		"type": "Won",
		"probability": 100,
		"position": 8,
	},
	{"deal_status": "Lost", "color": "red", "type": "Lost", "probability": 0, "position": 9},
	{"deal_status": "Declined", "color": "pink", "type": "Lost", "probability": 0, "position": 10},
]

LIFE_STATUS_NAMES = [row["deal_status"] for row in LIFE_DEAL_STATUSES]
FALLBACK_STATUS = "Contacted"


def ensure_life_statuses() -> list[str]:
	"""Create or update life statuses. Does not remove other statuses."""
	created: list[str] = []
	for row in LIFE_DEAL_STATUSES:
		name = row["deal_status"]
		if frappe.db.exists("CRM Deal Status", name):
			frappe.db.set_value(
				"CRM Deal Status",
				name,
				{
					"color": row["color"],
					"type": row["type"],
					"probability": row["probability"],
					"position": row["position"],
				},
				update_modified=False,
			)
		else:
			doc = frappe.get_doc({"doctype": "CRM Deal Status", **row})
			doc.insert(ignore_permissions=True)
			created.append(name)
	return created


def apply_life_pipeline(*, replace: bool = False) -> dict:
	"""Install the life pipeline. If replace=True, remap deals off non-life statuses and remove them."""
	created = ensure_life_statuses()
	removed: list[str] = []
	remapped = 0

	if replace:
		remapped, removed = _replace_non_life_statuses()

	frappe.clear_cache(doctype="CRM Deal Status")
	return {
		"statuses": LIFE_STATUS_NAMES,
		"created": created,
		"removed": removed,
		"remapped_deals": remapped,
		"mode": "replace" if replace else "merge",
	}


def _replace_non_life_statuses() -> tuple[int, list[str]]:
	ensure_life_statuses()
	existing = frappe.get_all("CRM Deal Status", pluck="name")
	to_remove = [name for name in existing if name not in LIFE_STATUS_NAMES]
	remapped = 0

	if to_remove:
		remapped = frappe.db.count("CRM Deal", {"status": ("in", to_remove)})
		if remapped:
			frappe.db.set_value(
				"CRM Deal",
				{"status": ("in", to_remove)},
				"status",
				FALLBACK_STATUS,
				update_modified=False,
			)

		for name in to_remove:
			frappe.delete_doc("CRM Deal Status", name, force=True, ignore_permissions=True)

	return remapped, to_remove


def list_life_statuses() -> list[dict]:
	return list(LIFE_DEAL_STATUSES)
