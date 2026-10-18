# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import annotations

import json
import re

import frappe
from frappe import _
from frappe.model.document import Document

DEFAULT_AVAILABILITY = {
	"mon": [["09:00", "17:00"]],
	"tue": [["09:00", "17:00"]],
	"wed": [["09:00", "17:00"]],
	"thu": [["09:00", "17:00"]],
	"fri": [["09:00", "17:00"]],
	"sat": [],
	"sun": [],
}

_SLUG_RE = re.compile(r"[^a-z0-9-]+")


def sanitize_slug(value: str | None) -> str:
	raw = (value or "").strip().lower().replace(" ", "-").replace("_", "-")
	slug = _SLUG_RE.sub("", raw).strip("-")
	while "--" in slug:
		slug = slug.replace("--", "-")
	return slug[:80]


class CRMBookingProfile(Document):
	def validate(self):
		self.slug = sanitize_slug(self.slug)
		if not self.slug:
			frappe.throw(_("Slug is required"))

		if self.provider == "Calendly" and self.enabled and not (self.calendly_url or "").strip():
			frappe.throw(_("Calendly URL is required when Calendly is enabled"))

		# Zoom / Meet credentials live on User Appointment Availability + Google Calendar
		# when frappe_appointment is installed; do not require them on this overlay.

		if self.duration_minutes is None or int(self.duration_minutes) < 5:
			frappe.throw(_("Duration must be at least 5 minutes"))

		self._validate_availability()

	def _validate_availability(self):
		if self.provider != "Native":
			return
		raw = (self.availability_json or "").strip()
		if not raw:
			self.availability_json = json.dumps(DEFAULT_AVAILABILITY, indent=2)
			return
		try:
			data = json.loads(raw)
		except json.JSONDecodeError:
			frappe.throw(_("Availability JSON is invalid"))
		if not isinstance(data, dict):
			frappe.throw(_("Availability JSON must be an object"))
		for day, windows in data.items():
			if day not in DEFAULT_AVAILABILITY:
				frappe.throw(_("Unknown weekday key: {0}").format(day))
			if not isinstance(windows, list):
				frappe.throw(_("Availability for {0} must be a list").format(day))
			for window in windows:
				if (
					not isinstance(window, (list, tuple))
					or len(window) != 2
					or not all(isinstance(t, str) for t in window)
				):
					frappe.throw(_("Each window must be [start, end] like [\"09:00\", \"17:00\"]"))


def default_availability_json() -> str:
	return json.dumps(DEFAULT_AVAILABILITY, indent=2)
