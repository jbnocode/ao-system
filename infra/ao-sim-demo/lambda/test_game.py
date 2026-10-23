"""Unit tests for the D2 game brain (pure logic, scripted fallback).

Run: python3 -m unittest test_game -v   (from this directory)
No boto3 / AWS needed: apply_turn with model_id='' uses scripted personas.
"""

import unittest

from api import make_handler
import json

from brain import apply_turn
from game_data import PERSONAS, STAGES
from scoring import build_report, detect_claims


def fresh_run(persona="P1"):
    p = PERSONAS[persona]
    return {
        "run_id": "test123",
        "persona_id": persona,
        "stage_index": 0,
        "ledger": {},
        "commitments": [],
        "ended": False,
        "ended_reason": "",
        "turns": [{"speaker": "prospect", "text": p["opening"], "turn": 1, "event": "opening"}],
    }


class TestData(unittest.TestCase):
    def test_thirty_stages_one_sensitive(self):
        self.assertEqual(len(STAGES), 30)
        self.assertEqual([s["title"] for s in STAGES if s["sensitive"]], ["Application · Pause capture"])


class TestScriptedGame(unittest.TestCase):
    def test_p1_opening_beats_advance(self):
        run = fresh_run("P1")
        out = apply_turn(run, "Hi, can you hear me okay? How is your day going?")
        self.assertEqual(out["prospect"]["event"], "none")
        self.assertFalse(out["ended"])

    def test_p6_respectful_exit_on_acknowledgement(self):
        run = fresh_run("P6")
        apply_turn(run, "Hi, what were you hoping to get from today?")  # beat 0
        apply_turn(run, "We can review the information you requested.")  # refusal lands
        self.assertEqual(run["turns"][-1]["event"], "refusal")
        out = apply_turn(run, "Understood. Thank you for your time.")
        self.assertTrue(out["ended"])
        self.assertEqual(run["ended_reason"], "respectful_exit")
        report = build_report(run)
        self.assertEqual(report["outcome"], "respectful_exit")
        self.assertGreater(report["points"], 0)

    def test_p6_pitching_after_refusal_hard_fails(self):
        run = fresh_run("P6")
        apply_turn(run, "Hi, what were you hoping to get from today?")
        apply_turn(run, "We can review the information you requested.")  # refusal
        apply_turn(run, "But this is really important, let me just show you the plans.")  # violation
        report = build_report(run)
        self.assertEqual(report["outcome"], "HARD_FAIL")
        self.assertEqual(report["points"], 0)
        self.assertTrue(any(f["rule"] == "continued_after_stop" for f in report["flags"]))


class TestHardFails(unittest.TestCase):
    def _report_for_agent_line(self, line):
        run = fresh_run("P1")
        run["turns"].append({"speaker": "agent", "text": line, "turn": 2, "event": "agent"})
        return build_report(run)

    def test_coverage_timing_claim_fails(self):
        r = self._report_for_agent_line("Your coverage starts today once we submit this.")
        self.assertEqual(r["outcome"], "HARD_FAIL")
        self.assertTrue(any(f["rule"] == "coverage_timing" for f in r["flags"]))

    def test_invented_price_fails(self):
        r = self._report_for_agent_line("It is only $135 a month for you.")
        self.assertTrue(any(f["rule"] == "invented_price" for f in r["flags"]))

    def test_correct_va_answer_does_not_fail(self):
        flags = detect_claims([{"turn": 1, "text": "No, I am not with the VA. Let me clarify my agency."}])
        self.assertFalse(any(f["rule"] == "va_affiliation" for f in flags))

    def test_report_never_claims_delivery(self):
        r = self._report_for_agent_line("Let's review the actual terms together.")
        self.assertEqual(r["jarvis_delivery"], "NOT SENT")
        self.assertFalse(r["transcript_included"])


class TestApi(unittest.TestCase):
    def setUp(self):
        self.handler = make_handler(model_id="")

    def _call(self, path, method, body=None):
        event = {
            "rawPath": path,
            "requestContext": {"http": {"method": method}},
            "body": json.dumps(body or {}),
        }
        resp = self.handler(event)
        return resp["statusCode"], json.loads(resp["body"])

    def test_full_run_flow(self):
        status, run = self._call("/runs", "POST", {"persona_id": "P6"})
        self.assertEqual(status, 201)
        rid = run["run_id"]
        self._call(f"/runs/{rid}/turns", "POST", {"agent_text": "Hi, what were you hoping for?"})
        self._call(f"/runs/{rid}/turns", "POST", {"agent_text": "We can review what you requested."})
        status, out = self._call(f"/runs/{rid}/turns", "POST", {"agent_text": "Understood. Thank you for your time."})
        self.assertEqual(status, 200)
        self.assertTrue(out["ended"])
        status, report = self._call(f"/runs/{rid}/end", "POST")
        self.assertEqual(report["outcome"], "respectful_exit")

    def test_health_advertises_scripted_fallback(self):
        status, body = self._call("/health", "GET")
        self.assertEqual(status, 200)
        self.assertFalse(body["ai_available"])


class _FakeResp:
    def __init__(self, payload):
        self._payload = payload

    def read(self):
        return json.dumps(self._payload).encode()

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


class TestOpenAIAdapter(unittest.TestCase):
    def test_chat_parses_json_mode_response(self):
        import llm

        captured = {}

        def opener(req, timeout=30):
            captured["url"] = req.full_url
            captured["auth"] = req.headers.get("Authorization")
            body = json.loads(req.data.decode())
            captured["format"] = body.get("response_format")
            return _FakeResp({"choices": [{"message": {"content": '{"prospect_line": "hi"}'}}]})

        out = llm.openai_chat("sys", "user", api_key="sk-test", opener=opener)
        self.assertIn("prospect_line", out)
        self.assertEqual(captured["auth"], "Bearer sk-test")
        self.assertEqual(captured["format"], {"type": "json_object"})

    def test_make_chat_prefers_openai_then_bedrock_then_none(self):
        import llm

        self.assertIsNotNone(llm.make_chat(api_key="sk-test"))
        self.assertIsNotNone(llm.make_chat(model_id="some-model"))
        self.assertIsNone(llm.make_chat())

    def test_ai_turn_uses_chat_callable(self):
        def fake_chat(system, user, max_tokens=300):
            if "playing a FICTIONAL veteran" in system:
                return '{"prospect_line": "Alright, go on.", "event": "none", "mood": "ENGAGED"}'
            return '{"stage_index": 0, "next_line": "Keep going.", "prospect": "ENGAGED", "objection_reply": "", "watch_out": "", "promises": []}'

        run = fresh_run("P1")
        out = apply_turn(run, "Can you hear me okay?", chat=fake_chat)
        self.assertEqual(out["prospect"]["prospect_line"], "Alright, go on.")
        self.assertEqual(out["coach"]["source"], "ai")

    def test_ai_outage_falls_back_to_scripted(self):
        def broken_chat(system, user, max_tokens=300):
            raise RuntimeError("provider down")

        run = fresh_run("P1")
        out = apply_turn(run, "Can you hear me okay?", chat=broken_chat)
        self.assertEqual(out["prospect"]["event"], "none")  # scripted P1 beat


if __name__ == "__main__":
    unittest.main()
