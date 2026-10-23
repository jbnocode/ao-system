#!/usr/bin/env python3
"""Pre-deploy check: caller identity + Bedrock text models in the selected Region.

Read-only. Run with the demo venv:  .venv/bin/python scripts/check_models.py
Credentials come from the standard boto3 chain (aws login session). No keys
are read from files or printed; only the account id and model ids are shown.
"""

from __future__ import annotations

import sys

import boto3
from botocore.exceptions import BotoCoreError, ClientError

REGION = "ap-southeast-2"


def main() -> int:
    session = boto3.Session(region_name=REGION)
    try:
        ident = session.client("sts").get_caller_identity()
    except (BotoCoreError, ClientError) as e:
        print(f"STS_FAILED: {e}")
        print("Likely fix: run `aws login` again (session in ~/.aws/config may be expired).")
        return 1
    print(f"ACCOUNT: {ident['Account']}")
    print(f"REGION: {REGION}")

    bedrock = session.client("bedrock", region_name=REGION)
    try:
        models = bedrock.list_foundation_models(byOutputModality="TEXT")["modelSummaries"]
    except (BotoCoreError, ClientError) as e:
        print(f"BEDROCK_LIST_FAILED: {e}")
        return 1

    candidates = [
        m["modelId"]
        for m in models
        if m.get("modelLifecycle", {}).get("status") == "ACTIVE"
        and any(k in m["modelId"].lower() for k in ("nova", "claude", "gpt-oss", "llama", "mistral"))
    ]
    print("TEXT_MODEL_CANDIDATES:")
    for mid in sorted(candidates):
        print(f"  {mid}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
