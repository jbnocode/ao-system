# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import annotations

import frappe
import requests
from frappe import _


class VapiClient:
	"""Thin wrapper around Vapi REST API."""

	def __init__(self, api_key: str | None = None, base_url: str = "https://api.vapi.ai"):
		settings = frappe.get_single("CRM Vapi Settings")
		self.api_key = api_key or _private_key(settings)
		self.base_url = (base_url or "https://api.vapi.ai").rstrip("/")
		if not self.api_key:
			frappe.throw(_("Vapi private API key is not configured. Add it in Settings → Vapi."))

	def _headers(self) -> dict:
		return {
			"Authorization": f"Bearer {self.api_key}",
			"Content-Type": "application/json",
		}

	def request(self, method: str, path: str, payload: dict | None = None) -> dict | list:
		url = f"{self.base_url}{path}"
		try:
			resp = requests.request(
				method,
				url,
				headers=self._headers(),
				json=payload,
				timeout=45,
			)
		except requests.RequestException as exc:
			frappe.throw(_("Vapi request failed: {0}").format(str(exc)[:200]))

		if resp.status_code >= 400:
			detail = _error_detail(resp)
			frappe.throw(_("Vapi error ({0}): {1}").format(resp.status_code, detail))

		if not resp.content:
			return {}
		try:
			return resp.json()
		except Exception:
			return {"raw": resp.text}

	def list_phone_numbers(self) -> list:
		data = self.request("GET", "/phone-number")
		return data if isinstance(data, list) else []

	def import_twilio_number(
		self,
		number: str,
		twilio_account_sid: str,
		twilio_auth_token: str,
		assistant_id: str | None = None,
		name: str | None = None,
	) -> dict:
		payload = {
			"provider": "twilio",
			"number": number,
			"twilioAccountSid": twilio_account_sid,
			"twilioAuthToken": twilio_auth_token,
		}
		if assistant_id:
			payload["assistantId"] = assistant_id
		if name:
			payload["name"] = name
		return self.request("POST", "/phone-number", payload)

	def update_phone_number(self, phone_id: str, payload: dict) -> dict:
		return self.request("PATCH", f"/phone-number/{phone_id}", payload)

	def create_assistant(self, payload: dict) -> dict:
		return self.request("POST", "/assistant", payload)

	def update_assistant(self, assistant_id: str, payload: dict) -> dict:
		return self.request("PATCH", f"/assistant/{assistant_id}", payload)

	def get_assistant(self, assistant_id: str) -> dict:
		return self.request("GET", f"/assistant/{assistant_id}")

	def create_call(self, payload: dict) -> dict:
		return self.request("POST", "/call", payload)

	def list_calls(self, params: dict | None = None) -> list:
		query = ""
		if params:
			from urllib.parse import urlencode

			filtered = {k: v for k, v in params.items() if v not in (None, "")}
			if filtered:
				query = "?" + urlencode(filtered)
		data = self.request("GET", f"/call{query}")
		return data if isinstance(data, list) else []


def _private_key(settings) -> str:
	try:
		return settings.get_password("private_api_key") or ""
	except Exception:
		return ""


def _error_detail(resp) -> str:
	try:
		data = resp.json()
		if isinstance(data, dict):
			return str(data.get("message") or data.get("error") or data)[:300]
		return str(data)[:300]
	except Exception:
		return (resp.text or "Unknown error")[:300]


def get_client() -> VapiClient:
	settings = frappe.get_single("CRM Vapi Settings")
	if not settings.enabled:
		frappe.throw(_("Vapi is disabled. Enable it in Settings → Vapi."))
	return VapiClient()
