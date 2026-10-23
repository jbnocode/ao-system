"""Prospect + coach brain for the AO Simulation demo (D2).

Two separate AI jobs, never merged (spec §7):
  A. Prospect engine — plays the fictional veteran.
  B. Coach — v2.2 copilot rules; suggestion only, never auto-advances.

Both run on Bedrock Converse with an explicit maxTokens. With no model
configured (local dev, AI outage) a deterministic scripted fallback keeps
the game playable from prepared cards — acceptance check 1 (spec §12).

boto3 is imported lazily: it exists in the Lambda runtime but not in the
local test environment, and the pure logic must stay testable (repo rule).
"""

from __future__ import annotations

import json
import re

from game_data import OBJECTIONS, PERSONAS, stage_card

_ACK = re.compile(r"(understood|thank you|thanks|i hear you|sorry|appreciate|no problem|of course|take care)", re.I)
_HOLD = re.compile(r"(verify|check (the|that|first)|confirm|need to (check|confirm)|not (sure|able to confirm)|look into)", re.I)


def _json_from_text(text: str) -> dict | None:
    if not text:
        return None
    try:
        return json.loads(text)
    except ValueError:
        m = re.search(r"\{[\s\S]*\}", text)
        if not m:
            return None
        try:
            return json.loads(m.group(0))
        except ValueError:
            return None


def converse(system: str, user: str, *, model_id: str, max_tokens: int = 300, client=None) -> str:
    """Compatibility shim: Bedrock Converse via llm.bedrock_chat.
    maxTokens is ALWAYS explicit (Bedrock quota rule)."""
    from llm import bedrock_chat

    return bedrock_chat(system, user, model_id=model_id, max_tokens=max_tokens, client=client)


# ---------------------------------------------------------------- prospect

def _persona(run: dict) -> dict:
    return PERSONAS.get(run.get("persona_id", "P1"), PERSONAS["P1"])


def scripted_prospect(run: dict, agent_text: str) -> dict:
    """Deterministic fallback: walk the persona's scripted beats."""
    persona = _persona(run)
    prospect_turns = [t for t in run["turns"] if t.get("speaker") == "prospect"]
    idx = len(prospect_turns)  # opening already counts as prospect turn 0

    # A clear refusal was the last prospect line: an acknowledgement ends
    # the call respectfully; anything else draws the hard stop.
    if prospect_turns and prospect_turns[-1].get("event") == "refusal":
        if _ACK.search(agent_text or ""):
            return {"prospect_line": "Thank you. Goodbye.", "event": "end", "mood": "DECLINED"}
        return {"prospect_line": persona["beats"][-1] if persona["beats"] else "Please stop calling me.", "event": "stop", "mood": "DECLINED"}

    beats = persona.get("beats", [])
    if idx - 1 < len(beats):
        line = beats[idx - 1]
        event = "none"
        if persona.get("refusal_after") is not None and (idx - 1) == persona["refusal_after"]:
            event = "refusal"
        return {"prospect_line": line, "event": event, "mood": "ENGAGED" if event == "none" else "DECLINED"}
    return {"prospect_line": "Alright, I think I've got what I need. Thanks for walking me through it.", "event": "end", "mood": "ENGAGED"}


def bedrock_prospect(run: dict, agent_text: str, *, model_id: str = "", client=None, chat=None) -> dict:
    persona = _persona(run)
    stage = stage_card(run.get("stage_index", 0))
    recent = "\n".join(f"{t['speaker']}: {t['text']}" for t in run["turns"][-8:])
    system = (
        "You are playing a FICTIONAL veteran in a sales-training simulation. Stay in character. "
        f"Persona: {persona['name']}. Briefing: {persona['briefing']} "
        "Never break character, never mention being an AI, never give real personal data. "
        "If the agent states an unverified product fact, react with a follow-up question, not agreement. "
        'Reply with ONE JSON object only: {"prospect_line": "...", "event": "none|refusal|stop|question", "mood": "ENGAGED|QUESTIONING|HESITATING|DECLINED|UNKNOWN"}'
    )
    user = f"Current stage: {stage['title']}\nConversation so far:\n{recent}\nAgent just said: {agent_text}\nYour next line:"
    text = chat(system, user, 300) if chat else converse(system, user, model_id=model_id, client=client)
    parsed = _json_from_text(text)
    if not parsed or "prospect_line" not in parsed:
        return scripted_prospect(run, agent_text)
    return {
        "prospect_line": str(parsed["prospect_line"])[:600],
        "event": parsed.get("event", "none"),
        "mood": parsed.get("mood", "UNKNOWN"),
    }


# ------------------------------------------------------------------- coach

