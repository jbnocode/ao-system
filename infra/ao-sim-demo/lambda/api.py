"""AO Simulation Game demo API.

Routes (spec §11 demo flow):
  GET  /health                  — front-door check (proves API, not Bedrock)
  POST /runs                    — create a fictional run (persona, difficulty)
  POST /runs/{runId}/turns      — one agent turn → prospect reply + coach
  POST /runs/{runId}/end        — freeze and score the Stage-30 report card

Rules from the copilot handoff, enforced here: fictional data only, no
external actions, no transcript content in logs, report exports always
state jarvis_delivery NOT SENT.
"""

from __future__ import annotations

import json
import os
import re
import uuid

from brain import apply_turn
from game_data import PERSONAS, stage_card
from scoring import build_report
from store import MemoryStore, default_store

MODEL_ID = os.environ.get("BEDROCK_MODEL_ID", "")
MODEL_CONFIGURED = bool(MODEL_ID) and MODEL_ID != "PLACEHOLDER_SET_AT_PREDEPLOY_GATE"
REGION = os.environ.get("GAME_REGION", "")


def _response(status: int, body: dict) -> dict:
    return {
        "statusCode": status,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(body),
    }


def _body(event) -> dict:
    try:
        return json.loads(event.get("body") or "{}")
    except ValueError:
        return {}


def make_handler(store=None, model_id: str | None = None, chat=None):
    store = store if store is not None else MemoryStore()
    model = MODEL_ID if model_id is None else model_id
    if not MODEL_CONFIGURED and model_id is None:
        model = ""
    if chat is None and model_id is None and os.environ.get("OPENAI_API_KEY"):
        from llm import make_chat

        chat = make_chat(api_key=os.environ["OPENAI_API_KEY"])

    def handler(event, context=None):  # noqa: ARG001 — Lambda signature
        path = event.get("rawPath") or event.get("path", "")
        method = (event.get("requestContext", {}).get("http", {}) or {}).get("method") or event.get("httpMethod", "")

        if path == "/health" and method == "GET":
            return _response(
                200,
                {
                    "app": "ao-sim-demo",
                    "slice": "D2-brain",
                    "region": REGION,
                    "ai_available": bool(chat or model),
                    "note": "ai_available=false means scripted fallback: prepared cards remain playable (acceptance 1).",
                },
            )

        if path == "/runs" and method == "POST":
            body = _body(event)
            persona_id = body.get("persona_id", "P1")
            if persona_id not in PERSONAS:
                return _response(400, {"error": "unknown_persona", "personas": sorted(PERSONAS)})
            persona = PERSONAS[persona_id]
            run = {
                "run_id": uuid.uuid4().hex[:12],
                "persona_id": persona_id,
                "difficulty": body.get("difficulty", "Guided"),
                "stage_index": 0,
                "ledger": {},
                "commitments": [],
                "ended": False,
                "ended_reason": "",
                "turns": [{"speaker": "prospect", "text": persona["opening"], "turn": 1, "event": "opening"}],
            }
            store.put(run)
            return _response(
                201,
                {
                    "run_id": run["run_id"],
                    "persona": {"id": persona_id, "name": persona["name"], "briefing": persona["briefing"]},
                    "opening": persona["opening"],
                    "stage": stage_card(0),
                    "ai_available": bool(chat or model),
                    "source_set": "PARTIAL",
                    "mode": "Simulation (fictional)",
                },
            )

        m = re.fullmatch(r"/runs/([\w-]+)/turns", path)
        if m and method == "POST":
            run = store.get(m.group(1))
            if not run:
                return _response(404, {"error": "run_not_found"})
            if run.get("ended"):
                return _response(409, {"error": "run_ended"})
            body = _body(event)
            if "stage_index" in body:
                run["stage_index"] = max(0, min(int(body["stage_index"]), 29))
            agent_text = str(body.get("agent_text", "")).strip()
            if not agent_text:
                return _response(400, {"error": "agent_text_required"})
            result = apply_turn(run, agent_text, model_id=model, chat=chat)
            store.put(run)
            return _response(200, {"run_id": run["run_id"], **result})

        # Voice routes live in the separate container Lambda (lambda-voice/,
        # Kokoro + faster-whisper) — see lib stack AO_SIM_VOICE=1 routes.
        m = re.fullmatch(r"/runs/([\w-]+)/end", path)
        if m and method == "POST":
            run = store.get(m.group(1))
            if not run:
                return _response(404, {"error": "run_not_found"})
            run["ended"] = True
            if not run.get("ended_reason"):
                run["ended_reason"] = "agent_ended"
            report = build_report(run)
            store.put(run)
            return _response(200, report)

        return _response(404, {"error": "not_found", "path": path})

    return handler


# Lambda entry point. A module-level MemoryStore fallback is never used in
# AWS (TABLE_NAME is set there -> DynamoStore), only in local invocations.
def _default_handler():
    chat = None
    try:
        from llm import make_chat, resolve_api_key

        chat = make_chat(api_key=resolve_api_key(), model_id=MODEL_ID if MODEL_CONFIGURED else "")
    except Exception:
        chat = None  # no brain configured -> scripted fallback, game still playable
    return make_handler(
        store=default_store() if os.environ.get("TABLE_NAME") else MemoryStore(),
        chat=chat,
    )


handler = _default_handler()
