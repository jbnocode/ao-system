# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""AI provider presets (OpenAI, Amazon Bedrock, custom OpenAI-compatible)."""

from __future__ import annotations

PROVIDER_OPENAI = "OpenAI"
PROVIDER_BEDROCK = "Amazon Bedrock"
PROVIDER_CUSTOM = "Custom"

DEFAULT_OPENAI_BASE = "https://api.openai.com/v1"
DEFAULT_OPENAI_MODEL = "gpt-4o-mini"
DEFAULT_BEDROCK_REGION = "us-east-1"
DEFAULT_BEDROCK_MODEL = "openai.gpt-oss-20b-1:0"

BEDROCK_REGIONS = (
	"ap-southeast-2",
	"us-east-1",
	"us-east-2",
	"us-west-2",
	"eu-west-1",
	"eu-central-1",
	"ap-southeast-1",
	"ap-northeast-1",
)

# Models known to support Bedrock Runtime OpenAI Chat Completions.
# Sites should confirm access in the Bedrock console for their region.
BEDROCK_MODELS = (
	"openai.gpt-oss-20b-1:0",
	"openai.gpt-oss-120b-1:0",
)


def normalize_provider(provider: str | None) -> str:
	value = (provider or "").strip()
	if value in (PROVIDER_OPENAI, PROVIDER_BEDROCK, PROVIDER_CUSTOM):
		return value
	# Infer from an existing base URL (pre-provider field installs)
	return PROVIDER_OPENAI


def bedrock_base_url(region: str | None = None) -> str:
	r = (region or DEFAULT_BEDROCK_REGION).strip() or DEFAULT_BEDROCK_REGION
	return f"https://bedrock-runtime.{r}.amazonaws.com/openai/v1"


def resolve_base_url(
	provider: str | None = None,
	base_url: str | None = None,
	aws_region: str | None = None,
) -> str:
	"""Return the chat-completions base URL (no trailing slash)."""
	p = normalize_provider(provider)
	if p == PROVIDER_BEDROCK:
		return bedrock_base_url(aws_region)
	raw = (base_url or "").strip().rstrip("/")
	if raw:
		return raw
	return DEFAULT_OPENAI_BASE


def default_model_for(provider: str | None) -> str:
	p = normalize_provider(provider)
	if p == PROVIDER_BEDROCK:
		return DEFAULT_BEDROCK_MODEL
	return DEFAULT_OPENAI_MODEL


def apply_provider_defaults(settings) -> None:
	"""Fill base_url / model from provider when switching to Bedrock or OpenAI."""
	provider = normalize_provider(getattr(settings, "provider", None))
	settings.provider = provider
	if provider == PROVIDER_BEDROCK:
		region = (getattr(settings, "aws_region", None) or DEFAULT_BEDROCK_REGION).strip()
		settings.aws_region = region
		settings.base_url = bedrock_base_url(region)
		if not (getattr(settings, "model", None) or "").strip():
			settings.model = DEFAULT_BEDROCK_MODEL
	elif provider == PROVIDER_OPENAI:
		if not (getattr(settings, "base_url", None) or "").strip():
			settings.base_url = DEFAULT_OPENAI_BASE
		if not (getattr(settings, "model", None) or "").strip():
			settings.model = DEFAULT_OPENAI_MODEL


def provider_catalog() -> dict:
	"""JSON-friendly catalog for the settings UI."""
	return {
		"providers": [PROVIDER_OPENAI, PROVIDER_BEDROCK, PROVIDER_CUSTOM],
		"bedrock_regions": list(BEDROCK_REGIONS),
		"bedrock_models": list(BEDROCK_MODELS),
		"defaults": {
			PROVIDER_OPENAI: {
				"base_url": DEFAULT_OPENAI_BASE,
				"model": DEFAULT_OPENAI_MODEL,
			},
			PROVIDER_BEDROCK: {
				"aws_region": DEFAULT_BEDROCK_REGION,
				"base_url": bedrock_base_url(DEFAULT_BEDROCK_REGION),
				"model": DEFAULT_BEDROCK_MODEL,
			},
			PROVIDER_CUSTOM: {
				"base_url": DEFAULT_OPENAI_BASE,
				"model": DEFAULT_OPENAI_MODEL,
			},
		},
	}
