#!/usr/bin/env python3
"""Read-only Bedrock quota check for the demo models (Service Quotas API)."""

from __future__ import annotations

import sys

import boto3
from botocore.exceptions import BotoCoreError, ClientError

REGION = "ap-southeast-2"
NEEDLES = ("nova lite", "nova micro", "gpt-oss-20b", "tokens per day")


def main() -> int:
    client = boto3.Session(region_name=REGION).client("service-quotas", region_name=REGION)
    try:
        paginator = client.get_paginator("list_service_quotas")
        rows = []
        for page in paginator.paginate(ServiceCode="bedrock"):
            for q in page.get("Quotas", []):
                name = q.get("QuotaName", "")
                low = name.lower()
                if any(n in low for n in NEEDLES):
                    rows.append((name, q.get("Value"), q.get("QuotaCode"), q.get("Adjustable")))
    except (BotoCoreError, ClientError) as e:
        print(f"QUOTA_LIST_FAILED: {e}")
        return 1
    if not rows:
        print("No matching quotas returned (service may not be enabled on this plan).")
        return 0
    for name, value, code, adj in sorted(rows):
        print(f"{name} = {value}  (code={code}, adjustable={adj})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
