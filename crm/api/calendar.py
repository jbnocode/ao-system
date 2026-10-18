# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import get_request_site_address


def _is_system_manager() -> bool:
	return "System Manager" in frappe.get_roles()


def _can_configure_google_api() -> bool:
	"""Managers may set site Google OAuth; agents only connect their own calendar."""
	roles = set(frappe.get_roles())
	return bool(roles & {"System Manager", "Sales Manager"})


def _redirect_uri() -> str:
	callback = "frappe.integrations.doctype.google_calendar.google_calendar.google_callback"
	try:
		base = get_request_site_address(full_address=True)
	except RuntimeError:
		base = frappe.utils.get_url()
	return f"{base}?cmd={callback}"


def _calendar_for_user(user: str | None = None) -> str | None:
	user = user or frappe.session.user
	return frappe.db.get_value("Google Calendar", {"user": user}, "name")


def _get_own_calendar(name: str | None = None):
	"""Load the current user's Google Calendar row (ownership enforced)."""
	user = frappe.session.user
	name = name or _calendar_for_user(user)
	if not name:
		return None
	doc = frappe.get_doc("Google Calendar", name)
	if doc.user != user and not _is_system_manager():
		frappe.throw(_("Not allowed"), frappe.PermissionError)
	return doc


@frappe.whitelist()
def get_google_calendar_status() -> dict:
	"""Return Google API + current user's calendar connection status for Settings."""
	settings = frappe.get_cached_doc("Google Settings")
	calendar = None
	doc = _get_own_calendar()
	if doc:
		calendar = {
			"name": doc.name,
			"calendar_name": doc.calendar_name,
			"enable": bool(doc.enable),
			"pull_from_google_calendar": bool(doc.pull_from_google_calendar),
			"push_to_google_calendar": bool(doc.push_to_google_calendar),
			"sync_as_public": bool(doc.sync_as_public),
			"google_calendar_id": doc.google_calendar_id,
			"connected": bool(doc.refresh_token),
		}

	can_configure = _can_configure_google_api()
	return {
		"can_configure_api": can_configure,
		"api_enabled": bool(settings.enable),
		"has_client_id": bool(settings.client_id),
		"has_client_secret": bool(
			settings.get_password(fieldname="client_secret", raise_exception=False)
		),
		"client_id": settings.client_id if can_configure else None,
		"redirect_uri": _redirect_uri(),
		"docs_url": "https://docs.frappe.io/framework/user/en/guides/integration/google_calendar",
		"calendar": calendar,
	}


@frappe.whitelist()
def save_google_settings(
	enable: int | str | bool = 0,
	client_id: str | None = None,
	client_secret: str | None = None,
) -> dict:
	"""Sales Manager / System Manager: enable Google API and save OAuth client credentials."""
	if not _can_configure_google_api():
		frappe.throw(
			_("Only Sales Managers or System Managers can configure Google Settings."),
			frappe.PermissionError,
		)

	settings = frappe.get_doc("Google Settings")
	settings.enable = 1 if frappe.utils.cint(enable) else 0
	if client_id is not None:
		settings.client_id = (client_id or "").strip()
	# Leave blank to keep the existing secret
	if client_secret:
		settings.client_secret = client_secret
	settings.save(ignore_permissions=True)
	frappe.clear_cache(doctype="Google Settings")
	return get_google_calendar_status()


@frappe.whitelist()
def ensure_my_google_calendar(
	calendar_name: str | None = None,
	pull_from_google_calendar: int | str | bool = 1,
	push_to_google_calendar: int | str | bool = 1,
	sync_as_public: int | str | bool = 0,
) -> dict:
	"""Create or update the current user's Google Calendar connection row."""
	user = frappe.session.user
	if user == "Guest":
		frappe.throw(_("Login required"), frappe.PermissionError)

	settings = frappe.get_cached_doc("Google Settings")
	if not settings.enable:
		frappe.throw(_("Enable Google API in Calendar settings first."))
	if not settings.client_id or not settings.get_password(
		fieldname="client_secret", raise_exception=False
	):
		frappe.throw(_("Enter Client ID and Client Secret in Calendar settings first."))

	full_name = frappe.db.get_value("User", user, "full_name") or user
	default_name = f"{full_name} Calendar"
	# Sales User may lack Desk User / Google Calendar perms — own-row only via ignore_permissions.
	doc = _get_own_calendar()

	if doc:
		if calendar_name:
			doc.calendar_name = calendar_name.strip()
		doc.enable = 1
		doc.pull_from_google_calendar = 1 if frappe.utils.cint(pull_from_google_calendar) else 0
		doc.push_to_google_calendar = 1 if frappe.utils.cint(push_to_google_calendar) else 0
		doc.sync_as_public = 1 if frappe.utils.cint(sync_as_public) else 0
		doc.save(ignore_permissions=True)
	else:
		doc = frappe.get_doc(
			{
				"doctype": "Google Calendar",
				"enable": 1,
				"calendar_name": (calendar_name or default_name).strip(),
				"user": user,
				"pull_from_google_calendar": 1 if frappe.utils.cint(pull_from_google_calendar) else 0,
				"push_to_google_calendar": 1 if frappe.utils.cint(push_to_google_calendar) else 0,
				"sync_as_public": 1 if frappe.utils.cint(sync_as_public) else 0,
			}
		)
		doc.insert(ignore_permissions=True)

	return get_google_calendar_status()


@frappe.whitelist()
def authorize_my_google_calendar(reauthorize: int | str | bool = 0) -> dict:
	"""Return the Google OAuth URL for the current user's calendar connection."""
	_ = reauthorize  # kept for API compatibility with the Connect / Reconnect button
	doc = _get_own_calendar()
	if not doc:
		status = ensure_my_google_calendar()
		name = (status.get("calendar") or {}).get("name")
		doc = _get_own_calendar(name) if name else None
	if not doc:
		frappe.throw(_("Could not create Google Calendar connection"))

	from frappe.integrations.doctype.google_calendar.google_calendar import (
		get_authentication_url,
	)

	# Always open Google consent from CRM (callback finishes the token exchange).
	google_settings = frappe.get_cached_doc("Google Settings")
	frappe.cache.hset("google_calendar", "google_calendar", doc.name)
	return get_authentication_url(
		client_id=google_settings.client_id, redirect_uri=_redirect_uri()
	)

@frappe.whitelist()
def sync_my_google_calendar() -> dict:
	"""Pull events from Google for the current user's connected calendar."""
	doc = _get_own_calendar()
	if not doc:
		frappe.throw(_("Connect Google Calendar first."))
	if not doc.refresh_token:
		frappe.throw(_("Authorize Google Calendar Access first."))

	from frappe.integrations.doctype.google_calendar.google_calendar import (
		sync_events_from_google_calendar,
	)

	message = sync_events_from_google_calendar(doc.name)
	return {"messages": [message] if message else [], "status": get_google_calendar_status()}
