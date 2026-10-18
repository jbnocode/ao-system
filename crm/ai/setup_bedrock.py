# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""One-shot: configure CRM AI Settings for Amazon Bedrock.

	bench --site <site> execute crm.ai.setup_bedrock.apply
	bench --site <site> execute crm.ai.setup_bedrock.apply --kwargs "{'api_key': '…', 'aws_region': 'us-east-1'}"
"""

from __future__ import annotations

import frappe

from crm.ai.providers import (
	DEFAULT_BEDROCK_MODEL,
	DEFAULT_BEDROCK_REGION,
	PROVIDER_BEDROCK,
	bedrock_base_url,
)
from crm.demo.insurance import create_demo_insurance


def apply(
	api_key: str | None = None,
	aws_region: str | None = None,
	model: str | None = None,
	seed_insurance: int = 1,
) -> dict:
	"""Enable Bedrock provider on CRM AI Settings (keeps offline demo on)."""
	region = (aws_region or DEFAULT_BEDROCK_REGION).strip() or DEFAULT_BEDROCK_REGION
	model_id = (model or DEFAULT_BEDROCK_MODEL).strip() or DEFAULT_BEDROCK_MODEL

	doc = frappe.get_single("CRM AI Settings")
	doc.enabled = 1
	doc.provider = PROVIDER_BEDROCK
	doc.aws_region = region
	doc.base_url = bedrock_base_url(region)
	doc.model = model_id
	doc.allow_offline_demo = 1
	if not doc.credits_per_request:
		doc.credits_per_request = 1
	if api_key:
		doc.api_key = api_key
	doc.save(ignore_permissions=True)

	insurance = {}
	if frappe.utils.cint(seed_insurance):
		try:
			insurance = create_demo_insurance()
		except Exception as exc:
			insurance = {"error": str(exc)[:200]}

	frappe.db.commit()

	has_key = False
	try:
		has_key = bool(doc.get_password("api_key"))
	except Exception:
		has_key = False

	result = {
		"enabled": bool(doc.enabled),
		"provider": doc.provider,
		"aws_region": doc.aws_region,
		"base_url": doc.base_url,
		"model": doc.model,
		"allow_offline_demo": bool(doc.allow_offline_demo),
		"has_api_key": has_key,
		"insurance": {
			"quotes": len((insurance or {}).get("quotes") or []),
			"policies": len((insurance or {}).get("policies") or []),
			"error": (insurance or {}).get("error"),
		},
	}
	print(frappe.as_json(result, indent=2))
	return result
