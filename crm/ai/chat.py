# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import annotations

import json

import frappe
import requests
from frappe import _

from crm.ai.automation_schema import schema_for_prompt
from crm.ai.credits import consume, ensure_balance, get_balance, get_settings
from crm.ai.demo import demo_response
from crm.ai.providers import (
	PROVIDER_BEDROCK,
	PROVIDER_OPENROUTER,
	normalize_provider,
	provider_catalog,
	resolve_base_url,
)


@frappe.whitelist()
def chat(messages=None, context=None) -> dict:
	"""Credit-gated chat. context.type: general | automation_builder."""
	settings = get_settings()
	if not settings.enabled:
		frappe.throw(_("AI is disabled. Ask an admin to enable CRM AI Settings."))

	messages = _parse_json(messages, [])
	context = _parse_json(context, {}) or {}
	if not isinstance(messages, list) or not messages:
		frappe.throw(_("messages is required"))

	user = frappe.session.user
	ensure_balance(user)
	cost = int(settings.credits_per_request or 1)
	balance = int(frappe.db.get_value("CRM AI Credit Balance", user, "credits") or 0)
	if cost > 0 and balance < cost:
		frappe.throw(
			_("Not enough AI credits ({0} left). Ask an admin to top up.").format(balance)
		)

	last_user = _last_user_text(messages)
	context_type = (context.get("type") or "general").lower()
	api_key = _api_key(settings)

	# Deterministic quote/policy tables (Unlock-style) before calling the LLM
	if context_type != "automation_builder":
		try:
			from crm.ai.insurance_context import get_insurance_snapshot, insurance_reply_for_prompt

			insurance = insurance_reply_for_prompt(last_user, get_insurance_snapshot())
		except Exception:
			insurance = None
		if insurance:
			remaining = consume(
				user,
				cost,
				context_type=context_type,
				message_preview=last_user,
				status="Success",
			)
			insurance["credits"] = remaining
			insurance["credits_spent"] = cost
			insurance.setdefault("demo", False)
			insurance.setdefault("blocks", [])
			return insurance

	if not api_key:
		if not settings.allow_offline_demo:
			frappe.throw(_("No AI API key configured. Add one in CRM AI Settings."))
		result = demo_response(last_user, context)
		remaining = consume(
			user,
			cost,
			context_type=context_type,
			message_preview=last_user,
			status="Demo",
		)
		result["credits"] = remaining
		result["credits_spent"] = cost
		return result

	try:
		llm = _call_openai(settings, api_key, messages, context)
	except Exception as exc:
		consume(
			user,
			0,
			context_type=context_type,
			message_preview=last_user,
			status="Failed",
		)
		frappe.throw(_("AI provider error: {0}").format(str(exc)[:200]))

	remaining = consume(
		user,
		cost,
		context_type=context_type,
		message_preview=last_user,
		status="Success",
		tokens_in=llm.get("tokens_in"),
		tokens_out=llm.get("tokens_out"),
	)
	payload = llm.get("payload") or {"reply": llm.get("reply") or "", "ops": [], "blocks": []}
	payload.setdefault("blocks", [])
	payload["credits"] = remaining
	payload["credits_spent"] = cost
	payload["demo"] = False
	return payload


@frappe.whitelist()
def get_ai_status() -> dict:
	settings = get_settings()
	bal = get_balance()
	provider = normalize_provider(getattr(settings, "provider", None))
	return {
		**bal,
		"has_api_key": bool(_api_key(settings)),
		"allow_offline_demo": bool(settings.allow_offline_demo),
		"model": settings.model,
		"provider": provider,
		"aws_region": getattr(settings, "aws_region", None) or "",
		"base_url": resolve_base_url(
			provider,
			getattr(settings, "base_url", None),
			getattr(settings, "aws_region", None),
		),
	}


@frappe.whitelist()
def get_provider_catalog() -> dict:
	"""Presets for Settings → AI (OpenAI / Bedrock / Custom)."""
	return provider_catalog()


