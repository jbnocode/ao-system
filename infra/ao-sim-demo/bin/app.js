#!/usr/bin/env node
// AO Simulation Game — disposable all-AWS demo app.
// Spec: .pi/feats/simulation-game/spec.md §11 (all-AWS demo, ap-southeast-2).
// Deploy is gated: synth/diff locally first, then the pre-deploy checklist
// (Region confirmation, plan/spend-limit, budget alert, model availability).
const cdk = require('aws-cdk-lib');
const { AoSimDemoStack } = require('../lib/ao-sim-demo-stack');

const app = new cdk.App();

const region = process.env.AO_SIM_REGION || 'ap-southeast-2';
// Account stays unset for offline synth; deploy requires CDK_DEFAULT_ACCOUNT
// (from `aws login` session) so we never hardcode an account id in git.
const account = process.env.CDK_DEFAULT_ACCOUNT || undefined;

new AoSimDemoStack(app, 'AoSimDemoStack', {
  env: account ? { account, region } : { region },
  description: 'AO Simulation Game demo (disposable). Spec §11.',
});

app.synth();
