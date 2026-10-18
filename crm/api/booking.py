# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""Booking facade.

Native scheduling is powered by ``frappe_appointment`` (User Appointment Availability).
Calendly remains a CRM-only overlay on ``CRM Booking Profile``.
"""

from __future__ import annotations

import json

import frappe
from frappe import _
from frappe.utils import cint, get_url

from crm.fcrm.doctype.crm_booking_profile.crm_booking_profile import (
	sanitize_slug,
)

WEEKDAY_KEYS = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")
WEEKDAY_LABELS = {
	"mon": "Monday",
	"tue": "Tuesday",
	"wed": "Wednesday",
	"thu": "Thursday",
	"fri": "Friday",
	"sat": "Saturday",
	"sun": "Sunday",
}
LABEL_TO_KEY = {v: k for k, v in WEEKDAY_LABELS.items()}

DEFAULT_AVAILABILITY = {
	"mon": [["09:00", "17:00"]],
	"tue": [["09:00", "17:00"]],
	"wed": [["09:00", "17:00"]],
	"thu": [["09:00", "17:00"]],
	"fri": [["09:00", "17:00"]],
	"sat": [],
	"sun": [],
}


def appointment_installed() -> bool:
	return "frappe_appointment" in frappe.get_installed_apps()


def _is_system_manager() -> bool:
	return "System Manager" in frappe.get_roles()


def _can_configure_site_integrations() -> bool:
	roles = set(frappe.get_roles())
	return bool(roles & {"System Manager", "Sales Manager"})


def _google_calendar_for_user(user: str) -> str | None:
	return frappe.db.get_value("Google Calendar", {"user": user}, "name")


def _google_calendar_connected(user: str) -> bool:
	row = frappe.db.get_value(
		"Google Calendar",
		{"user": user},
		["enable", "refresh_token", "custom_zoom_user_email"],
		as_dict=True,
	)
	return bool(row and row.enable and row.refresh_token)


def _google_calendar_row(user: str) -> dict | None:
	name = _google_calendar_for_user(user)
	if not name:
		return None
	return frappe.db.get_value(
		"Google Calendar",
		name,
		["name", "enable", "refresh_token", "custom_zoom", "custom_zoom_user_email"],
		as_dict=True,
	)


def _crm_profile_name(user: str) -> str | None:
	return frappe.db.get_value("CRM Booking Profile", {"user": user}, "name")


def _default_slug_for_user(user: str) -> str:
	username = frappe.db.get_value("User", user, "username")
	full_name = frappe.db.get_value("User", user, "full_name") or user
	base = sanitize_slug(username or full_name.split("@")[0] if "@" in full_name else full_name)
	if not base:
		base = sanitize_slug(user.split("@")[0]) or "agent"
	candidate = base
	n = 1
	while True:
		owner = frappe.db.get_value("User Appointment Availability", {"slug": candidate}, "user")
		if not owner or owner == user:
			crm_owner = frappe.db.get_value("CRM Booking Profile", {"slug": candidate}, "user")
			if not crm_owner or crm_owner == user:
				return candidate
		n += 1
		candidate = f"{base}-{n}"


def _seconds_to_minutes(value) -> int:
	try:
		sec = float(value or 0)
	except (TypeError, ValueError):
		return 30
	if sec <= 0:
		return 30
	# Duration fields are seconds; tolerate accidental minute values.
	if sec < 300:
		return max(5, int(sec))
	return max(5, int(round(sec / 60)))


def _minutes_to_duration(minutes: int) -> int:
	return max(5, int(minutes or 30)) * 60


def _normalize_time(value) -> str:
	text = str(value or "09:00:00")
	parts = text.split(":")
	return f"{int(parts[0]):02d}:{int(parts[1]):02d}"


def _availability_from_slots(rows: list) -> dict:
	out = {k: [] for k in WEEKDAY_KEYS}
	for row in rows or []:
		key = LABEL_TO_KEY.get(row.get("day") or "")
		if not key:
			continue
		out[key].append([_normalize_time(row.get("start_time")), _normalize_time(row.get("end_time"))])
	return out


def _slots_from_availability(availability: dict | None) -> list[dict]:
	data = availability or DEFAULT_AVAILABILITY
	rows = []
	for key in WEEKDAY_KEYS:
		for window in data.get(key) or []:
			if not isinstance(window, (list, tuple)) or len(window) < 2:
				continue
			rows.append(
				{
					"day": WEEKDAY_LABELS[key],
					"start_time": f"{_normalize_time(window[0])}:00",
					"end_time": f"{_normalize_time(window[1])}:00",
				}
			)
	return rows


def _parse_availability_json(raw: str | None) -> dict:
	text = (raw or "").strip()
	if not text:
		return dict(DEFAULT_AVAILABILITY)
	try:
		data = json.loads(text)
	except json.JSONDecodeError:
		return dict(DEFAULT_AVAILABILITY)
	if not isinstance(data, dict):
		return dict(DEFAULT_AVAILABILITY)
	out = dict(DEFAULT_AVAILABILITY)
	for key in WEEKDAY_KEYS:
		windows = data.get(key, [])
		if isinstance(windows, list):
			out[key] = windows
	return out


def _uaa_for_user(user: str):
	if not appointment_installed():
		return None
	name = frappe.db.get_value("User Appointment Availability", {"user": user}, "name")
	if not name:
		return None
	return frappe.get_doc("User Appointment Availability", name)


def _ensure_uaa(user: str):
	"""Create User Appointment Availability when Google Calendar exists."""
	doc = _uaa_for_user(user)
	if doc:
		return doc
	calendar = _google_calendar_for_user(user)
	if not calendar:
		return None
	doc = frappe.get_doc(
		{
			"doctype": "User Appointment Availability",
			"user": user,
			"google_calendar": calendar,
			"enable_scheduling": 0,
			"slug": _default_slug_for_user(user),
			"meeting_provider": "None",
			"appointment_time_slot": _slots_from_availability(DEFAULT_AVAILABILITY),
			"available_durations": [
				{
					"title": _("Meeting"),
					"duration": _minutes_to_duration(30),
					"availability_window": 14,
					"minimum_buffer_time": 0,
					"allow_rescheduling": 1,
				}
			],
		}
	)
	doc.insert(ignore_permissions=True)
	return doc


def _crm_overlay(user: str) -> dict:
	name = _crm_profile_name(user)
	if not name:
		return {
			"provider": "Native",
			"calendly_url": "",
			"page_title": "",
			"timezone": "UTC",
			"slug": "",
		}
	row = frappe.db.get_value(
		"CRM Booking Profile",
		name,
		["provider", "calendly_url", "page_title", "timezone", "slug"],
		as_dict=True,
	)
	return {
		"provider": row.provider or "Native",
		"calendly_url": row.calendly_url or "",
		"page_title": row.page_title or "",
		"timezone": row.timezone or "UTC",
		"slug": row.slug or "",
	}


def _save_crm_overlay(
	user: str,
	*,
	provider: str,
	calendly_url: str,
	page_title: str,
	slug: str,
	timezone: str,
	enabled: int,
) -> None:
	"""Keep Calendly + title/timezone on CRM Booking Profile."""
	name = _crm_profile_name(user)
	payload = {
		"user": user,
		"provider": provider,
		"calendly_url": calendly_url,
		"page_title": page_title,
		"slug": slug,
		"timezone": timezone or "UTC",
		"enabled": enabled,
		"duration_minutes": 30,
		"meeting_provider": "None",
		"availability_json": json.dumps(DEFAULT_AVAILABILITY),
	}
	if name:
		doc = frappe.get_doc("CRM Booking Profile", name)
		doc.update(payload)
		doc.save(ignore_permissions=True)
	else:
		doc = frappe.get_doc({"doctype": "CRM Booking Profile", **payload})
		doc.insert(ignore_permissions=True)


def _map_meeting_out(provider: str | None, meeting_link: str | None) -> tuple[str, str, str]:
	"""Return (ui_provider, zoom_url, meet_url)."""
	provider = provider or "None"
	link = (meeting_link or "").strip()
	if provider == "Google Meet":
		return "Google Meet", "", link
	if provider == "Zoom":
		return "Zoom", link, ""
	if provider == "Custom":
		if "meet.google" in link.lower():
			return "Google Meet", "", link
		return "Zoom", link, ""
	return "None", "", ""


def _map_meeting_in(
	meeting_provider: str,
	zoom_personal_url: str,
	meet_personal_url: str,
	zoom_s2s_enabled: bool,
	calendar_connected: bool,
) -> tuple[str, str]:
	"""Return (uaa meeting_provider, meeting_link). Agents may use personal links — no approval."""
	meeting_provider = (meeting_provider or "None").strip()
	zoom_url = (zoom_personal_url or "").strip()
	meet_url = (meet_personal_url or "").strip()

	if meeting_provider == "Google Meet":
		if calendar_connected:
			return "Google Meet", meet_url
		if meet_url:
			return "Custom", meet_url
		frappe.throw(
			_("Add a Google Meet link, or connect Google Calendar to auto-create Meet links.")
		)

	if meeting_provider == "Zoom":
		if zoom_s2s_enabled:
			return "Zoom", ""
		if zoom_url:
			return "Custom", zoom_url
		frappe.throw(_("Add your Zoom personal meeting URL to use Zoom."))

	return "None", ""


def _zoom_site_status() -> dict:
	can_configure = _can_configure_site_integrations()
	if not appointment_installed():
		return {"enable_zoom": False, "configured": False, "can_configure": can_configure}
	settings = frappe.get_single("Appointment Settings")
	has_secret = bool(settings.get_password("zoom_client_secret", raise_exception=False))
	return {
		"enable_zoom": bool(settings.enable_zoom),
		"configured": bool(
			settings.enable_zoom
			and settings.zoom_account_id
			and settings.zoom_client_id
			and has_secret
		),
		"can_configure": can_configure,
		"zoom_account_id": settings.zoom_account_id if can_configure else None,
		"zoom_client_id": settings.zoom_client_id if can_configure else None,
		"has_client_secret": has_secret,
	}


def _serialize(user: str) -> dict:
	overlay = _crm_overlay(user)
	full_name = frappe.db.get_value("User", user, "full_name") or user
	calendar = _google_calendar_row(user)
	zoom_site = _zoom_site_status()
	uaa = _uaa_for_user(user)

	availability = dict(DEFAULT_AVAILABILITY)
	duration_minutes = 30
	buffer_minutes = 0
	advance_days = 14
	meeting_provider = "None"
	zoom_personal_url = ""
	meet_personal_url = ""
	slug = overlay.get("slug") or _default_slug_for_user(user)
	enabled = False
	schedule_url = None
	durations: list[dict] = []

	if uaa:
		availability = _availability_from_slots(uaa.get("appointment_time_slot") or [])
		enabled = bool(uaa.enable_scheduling)
		slug = uaa.slug or slug
		meeting_provider, zoom_personal_url, meet_personal_url = _map_meeting_out(
			uaa.meeting_provider, uaa.meeting_link
		)
		for row in uaa.get("available_durations") or []:
			mins = _seconds_to_minutes(row.duration)
			durations.append(
				{
					"name": row.name,
					"title": row.title,
					"duration_minutes": mins,
					"availability_window": cint(row.availability_window) or 14,
					"buffer_minutes": _seconds_to_minutes(row.minimum_buffer_time)
					if row.minimum_buffer_time
					else 0,
				}
			)
		if durations:
			duration_minutes = durations[0]["duration_minutes"]
			advance_days = durations[0]["availability_window"]
			buffer_minutes = durations[0]["buffer_minutes"]
		schedule_url = f"{get_url()}/schedule/in/{slug}"

	provider = overlay.get("provider") or "Native"
	calendly_url = overlay.get("calendly_url") or ""
	page_title = overlay.get("page_title") or _("Meet with {0}").format(full_name)
	timezone = overlay.get("timezone") or "UTC"

	public_url = schedule_url
	share_url = calendly_url if provider == "Calendly" and calendly_url else schedule_url

	return {
		"engine": "frappe_appointment" if appointment_installed() else "native",
		"appointment_installed": appointment_installed(),
		"name": uaa.name if uaa else None,
		"user": user,
		"user_name": full_name,
		"enabled": enabled if provider == "Native" else bool(enabled or calendly_url),
		"provider": provider,
		"page_title": page_title,
		"slug": slug,
		"duration_minutes": duration_minutes,
		"timezone": timezone,
		"advance_days": advance_days,
		"buffer_minutes": buffer_minutes,
		"calendly_url": calendly_url,
		"availability": availability,
		"availability_json": json.dumps(availability),
		"durations": durations,
		"meeting_provider": meeting_provider,
		"zoom_personal_url": zoom_personal_url,
		"meet_personal_url": meet_personal_url,
		"zoom_account_email": (calendar or {}).get("custom_zoom_user_email") or "",
		"public_url": public_url,
		"share_url": share_url,
		"schedule_url": schedule_url,
		"google_calendar_connected": _google_calendar_connected(user),
		"google_calendar": (calendar or {}).get("name"),
		"zoom_site": zoom_site,
	}


@frappe.whitelist()
def get_my_booking_profile() -> dict:
	user = frappe.session.user
	if user == "Guest":
		frappe.throw(_("Login required"), frappe.PermissionError)
	if appointment_installed() and _google_calendar_for_user(user):
		_ensure_uaa(user)
	return _serialize(user)


@frappe.whitelist()
def save_my_booking_profile(
	enabled: int | str | bool = 0,
	provider: str = "Native",
	page_title: str | None = None,
	slug: str | None = None,
	duration_minutes: int | str = 30,
	timezone: str | None = "UTC",
	advance_days: int | str = 14,
	buffer_minutes: int | str = 0,
	calendly_url: str | None = None,
	availability_json: str | None = None,
	meeting_provider: str = "None",
	zoom_personal_url: str | None = None,
	meet_personal_url: str | None = None,
	zoom_account_email: str | None = None,
) -> dict:
	user = frappe.session.user
	if user == "Guest":
		frappe.throw(_("Login required"), frappe.PermissionError)

	provider = (provider or "Native").strip()
	if provider not in ("Native", "Calendly"):
		frappe.throw(_("Invalid booking provider"))

	meeting_provider = (meeting_provider or "None").strip()
	if meeting_provider not in ("None", "Google Meet", "Zoom"):
		frappe.throw(_("Invalid meeting provider"))

	clean_slug = sanitize_slug(slug) or _default_slug_for_user(user)
	enabled_int = 1 if cint(enabled) else 0
	title = (page_title or "").strip() or _("Meet with {0}").format(
		frappe.db.get_value("User", user, "full_name") or user
	)
	tz = (timezone or "UTC").strip() or "UTC"
	cal_url = (calendly_url or "").strip()

	_save_crm_overlay(
		user,
		provider=provider,
		calendly_url=cal_url,
		page_title=title,
		slug=clean_slug,
		timezone=tz,
		enabled=enabled_int,
	)

	if not appointment_installed():
		frappe.throw(
			_("Install the frappe_appointment app to enable native booking."),
			frappe.ValidationError,
		)

	calendar = _google_calendar_for_user(user)
	calendar_connected = _google_calendar_connected(user)
	# Native scheduling needs a Google Calendar row for conflict checks — connect when ready.
	# Meet/Zoom personal links work without waiting for site OAuth approval.

	zoom_site = _zoom_site_status()
	meet_provider, meet_link = _map_meeting_in(
		meeting_provider,
		zoom_personal_url or "",
		meet_personal_url or "",
		bool(zoom_site.get("configured")),
		calendar_connected,
	)

	if calendar and zoom_account_email is not None:
		frappe.db.set_value(
			"Google Calendar",
			calendar,
			"custom_zoom_user_email",
			(zoom_account_email or "").strip(),
		)

	uaa = _ensure_uaa(user)
	if not uaa:
		# No calendar yet — still allow Meet/Zoom prefs once calendar exists; overlay saved
		return _serialize(user)

	availability = _parse_availability_json(availability_json)
	duration_m = max(5, cint(duration_minutes) or 30)
	advance = max(1, cint(advance_days) or 14)
	buffer_m = max(0, cint(buffer_minutes) or 0)

	uaa.google_calendar = calendar or uaa.google_calendar
	# Only publish native schedule when calendar is connected (frappe_appointment requirement)
	uaa.enable_scheduling = (
		1 if enabled_int and provider == "Native" and calendar_connected else 0
	)
	uaa.slug = clean_slug
	uaa.meeting_provider = meet_provider
	uaa.meeting_link = meet_link
	uaa.set("appointment_time_slot", [])
	for row in _slots_from_availability(availability):
		uaa.append("appointment_time_slot", row)

	# Keep a single primary duration in sync with the Booking page
	uaa.set("available_durations", [])
	uaa.append(
		"available_durations",
		{
			"title": title[:140] or _("Meeting"),
			"duration": _minutes_to_duration(duration_m),
			"availability_window": advance,
			"minimum_buffer_time": buffer_m * 60 if buffer_m else 0,
			"allow_rescheduling": 1,
		},
	)
	uaa.save(ignore_permissions=True)
	return _serialize(user)


@frappe.whitelist()
def save_zoom_site_settings(
	enable_zoom: int | str | bool = 0,
	zoom_account_id: str | None = None,
	zoom_client_id: str | None = None,
	zoom_client_secret: str | None = None,
) -> dict:
	"""Sales Manager / System Manager: Zoom Server-to-Server OAuth on Appointment Settings."""
	if not _can_configure_site_integrations():
		frappe.throw(
			_("Only Sales Managers or System Managers can configure Zoom API."),
			frappe.PermissionError,
		)
	if not appointment_installed():
		frappe.throw(_("frappe_appointment is not installed"))

	settings = frappe.get_single("Appointment Settings")
	settings.enable_zoom = 1 if cint(enable_zoom) else 0
	if zoom_account_id is not None:
		settings.zoom_account_id = (zoom_account_id or "").strip()
	if zoom_client_id is not None:
		settings.zoom_client_id = (zoom_client_id or "").strip()
	if zoom_client_secret:
		settings.zoom_client_secret = zoom_client_secret
	settings.save(ignore_permissions=True)
	return {"zoom_site": _zoom_site_status()}


@frappe.whitelist()
def get_my_recent_bookings(limit: int | str = 20) -> list[dict]:
	user = frappe.session.user
	if user == "Guest":
		frappe.throw(_("Login required"), frappe.PermissionError)

	limit = min(100, max(1, cint(limit) or 20))
	# Prefer CRM Booking rows if any; else recent Events owned by the agent
	rows = frappe.get_all(
		"CRM Booking",
		filters={"agent_user": user},
		fields=[
			"name",
			"guest_name",
			"guest_email",
			"guest_phone",
			"starts_on",
			"ends_on",
			"status",
			"provider",
			"meeting_provider",
			"meeting_link",
			"event",
		],
		order_by="starts_on desc",
		limit_page_length=limit,
	)
	if rows:
		return rows

	events = frappe.get_all(
		"Event",
		filters={"owner": user, "status": ["!=", "Cancelled"]},
		fields=["name", "subject", "starts_on", "ends_on", "status", "location"],
		order_by="starts_on desc",
		limit_page_length=limit,
	)
	out = []
	for ev in events:
		out.append(
			{
				"name": ev.name,
				"guest_name": ev.subject,
				"guest_email": "",
				"guest_phone": "",
				"starts_on": ev.starts_on,
				"ends_on": ev.ends_on,
				"status": "Scheduled" if ev.status != "Cancelled" else "Cancelled",
				"provider": "Native",
				"meeting_provider": "None",
				"meeting_link": ev.location or "",
				"event": ev.name,
			}
		)
	return out


@frappe.whitelist(allow_guest=True)
def get_public_booking(slug: str) -> dict:
	"""Resolve public booking: Calendly overlay or frappe_appointment schedule URL."""
	slug = sanitize_slug(slug)
	if not slug:
		frappe.throw(_("Booking page not found"), frappe.DoesNotExistError)

	# Calendly overlay by CRM slug
	crm = frappe.db.get_value(
		"CRM Booking Profile",
		{"slug": slug, "enabled": 1, "provider": "Calendly"},
		["page_title", "calendly_url", "user_name", "user"],
		as_dict=True,
	)
	if crm and (crm.calendly_url or "").strip():
		return {
			"slug": slug,
			"page_title": crm.page_title or _("Book a meeting"),
			"provider": "Calendly",
			"calendly_url": crm.calendly_url,
			"agent_name": crm.user_name,
			"meeting_provider": "None",
		}

	if appointment_installed():
		uaa = frappe.db.get_value(
			"User Appointment Availability",
			{"slug": slug, "enable_scheduling": 1},
			["user", "meeting_provider", "meeting_link"],
			as_dict=True,
		)
		if uaa:
			full_name = frappe.db.get_value("User", uaa.user, "full_name") or uaa.user
			return {
				"slug": slug,
				"page_title": _("Meet with {0}").format(full_name),
				"provider": "Native",
				"calendly_url": None,
				"agent_name": full_name,
				"meeting_provider": uaa.meeting_provider or "None",
				"schedule_url": f"{get_url()}/schedule/in/{slug}",
			}

	frappe.throw(_("Booking page not found"), frappe.DoesNotExistError)


@frappe.whitelist(allow_guest=True)
def get_public_slots(slug: str, date: str | None = None) -> dict:
	"""Deprecated for native — use frappe_appointment schedule UI. Kept for Calendly-only sites."""
	_ = (slug, date)
	return {"date": date, "slots": [], "timezone": "UTC"}


@frappe.whitelist(allow_guest=True)
def create_public_booking(
	slug: str,
	date: str,
	time: str,
	guest_name: str,
	guest_email: str | None = None,
	guest_phone: str | None = None,
	guest_notes: str | None = None,
) -> dict:
	"""Native booking happens on /schedule — this endpoint is not used with frappe_appointment."""
	_ = (slug, date, time, guest_name, guest_email, guest_phone, guest_notes)
	frappe.throw(
		_("Please book via the schedule page."),
		frappe.ValidationError,
	)
