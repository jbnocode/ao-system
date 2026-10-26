#!/usr/bin/env python3
"""Print `export OPENAI_API_KEY=...` from local CRM AI Settings (stdout only)."""

from __future__ import annotations

import os
import sys


def main() -> int:
	sites = os.path.expanduser("~/frappe-bench/sites")
	if not os.path.isdir(sites):
		print("echo 'CRM sites path not found' >&2", file=sys.stderr)
		return 1

	os.chdir(sites)
	sys.path.insert(0, os.path.expanduser("~/frappe-bench/apps/frappe"))
	# Prefer bench env if available
	bench_env = os.path.expanduser("~/frappe-bench/env/bin/python")
	if sys.executable != bench_env and os.path.exists(bench_env):
		print(
			f"echo 'Re-run with: {bench_env} {os.path.abspath(__file__)}' >&2",
			file=sys.stderr,
		)

	import frappe

	frappe.init(site="crm.localhost")
	frappe.connect()
	try:
		doc = frappe.get_single("CRM AI Settings")
		key = doc.get_password("api_key") or ""
	finally:
		frappe.destroy()

	if not key:
		print("echo 'No api_key on CRM AI Settings' >&2", file=sys.stderr)
		return 1

	# Shell-safe single quotes
	escaped = key.replace("'", "'\"'\"'")
	print(f"export OPENAI_API_KEY='{escaped}'")
	return 0


if __name__ == "__main__":
	raise SystemExit(main())
