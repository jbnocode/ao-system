# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""Install the life-insurance demo pack.

	bench --site <site> execute crm.life.install.install
	bench --site <site> execute crm.life.install.install --kwargs "{'replace_pipeline': 1, 'enable_flows': 1}"
"""

from __future__ import annotations

import frappe

from crm.life.fields import ensure_case_fields
from crm.life.flows import install as install_flows
from crm.life.layouts import apply_life_layouts
from crm.life.pipeline import apply_life_pipeline


def install(
	replace_pipeline: int = 1,
	enable_flows: int = 0,
	enable_life_mode: int = 1,
) -> dict:
	"""Apply life statuses, case fields, layouts, and automation recipes."""
	ensure_case_fields()
	pipeline = apply_life_pipeline(replace=bool(frappe.utils.cint(replace_pipeline)))
	install_flows(enable=frappe.utils.cint(enable_flows))

	life_on = bool(frappe.utils.cint(enable_life_mode))
	if life_on:
		frappe.db.set_single_value("FCRM Settings", "life_agency_mode", 1)
		apply_life_layouts()

	frappe.db.commit()
	result = {
		"pipeline": pipeline,
		"flows_enabled": bool(frappe.utils.cint(enable_flows)),
		"life_agency_mode": life_on,
	}
	print(frappe.as_json(result, indent=2))
	return result
