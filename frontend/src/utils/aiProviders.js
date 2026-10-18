/** Client-side helpers mirroring crm.ai.providers presets. */

export const PROVIDER_OPENAI = 'OpenAI'
export const PROVIDER_BEDROCK = 'Amazon Bedrock'
export const PROVIDER_OPENROUTER = 'OpenRouter'
export const PROVIDER_CUSTOM = 'Custom'

export const DEFAULT_OPENAI_BASE = 'https://api.openai.com/v1'
export const DEFAULT_OPENAI_MODEL = 'gpt-4o-mini'
export const DEFAULT_BEDROCK_REGION = 'us-east-1'
export const DEFAULT_BEDROCK_MODEL = 'openai.gpt-oss-20b-1:0'
export const DEFAULT_OPENROUTER_BASE = 'https://openrouter.ai/api/v1'
export const DEFAULT_OPENROUTER_MODEL = 'openrouter/free'

export function bedrockBaseUrl(region = DEFAULT_BEDROCK_REGION) {
  const r = String(region || DEFAULT_BEDROCK_REGION).trim() || DEFAULT_BEDROCK_REGION
  return `https://bedrock-runtime.${r}.amazonaws.com/openai/v1`
}

export function resolveBaseUrl(provider, baseUrl, awsRegion) {
  if (provider === PROVIDER_BEDROCK) return bedrockBaseUrl(awsRegion)
  if (provider === PROVIDER_OPENROUTER) {
    const raw = String(baseUrl || '')
      .trim()
      .replace(/\/+$/, '')
    return raw || DEFAULT_OPENROUTER_BASE
  }
  const raw = String(baseUrl || '')
    .trim()
    .replace(/\/+$/, '')
  return raw || DEFAULT_OPENAI_BASE
}

export function applyProviderPreset(form, provider) {
  const next = { ...form, provider }
  if (provider === PROVIDER_BEDROCK) {
    next.aws_region = next.aws_region || DEFAULT_BEDROCK_REGION
    next.base_url = bedrockBaseUrl(next.aws_region)
    if (
      !next.model ||
      next.model === DEFAULT_OPENAI_MODEL ||
      next.model.startsWith('gpt-') ||
      next.model.includes('openrouter') ||
      next.model.includes(':free')
    ) {
      next.model = DEFAULT_BEDROCK_MODEL
    }
  } else if (provider === PROVIDER_OPENROUTER) {
    next.base_url = DEFAULT_OPENROUTER_BASE
    if (
      !next.model ||
      next.model === DEFAULT_OPENAI_MODEL ||
      next.model.includes('gpt-oss') ||
      next.model.startsWith('gpt-')
    ) {
      next.model = DEFAULT_OPENROUTER_MODEL
    }
  } else if (provider === PROVIDER_OPENAI) {
    next.base_url = DEFAULT_OPENAI_BASE
    if (
      !next.model ||
      next.model.includes('gpt-oss') ||
      next.model.includes('bedrock') ||
      next.model.includes('openrouter') ||
      next.model.includes(':free')
    ) {
      next.model = DEFAULT_OPENAI_MODEL
    }
  }
  return next
}
