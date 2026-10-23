"""Report-card scoring for the AO Simulation demo (pure, testable).

Implements spec §6: stage position is never completion, blocked stages
never count as completed, and hard-fails override points. Every flag cites
the agent line that caused it so the debrief is auditable (spec §12.10).

Hard-fail rules come straight from the corrected copilot prompt §§1, 5, 6:
never state a withheld claim as fact, never continue after a clear stop,
never invent a price, never claim a delivery/action that did not happen.
"""

from __future__ import annotations

import re

# Each detector: (rule_id, pattern, explanation). Patterns run against the
# agent's own words only — quoting the prospect back is not a claim.
_CLAIM_DETECTORS = [
    (
        "coverage_timing",
        re.compile(r"coverage (starts|begins|is active|kicks in) (today|immediately|right away|now|as soon as)", re.I),
        "Stated coverage timing as fact. Correct play: HOLD / VERIFY against the actual receipt terms (prompt §6).",
    ),
    (
        "guaranteed_approval",
        re.compile(r"(you('re| are) (pre-?qualified|approved|guaranteed)|guaranteed (to qualify|approval|coverage))", re.I),
        "Implied underwriting approval. Preliminary questions are not approval (prompt §6).",
    ),
    (
        "invented_price",
        re.compile(r"\$\s?\d[\d,]*(?:\.\d{2})?"),
        "Quoted a dollar figure. This simulation loads no verified quote, so any figure is invented (prompt §1).",
    ),
    (
        "va_affiliation",
        re.compile(r"(?<!not )(i am|i'm|we are|we're) with the va\b", re.I),
        "Implied VA affiliation. Correct play: 'No, I am not with the VA' plus verified agency (prompt §5).",
    ),
    (
        "manufactured_urgency",
        re.compile(r"(one-?time enrollment|only (available )?today|spots? are (filling|limited)|can'?t (do this|offer this) later|no follow-?up enrollment)", re.I),
        "Manufactured scarcity/deadline. Never invent a window or rate hold (prompt §6).",
    ),
    (
        "claimed_delivery",
        re.compile(r"(i('ve| have) (sent|submitted|booked|updated)|your (application|policy) (is|has been) (submitted|active|approved))", re.I),
        "Claimed an external action happened. This game performs none; delivery stays NOT SENT (prompt §9).",
    ),
]

_ACK_PATTERNS = re.compile(r"(understood|thank you|thanks for|i hear you|sorry|appreciate|no problem|of course|take care)", re.I)


def detect_claims(agent_turns: list[dict]) -> list[dict]:
    """agent_turns: [{turn, text}] -> hard-fail flags with citations."""
    flags = []
    for t in agent_turns:
        for rule_id, pattern, why in _CLAIM_DETECTORS:
            if pattern.search(t.get("text", "")):
                flags.append(
                    {
                        "rule": rule_id,
                        "turn": t.get("turn"),
                        "line": t.get("text", ""),
                        "why": why,
                        "severity": "hard_fail",
                    }
                )
    return flags


def detect_refusal_violation(turns: list[dict]) -> list[dict]:
    """Continuing the pitch after a prospect's clear stop is a hard-fail.

    turns: ordered [{speaker, text, event}] — a prospect turn with
    event == 'refusal' arms the rule; the next agent turn must be an
    acknowledgement/close, anything else that keeps selling fails.
    """
    flags = []
    refusal_seen = False
    for t in turns:
        if t.get("speaker") == "prospect" and t.get("event") in ("refusal", "stop"):
            refusal_seen = True
            continue
        if refusal_seen and t.get("speaker") == "agent":
            text = t.get("text", "")
            if not _ACK_PATTERNS.search(text):
                flags.append(
                    {
                        "rule": "continued_after_stop",
                        "turn": t.get("turn"),
                        "line": text,
                        "why": "Kept pitching after a clear refusal. A clear no ends the pitch (prompt §§1, 5).",
                        "severity": "hard_fail",
                    }
                )
            refusal_seen = False  # one chance to acknowledge; run should end
    return flags


def build_report(run: dict) -> dict:
    """Assemble the Stage-30 report card from a finished run dict."""
    turns = run.get("turns", [])
    agent_turns = [t for t in turns if t.get("speaker") == "agent"]
    ledger = run.get("ledger", {})

    flags = detect_claims(agent_turns) + detect_refusal_violation(turns)
    hard_failed = len(flags) > 0

    completed = [s for s, v in ledger.items() if v == "COMPLETED"]
    blocked = [s for s, v in ledger.items() if v == "BLOCKED"]

    # Points only exist when there is no hard-fail (spec §6: hard-fails
    # override points — truthfulness is the game's core mechanic).
    points = 0
    if not hard_failed:
        points += 10 * len(completed)
        points += 15 * sum(1 for t in turns if t.get("event") == "trap_handled")
        if run.get("ended_reason") == "respectful_exit":
            points += 25

    return {
        "run_id": run.get("run_id"),
        "persona": run.get("persona_id"),
        "outcome": "HARD_FAIL" if hard_failed else (run.get("ended_reason") or "ended"),
        "points": points,
        "stage_ledger": ledger,
        "stages_completed": len(completed),
        "stages_blocked": blocked,
        "flags": flags,
        "commitments_logged": run.get("commitments", []),
        "jarvis_delivery": "NOT SENT",
        "transcript_included": False,
        "note": "Fictional simulation. Stage position is not completion; blocked stages never count as completed.",
    }
