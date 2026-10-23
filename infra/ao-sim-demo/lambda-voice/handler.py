"""Open-source voice for the AO Simulation demo (D4 revised).

POST /runs/{runId}/voice-out  {text}                    -> {audio_base64, content_type: audio/wav}
POST /runs/{runId}/voice-in   {audio_base64, format}    -> {text}   (synchronous, short turns)

Engines: Kokoro-82M TTS (Apache-2.0) + faster-whisper STT (MIT), both CPU.
Models are baked into the container image (see Dockerfile) — no downloads,
no AWS speech services (Transcribe is SCP-denied in this project; Polly
remains a documented fallback in spec §11, not code).

Sensitive-stage rule (spec §10.4): on the Application stage both routes
return 403 — nothing is voiced or transcribed there.
Engines load lazily on first use and are cached per container.
"""

from __future__ import annotations

import base64
import io
import json
import os
import re

TABLE_NAME = os.environ.get("TABLE_NAME", "")
_kokoro = None
_whisper = None


def _response(status: int, body: dict) -> dict:
    return {"statusCode": status, "headers": {"Content-Type": "application/json"}, "body": json.dumps(body)}


def _run_stage_index(run_id: str) -> int:
    import boto3  # container runtime

    table = boto3.resource("dynamodb").Table(TABLE_NAME)
    item = table.get_item(Key={"PK": f"RUN#{run_id}", "SK": "META"}).get("Item")
    if not item:
        return -1
    return int(json.loads(item["data"]).get("stage_index", 0))


def _is_sensitive(stage_index: int) -> bool:
    return stage_index == 27  # "Application · Pause capture" in game_data.STAGES


def _kokoro_engine():
    global _kokoro
    if _kokoro is None:
        from kokoro_onnx import Kokoro

        _kokoro = Kokoro("/opt/kokoro-v1.0.onnx", "/opt/voices-v1.0.bin")
    return _kokoro


def _whisper_engine():
    global _whisper
    if _whisper is None:
        from faster_whisper import WhisperModel

        _whisper = WhisperModel("tiny", device="cpu", compute_type="int8", download_root="/opt/whisper")
    return _whisper


def synthesize(text: str, *, engine=None) -> dict:
    """Text -> WAV base64. Engine injectable for tests."""
    import soundfile as sf

    kokoro = engine or _kokoro_engine()
    samples, sample_rate = kokoro.create((text or "")[:800], voice="af_sarah", speed=1.0, lang="en-us")
    buf = io.BytesIO()
    sf.write(buf, samples, sample_rate, format="WAV")
    return {"audio_base64": base64.b64encode(buf.getvalue()).decode(), "content_type": "audio/wav"}


def transcribe(audio_base64: str, *, engine=None) -> dict:
    """One short mic turn -> text. Engine injectable for tests."""
    whisper = engine or _whisper_engine()
    audio = io.BytesIO(base64.b64decode(audio_base64))
    segments, _info = whisper.transcribe(audio, language="en", beam_size=1)
    return {"text": "".join(s.text for s in segments).strip()}


def handler(event, context=None):  # noqa: ARG001 — Lambda signature
    path = event.get("rawPath") or ""
    method = (event.get("requestContext", {}).get("http", {}) or {}).get("method", "")
    try:
        body = json.loads(event.get("body") or "{}")
    except ValueError:
        body = {}

    m = re.fullmatch(r"/runs/([\w-]+)/voice-out", path)
    if m and method == "POST":
        stage = _run_stage_index(m.group(1))
        if stage < 0:
            return _response(404, {"error": "run_not_found"})
        if _is_sensitive(stage):
            return _response(403, {"error": "voice_blocked_sensitive_stage"})
        text = str(body.get("text", "")).strip()
        if not text:
            return _response(400, {"error": "text_required"})
        return _response(200, synthesize(text))

    m = re.fullmatch(r"/runs/([\w-]+)/voice-in", path)
    if m and method == "POST":
        stage = _run_stage_index(m.group(1))
        if stage < 0:
            return _response(404, {"error": "run_not_found"})
        if _is_sensitive(stage):
            return _response(403, {"error": "voice_blocked_sensitive_stage"})
        if not body.get("audio_base64"):
            return _response(400, {"error": "audio_base64_required"})
        return _response(200, transcribe(body["audio_base64"]))

    return _response(404, {"error": "not_found", "path": path})
