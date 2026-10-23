#!/usr/bin/env python3
"""Smoke-test one Bedrock Converse call in the selected Region (read: 1 call).

Explicit maxTokens is mandatory in this codebase (Bedrock quota rule).
"""

from __future__ import annotations

import json
import sys

import boto3
from botocore.exceptions import BotoCoreError, ClientError

REGION = "ap-southeast-2"
MODEL = sys.argv[1] if len(sys.argv) > 1 else "amazon.nova-2-lite-v1:0"


def main() -> int:
    client = boto3.Session(region_name=REGION).client("bedrock-runtime", region_name=REGION)
    try:
        resp = client.converse(
            modelId=MODEL,
            system=[{"text": "You are a fictional veteran in a training simulation. Reply with ONE JSON object only."}],
            messages=[{"role": "user", "content": [{"text": 'Say hello as the prospect: {"prospect_line": "...", "event": "none", "mood": "ENGAGED"}'}]}],
            inferenceConfig={"maxTokens": 200, "temperature": 0.7},
        )
    except (BotoCoreError, ClientError) as e:
        print(f"CONVERSE_FAILED [{MODEL}]: {e}")
        return 1
    text = "".join(p.get("text", "") for p in resp.get("output", {}).get("message", {}).get("content", []))
    usage = resp.get("usage", {})
    print(f"MODEL_OK: {MODEL}")
    print(f"RESPONSE: {text[:300]}")
    print(f"USAGE: {json.dumps(usage)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
