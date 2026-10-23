// D1 guardrails: the disposable demo must synth with the resources the
// spec promises — and nothing that would survive teardown or bill while idle.
const test = require('node:test');
const assert = require('node:assert');
const cdk = require('aws-cdk-lib');
const assertions = require('aws-cdk-lib/assertions');
const { AoSimDemoStack } = require('../lib/ao-sim-demo-stack');

function synth() {
  const app = new cdk.App();
  const stack = new AoSimDemoStack(app, 'TestStack', {
    env: { account: '123456789012', region: 'ap-southeast-2' },
  });
  return assertions.Template.fromStack(stack);
}

test('game state table is pay-per-request with TTL', () => {
  const t = synth();
  t.hasResourceProperties('AWS::DynamoDB::Table', {
    BillingMode: 'PAY_PER_REQUEST',
    TimeToLiveSpecification: { AttributeName: 'expiresAt', Enabled: true },
  });
});

test('turn API and brain exist', () => {
  const t = synth();
  t.resourceCountIs('AWS::ApiGatewayV2::Api', 1);
  t.hasResourceProperties('AWS::Lambda::Function', { Handler: 'api.handler', Runtime: 'python3.12' });
});

test('openai key lives in secrets manager, never in lambda env plaintext', () => {
  const t = synth();
  t.resourceCountIs('AWS::S3::Bucket', 1); // site only; voice is a container Lambda
  t.resourceCountIs('AWS::SecretsManager::Secret', 1);
  const tpl = t.toJSON();
  const lambdaEnv = JSON.stringify(Object.values(tpl.Resources).find((r) => r.Type === 'AWS::Lambda::Function').Properties.Environment);
  assert.ok(lambdaEnv.includes('OPENAI_SECRET_ARN'), 'lambda should reference the secret by ARN');
  assert.ok(!lambdaEnv.includes('sk-'), 'no API key material in the template');
});

test('site is private behind CloudFront', () => {
  const t = synth();
  t.resourceCountIs('AWS::CloudFront::Distribution', 1);
  t.hasResourceProperties('AWS::S3::Bucket', {
    PublicAccessBlockConfiguration: {
      BlockPublicAcls: true,
      BlockPublicPolicy: true,
      IgnorePublicAcls: true,
      RestrictPublicBuckets: true,
    },
  });
});