@frappe.whitelist()
def test_ai_connection() -> dict:
	"""Smoke-test the configured provider with a tiny chat completion."""
	frappe.only_for("System Manager")
	settings = get_settings()
	api_key = _api_key(settings)
	if not api_key:
		frappe.throw(_("Add an API key in CRM AI Settings first."))

	provider = normalize_provider(getattr(settings, "provider", None))
	base = resolve_base_url(
		provider,
		getattr(settings, "base_url", None),
		getattr(settings, "aws_region", None),
	)
	model = (settings.model or "").strip() or "gpt-4o-mini"
	url = f"{base.rstrip('/')}/chat/completions"
	try:
		resp = requests.post(
			url,
			headers={
				"Authorization": f"Bearer {api_key}",
				"Content-Type": "application/json",
			},
			json={
				"model": model,
				"messages": [
					{"role": "user", "content": "Reply with exactly: ok"},
				],
				"temperature": 0,
				"max_tokens": 16,
			},
			timeout=45,
		)
		if resp.status_code >= 400:
			detail = _http_error_detail(resp, provider)
			frappe.throw(_("AI provider error: {0}").format(detail))
		data = resp.json()
		content = (
			((data.get("choices") or [{}])[0].get("message") or {}).get("content") or ""
		).strip()
		return {
			"ok": True,
			"provider": provider,
			"base_url": base,
			"model": model,
			"reply_preview": content[:120],
		}
	except frappe.ValidationError:
		raise
	except Exception as exc:
		frappe.throw(_("AI provider error: {0}").format(str(exc)[:240]))


def _api_key(settings) -> str:
	try:
		return settings.get_password("api_key") or ""
	except Exception:
		return ""


def _last_user_text(messages) -> str:
	for msg in reversed(messages):
		if isinstance(msg, dict) and msg.get("role") == "user":
			return str(msg.get("content") or "")
	return ""


def _parse_json(value, default):
	if value is None or value == "":
		return default
	if isinstance(value, (dict, list)):
		return value
	try:
		return json.loads(value)
	except Exception:
		return default


def _call_openai(settings, api_key: str, messages: list, context: dict) -> dict:
	provider = normalize_provider(getattr(settings, "provider", None))
	base = resolve_base_url(
		provider,
		getattr(settings, "base_url", None),
		getattr(settings, "aws_region", None),
	)
	url = f"{base}/chat/completions"
	system = _system_prompt(context)
	payload_messages = [{"role": "system", "content": system}]
	for msg in messages[-20:]:
		if not isinstance(msg, dict):
			continue
		role = msg.get("role") or "user"
		if role not in ("user", "assistant", "system"):
			role = "user"
		payload_messages.append({"role": role, "content": str(msg.get("content") or "")})

	# Include snapshot for automation builder
	if (context.get("type") or "").lower() == "automation_builder" and context.get("snapshot"):
		payload_messages.append(
			{
				"role": "system",
				"content": "Current automation snapshot:\n"
				+ json.dumps(context.get("snapshot"), default=str)[:6000],
			}
		)

	model = (settings.model or "").strip() or "gpt-4o-mini"
	headers = {
		"Authorization": f"Bearer {api_key}",
		"Content-Type": "application/json",
	}
	if provider == PROVIDER_OPENROUTER:
		# Recommended by OpenRouter for ranking / free-tier routing.
		site = (frappe.utils.get_url() or "").rstrip("/") or "https://ao-crm.local"
		headers["HTTP-Referer"] = site
		headers["X-Title"] = "AO CRM"
	resp = requests.post(
		url,
		headers=headers,
		json={
			"model": model,
			"messages": payload_messages,
			"temperature": 0.3,
		},
		timeout=60,
	)
	if resp.status_code >= 400:
		frappe.throw(_("AI provider error: {0}").format(_http_error_detail(resp, provider)))
	data = resp.json()
	choices = data.get("choices") or []
	if not choices:
		frappe.throw(_("AI provider returned no choices"))
	content = (choices[0].get("message") or {}).get("content") or ""
	usage = data.get("usage") or {}
	parsed = _extract_json(content)
	return {
		"payload": parsed,
		"reply": parsed.get("reply") or content,
		"tokens_in": usage.get("prompt_tokens"),
		"tokens_out": usage.get("completion_tokens"),
	}


