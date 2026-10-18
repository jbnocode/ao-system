# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""Compact schema summary for automation-builder AI prompts."""

SCHEMA_SUMMARY = """
You help build Automation Flow steps for Frappe CRM.
Return JSON only when proposing changes:
{
  "reply": "short human message",
  "ops": [ ... ]
}

Allowed ops:
- set_meta: { "op": "set_meta", "title"?, "document_type"?, "enabled"? }
- set_trigger: { "op": "set_trigger", "trigger_type", "trigger_field"?, "to_value"?, "from_value"?, "document_type"? }
  trigger_type one of: Doc Created, Doc Updated, Field Value Changed, Scheduled, Date Based, Custom Event
- add_step: { "op": "add_step", "after_id"?, "branch"?: "If"|"Else", "values": { step_type, action_type?, params?, step_condition? } }
  step_type: Action | If | Wait | WaitForEvent
  action_type examples: CreateDocument, SendCRMEmail, SendCRMNotification, AdjustLeadScore, SetLeadTemperature, ConvertLeadToDeal, SetFieldValue
  For Wait: params as JSON string e.g. {"value": 2, "unit": "Days"}
  For CreateDocument CRM Task: params {"doctype":"CRM Task","values":{"title":"..."}}
- patch_step: { "op": "patch_step", "id": "<_id>", "values": { ... } }
- remove_step: { "op": "remove_step", "id": "<_id>" }

If the user only asks a question, return {"reply": "...", "ops": []}.
"""


def schema_for_prompt() -> str:
	return SCHEMA_SUMMARY.strip()
