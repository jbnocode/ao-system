# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""One-shot: configure CRM AI Settings for OpenRouter (free models OK).

	bench --site <site> execute crm.ai.setup_openrouter.apply --kwargs "{'api_key': '…'}"
"""

from __future__ import annotations

import frappe

from crm.ai.providers import (
	DEFAULT_OPENROUTER_BASE,
	DEFAULT_OPENROUTER_MODEL,
	PROVIDER_OPENROUTER,
)


def apply(api_key: str | None = None, model: str | None = None) -> dict:
	"""Enable OpenRouter on CRM AI Settings (keeps offline demo on)."""
	model_id = (model or DEFAULT_OPENROUTER_MODEL).strip() or DEFAULT_OPENROUTER_MODEL

	doc = frappe.get_single("CRM AI Settings")
	doc.enabled = 1
	doc.provider = PROVIDER_OPENROUTER
	doc.base_url = DEFAULT_OPENROUTER_BASE
	doc.model = model_id
	doc.allow_offline_demo = 1
	if not doc.credits_per_request:
		doc.credits_per_request = 1
	if api_key:
		doc.api_key = api_key
	doc.save(ignore_permissions=True)
	frappe.db.commit()

	has_key = False
	try:
		has_key = bool(doc.get_password("api_key"))
	except Exception:
		has_key = False

	result = {
		"enabled": bool(doc.enabled),
		"provider": doc.provider,
		"base_url": doc.base_url,
		"model": doc.model,
		"allow_offline_demo": bool(doc.allow_offline_demo),
		"has_api_key": has_key,
	}
	print(frappe.as_json(result, indent=2))
	return result
