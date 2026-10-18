import { describe, expect, it } from 'vitest'
import {
  DEFAULT_BEDROCK_MODEL,
  DEFAULT_OPENAI_MODEL,
  PROVIDER_BEDROCK,
  PROVIDER_OPENAI,
  applyProviderPreset,
  bedrockBaseUrl,
  resolveBaseUrl,
} from '../../src/utils/aiProviders'

describe('aiProviders', () => {
  it('builds bedrock runtime openai-compat url', () => {
    expect(bedrockBaseUrl('us-west-2')).toBe(
      'https://bedrock-runtime.us-west-2.amazonaws.com/openai/v1',
    )
  })

  it('resolves base url by provider', () => {
    expect(resolveBaseUrl(PROVIDER_BEDROCK, 'https://ignored', 'eu-west-1')).toBe(
      'https://bedrock-runtime.eu-west-1.amazonaws.com/openai/v1',
    )
    expect(resolveBaseUrl(PROVIDER_OPENAI, 'https://api.openai.com/v1/', '')).toBe(
      'https://api.openai.com/v1',
    )
  })

  it('applies bedrock preset', () => {
    const next = applyProviderPreset(
      { provider: PROVIDER_OPENAI, model: 'gpt-4o-mini', aws_region: '' },
      PROVIDER_BEDROCK,
    )
    expect(next.provider).toBe(PROVIDER_BEDROCK)
    expect(next.aws_region).toBe('us-east-1')
    expect(next.base_url).toContain('bedrock-runtime.us-east-1')
    expect(next.model).toBe(DEFAULT_BEDROCK_MODEL)
  })

  it('applies openai preset from bedrock model', () => {
    const next = applyProviderPreset(
      {
        provider: PROVIDER_BEDROCK,
        model: 'openai.gpt-oss-20b-1:0',
        base_url: 'https://bedrock-runtime.us-east-1.amazonaws.com/openai/v1',
      },
      PROVIDER_OPENAI,
    )
    expect(next.model).toBe(DEFAULT_OPENAI_MODEL)
    expect(next.base_url).toBe('https://api.openai.com/v1')
  })
})
