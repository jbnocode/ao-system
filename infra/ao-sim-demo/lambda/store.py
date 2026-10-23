"""Run storage for the AO Simulation demo.

DynamoDB in AWS (single table, whole run as one JSON item, 7-day TTL);
in-memory locally so the game logic is testable without AWS. boto3 is
imported lazily — it ships with the Lambda runtime, not with local Python.
"""

from __future__ import annotations

import json
import time


class MemoryStore:
    def __init__(self):
        self._runs = {}

    def put(self, run: dict) -> None:
        self._runs[run["run_id"]] = run

    def get(self, run_id: str) -> dict | None:
        return self._runs.get(run_id)


class DynamoStore:
    def __init__(self, table_name: str):
        import boto3  # Lambda runtime only

        self._table = boto3.resource("dynamodb").Table(table_name)

    def put(self, run: dict) -> None:
        self._table.put_item(
            Item={
                "PK": f"RUN#{run['run_id']}",
                "SK": "META",
                "data": json.dumps(run),
                "expiresAt": int(time.time()) + 7 * 24 * 3600,
            }
        )

    def get(self, run_id: str) -> dict | None:
        resp = self._table.get_item(Key={"PK": f"RUN#{run_id}", "SK": "META"})
        item = resp.get("Item")
        return json.loads(item["data"]) if item else None


def default_store():
    import os

    table = os.environ.get("TABLE_NAME", "")
    return DynamoStore(table) if table else MemoryStore()