def _http_error_detail(resp, provider: str) -> str:
	status = resp.status_code
	body = (resp.text or "")[:300]
	hint = ""
	if provider == PROVIDER_BEDROCK:
		if status in (401, 403):
			hint = (
				" Check the Bedrock API key, model access in this region, "
				"and that Chat Completions is enabled for the model."
			)
		elif status == 404:
			hint = " Confirm the AWS region and model ID support OpenAI Chat Completions."
	return f"HTTP {status}: {body}{hint}"


def _system_prompt(context: dict) -> str:
	context_type = (context.get("type") or "general").lower()
	if context_type == "automation_builder":
		return (
			"You are an AO CRM automation builder assistant. "
			+ schema_for_prompt()
			+ " Always respond with a single JSON object with keys reply, ops, and blocks."
		)

	insurance_blob = ""
	try:
		from crm.ai.insurance_context import get_insurance_snapshot

		snap = get_insurance_snapshot(limit=20)
		if snap.get("quotes") or snap.get("policies"):
			insurance_blob = (
				"\nInsurance records the user can see (do not invent missing rows):\n"
				+ json.dumps(snap, default=str)[:6000]
				+ "\n"
			)
	except Exception:
		insurance_blob = ""

	blocks_hint = (
		'Respond as JSON: {"reply": "...", "ops": [], "blocks": []}. '
		"When listing quotes or policies, include a blocks entry: "
		'{"type":"table","title":"...","columns":["Carrier","Product",...],"rows":[["…"],...]}. '
		"For “generate quotes” style asks without live carrier rates, say they are indicative "
		"and still return a helpful comparison table in blocks."
	)

	if context_type == "home" or context.get("briefing"):
		briefing_data = context.get("briefing") or context.get("snapshot") or {}
		briefing = json.dumps(briefing_data, default=str)[:5000]
		return (
			"You are AO CRM's home assistant for a life-insurance / sales CRM. "
			"Help with tasks, cold leads, meetings, deals/cases, quotes, policies, and daily priorities. "
			"Be concise and actionable. Use the briefing JSON for the user's current data; "
			"do not invent records that are not listed. "
			"If they want to build an automation, tell them to open Automations. "
			f"\nBriefing:\n{briefing}\n"
			f"{insurance_blob}"
			f"{blocks_hint}"
		)
	return (
		"You are a helpful assistant for AO CRM (Frappe CRM). "
		"Answer briefly about leads, deals, tasks, quotes, policies, and settings. "
		"If the user wants to build an automation, tell them to open Automations and use the Assistant there. "
		f"{insurance_blob}"
		f"{blocks_hint}"
	)


def _extract_json(content: str) -> dict:
	text = (content or "").strip()
	if text.startswith("```"):
		lines = text.split("\n")
		lines = [l for l in lines if not l.strip().startswith("```")]
		text = "\n".join(lines).strip()
	try:
		data = json.loads(text)
		if isinstance(data, dict):
			data.setdefault("ops", [])
			data.setdefault("blocks", [])
			data.setdefault("reply", "")
			return data
	except Exception:
		pass
	# Try to find a JSON object in the text
	start, end = text.find("{"), text.rfind("}")
	if start >= 0 and end > start:
		try:
			data = json.loads(text[start : end + 1])
			if isinstance(data, dict):
				data.setdefault("ops", [])
				data.setdefault("blocks", [])
				data.setdefault("reply", "")
				return data
		except Exception:
			pass
	return {"reply": content, "ops": [], "blocks": []}
