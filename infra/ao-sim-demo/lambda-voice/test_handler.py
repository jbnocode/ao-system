"""Unit tests for the open-source voice handler (engines faked).

Run: python3 -m unittest test_handler -v  (from this directory)
soundfile/faster-whisper/kokoro are only imported inside the engine
functions, so routing/sensitive-stage logic tests need no model files.
"""

import base64
import io
import json
import unittest

import handler


class _Seg:
    def __init__(self, text):
        self.text = text


class _FakeWhisper:
    def transcribe(self, audio, language="en", beam_size=1):
        return [_Seg(" hello "), _Seg("veteran ")], None


def _event(path, body):
    return {"rawPath": path, "requestContext": {"http": {"method": "POST"}}, "body": json.dumps(body)}


class TestVoiceHandler(unittest.TestCase):
    def setUp(self):
        handler._run_stage_index_orig = handler._run_stage_index

    def tearDown(self):
        handler._run_stage_index = handler._run_stage_index_orig

    def test_transcribe_joins_segments(self):
        out = handler.transcribe(base64.b64encode(b"audio").decode(), engine=_FakeWhisper())
        self.assertEqual(out["text"], "hello veteran")

    def test_sensitive_stage_blocks_voice_in_and_out(self):
        handler._run_stage_index = lambda run_id: 27  # Application · Pause capture
        resp_in = handler.handler(_event("/runs/abc/voice-in", {"audio_base64": "AA=="}))
        resp_out = handler.handler(_event("/runs/abc/voice-out", {"text": "hello"}))
        self.assertEqual(resp_in["statusCode"], 403)
        self.assertEqual(resp_out["statusCode"], 403)

    def test_unknown_run_404(self):
        handler._run_stage_index = lambda run_id: -1
        resp = handler.handler(_event("/runs/nope/voice-out", {"text": "hello"}))
        self.assertEqual(resp["statusCode"], 404)


if __name__ == "__main__":
    unittest.main()
