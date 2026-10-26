# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""Thin OpenAI Live REST client (requests)."""

from __future__ import annotations

import json

import frappe
import requests
from frappe import _


class LiveClient:
	def __init__(self, api_key: str | None = None):
		settings = frappe.get_single("CRM Live Settings")
		self.api_key = api_key or _openai_key(settings)
		if not self.api_key:
			frappe.throw(_("OpenAI API key is not configured. Add it in Settings → AI Live."))
		self.base = "https://api.openai.com/v1"

	def _headers(self) -> dict:
		return {
			"Authorization": f"Bearer {self.api_key}",
			"Content-Type": "application/json",
		}

	def request(self, method: str, path: str, payload: dict | None = None) -> dict:
		url = f"{self.base}{path}"
		try:
			resp = requests.request(
				method,
				url,
				headers=self._headers(),
				json=payload,
				timeout=60,
			)
		except requests.RequestException as exc:
			frappe.throw(_("OpenAI Live request failed: {0}").format(str(exc)[:200]))

		if resp.status_code >= 400:
			detail = _error_detail(resp)
			frappe.throw(_("OpenAI Live error ({0}): {1}").format(resp.status_code, detail))

		if not resp.content:
			return {}
		try:
			return resp.json()
		except Exception:
			return {"raw": resp.text}

	def create_webrtc_session(self, sdp: str, session: dict) -> dict:
		return self.request(
			"POST",
			"/live/sessions",
			{"session": session, "transport": {"type": "webrtc", "sdp": sdp}},
		)

	def create_sip_session(self, session: dict, transport: dict) -> dict:
		return self.request(
			"POST",
			"/live/sessions",
			{"session": session, "transport": transport},
		)

	def create_prompt_voice(self, name: str, prompt: str) -> dict:
		return self.request(
			"POST",
			"/audio/voices",
			{
				"name": name,
				"prompt": prompt,
			},
		)

	def list_voices(self) -> list:
		data = self.request("GET", "/audio/voices")
		if isinstance(data, dict):
			return data.get("data") or data.get("voices") or []
		return data if isinstance(data, list) else []


def _openai_key(settings) -> str:
	try:
		return settings.get_password("openai_api_key") or ""
	except Exception:
		return ""


def _error_detail(resp) -> str:
	try:
		data = resp.json()
		if isinstance(data, dict):
			err = data.get("error") or data
			if isinstance(err, dict):
				return str(err.get("message") or err)[:300]
			return str(err)[:300]
		return str(data)[:300]
	except Exception:
		return (resp.text or "Unknown error")[:300]


def get_client() -> LiveClient:
	settings = frappe.get_single("CRM Live Settings")
	if not settings.enabled:
		frappe.throw(_("AI Live is disabled. Enable it in Settings → AI Live."))
	return LiveClient()
