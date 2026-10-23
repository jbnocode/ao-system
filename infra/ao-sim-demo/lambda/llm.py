"""LLM chat adapter for the game brain (D2 revised).

Provider decision 2026-10-20: OpenAI API (Platform key) is the demo brain —
strict JSON outputs for the prospect/coach contracts, cheap mini model per
turn, and the CRM already defaults to OpenAI. Bedrock is retained as a
callable with the same (system, user, max_tokens) -> text shape, for when
this project's Bedrock quotas are ever raised above 0.

Important: a ChatGPT/OpenAI Business workspace subscription is NOT API
access. This adapter needs a Platform API key (platform.openai.com),
delivered to Lambda via Secrets Manager — never via code, env plaintext
in the template, or the browser.

No third-party deps: urllib only, so the zip Lambda stays small and the
adapter is testable with a fake opener.
"""

from __future__ import annotations

import json
import os
import urllib.request

OPENAI_URL = "https://api.openai.com/v1/chat/completions"
DEFAULT_MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")


def _post(url: str, payload: dict, api_key: str, *, opener=None, timeout: int = 30) -> dict:
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"},
        method="POST",
    )
    open_fn = opener or urllib.request.urlopen
    with open_fn(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode())


def openai_chat(system: str, user: str, *, api_key: str, model: str = "", max_tokens: int = 300, opener=None) -> str:
    """One chat completion that must answer as a JSON object."""
    resp = _post(
        OPENAI_URL,
        {
            "model": model or DEFAULT_MODEL,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "max_tokens": max_tokens,
            "temperature": 0.7,
            "response_format": {"type": "json_object"},
        },
        api_key,
        opener=opener,
    )
    return resp["choices"][0]["message"]["content"] or ""


def bedrock_chat(system: str, user: str, *, model_id: str, max_tokens: int = 300, client=None) -> str:
    """Bedrock Converse equivalent (retained path). maxTokens explicit."""
    if client is None:
        import boto3  # Lambda runtime only; lazy by design

        client = boto3.client("bedrock-runtime")
    resp = client.converse(
        modelId=model_id,
        system=[{"text": system}],
        messages=[{"role": "user", "content": [{"text": user}]}],
        inferenceConfig={"maxTokens": max_tokens, "temperature": 0.7},
    )
    parts = resp.get("output", {}).get("message", {}).get("content", [])
    return "".join(p.get("text", "") for p in parts)


def resolve_api_key() -> str:
    """OPENAI_API_KEY env (local dev) or Secrets Manager (deployed)."""
    key = os.environ.get("OPENAI_API_KEY", "")
    if key:
        return key
    arn = os.environ.get("OPENAI_SECRET_ARN", "")
    if not arn:
        return ""
    import boto3  # Lambda runtime only

    client = boto3.client("secretsmanager")
    return client.get_secret_value(SecretId=arn).get("SecretString", "") or ""


def make_chat(*, api_key: str = "", model_id: str = "", opener=None):
    """Return a (system, user, max_tokens) -> text callable, or None.

    None means: no usable brain configured -> callers use the scripted
    fallback and health reports ai_available=false (acceptance check 1).
    OpenAI wins when a key exists; Bedrock is used when a model id is set.
    """
    if api_key:
        return lambda system, user, max_tokens=300: openai_chat(
            system, user, api_key=api_key, max_tokens=max_tokens, opener=opener
        )
    if model_id:
        return lambda system, user, max_tokens=300: bedrock_chat(
            system, user, model_id=model_id, max_tokens=max_tokens
        )
    return None