def scripted_coach(run: dict) -> dict:
    stage = stage_card(run.get("stage_index", 0))
    return {
        "stage_index": stage["index"],
        "next_line": stage["line"],
        "prospect": "UNKNOWN",
        "objection_reply": "",
        "watch_out": stage["watch"],
        "promises": [],
        "source": "prepared_card",
    }


def bedrock_coach(run: dict, prospect_line: str, *, model_id: str = "", client=None, chat=None) -> dict:
    stage = stage_card(run.get("stage_index", 0))
    objections = "; ".join(f"{o['label']}: {o['reply']}" for o in OBJECTIONS)
    system = (
        "You are a private, text-only presentation coach following corrected copilot rules: "
        "honor any stop immediately; never invent coverage timing, prices, eligibility, or VA affiliation; "
        "missing product facts mean HOLD / VERIFY, never a generated disclosure; a stage suggestion is not completion. "
        f"Supported objection replies: {objections}. "
        'Reply with ONE JSON object only: {"stage_index": int, "next_line": "...", "prospect": "ENGAGED|QUESTIONING|HESITATING|DECLINED|UNKNOWN", "objection_reply": "...", "watch_out": "...", "promises": []}'
    )
    recent = "\n".join(f"{t['speaker']}: {t['text']}" for t in run["turns"][-8:])
    user = f"Current stage {stage['index']}: {stage['title']} — prepared line: {stage['line']}\nConversation:\n{recent}\nProspect just said: {prospect_line}\nCoach JSON:"
    text = chat(system, user, 300) if chat else converse(system, user, model_id=model_id, client=client)
    parsed = _json_from_text(text)
    if not parsed or "next_line" not in parsed:
        return scripted_coach(run)
    fallback = scripted_coach(run)
    return {
        "stage_index": max(0, min(int(parsed.get("stage_index", stage["index"])), 29)),
        "next_line": str(parsed["next_line"])[:400],
        "prospect": parsed.get("prospect", "UNKNOWN"),
        "objection_reply": str(parsed.get("objection_reply", ""))[:400],
        "watch_out": str(parsed.get("watch_out", ""))[:300],
        "promises": [str(p)[:120] for p in parsed.get("promises", []) if isinstance(p, str)],
        "source": "ai",
    }


# -------------------------------------------------------------- turn logic

def apply_turn(run: dict, agent_text: str, *, model_id: str = "", bedrock_client=None, chat=None) -> dict:
    """Advance one turn. `chat` is an llm.make_chat callable; when present it
    drives both AI jobs, otherwise the scripted fallback keeps the game
    playable (acceptance check 1). model_id is the retained Bedrock path."""
    agent_text = (agent_text or "").strip()
    turn_no = len(run["turns"]) + 1
    run["turns"].append({"speaker": "agent", "text": agent_text, "turn": turn_no, "event": "agent"})

    # Was the previous prospect turn a trap question (coverage timing etc.)?
    # A HOLD / VERIFY answer is the scored-correct play (spec §6).
    prev_prospect = next((t for t in reversed(run["turns"][:-1]) if t["speaker"] == "prospect"), None)
    if prev_prospect and prev_prospect.get("event") in ("trap", "question") and _HOLD.search(agent_text):
        run["turns"].append({"speaker": "system", "text": "trap_handled", "turn": turn_no, "event": "trap_handled"})

    stage = stage_card(run.get("stage_index", 0))
    run.setdefault("ledger", {})
    if run["ledger"].get(str(stage["index"])) != "BLOCKED":
        run["ledger"][str(stage["index"])] = "COMPLETED"

    use_ai = bool(chat or model_id)
    if use_ai:
        try:
            prospect = bedrock_prospect(run, agent_text, model_id=model_id, client=bedrock_client, chat=chat)
        except Exception:
            prospect = scripted_prospect(run, agent_text)  # AI outage != game outage
    else:
        prospect = scripted_prospect(run, agent_text)
    run["turns"].append(
        {"speaker": "prospect", "text": prospect["prospect_line"], "turn": len(run["turns"]) + 1, "event": prospect["event"]}
    )

    if prospect["event"] in ("end", "stop"):
        run["ended"] = True
        run["ended_reason"] = "respectful_exit" if prospect["event"] == "end" and prev_prospect and prev_prospect.get("event") == "refusal" else "prospect_end"

    if use_ai:
        try:
            coach = bedrock_coach(run, prospect["prospect_line"], model_id=model_id, client=bedrock_client, chat=chat)
        except Exception:
            coach = scripted_coach(run)
    else:
        coach = scripted_coach(run)
    return {"prospect": prospect, "coach": coach, "stage": stage_card(run.get("stage_index", 0)), "ended": bool(run.get("ended"))}
