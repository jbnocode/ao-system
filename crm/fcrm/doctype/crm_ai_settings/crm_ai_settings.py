# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from frappe.model.document import Document

from crm.ai.providers import PROVIDER_BEDROCK, apply_provider_defaults, bedrock_base_url


class CRMAISettings(Document):
	def validate(self):
		apply_provider_defaults(self)
		if self.provider == PROVIDER_BEDROCK:
			# Always pin Bedrock to the Runtime OpenAI-compat endpoint for the region
			self.base_url = bedrock_base_url(self.aws_region)
