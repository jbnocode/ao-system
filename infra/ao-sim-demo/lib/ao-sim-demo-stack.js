const cdk = require('aws-cdk-lib');
const { RemovalPolicy, Duration } = cdk;
const s3 = require('aws-cdk-lib/aws-s3');
const s3deploy = require('aws-cdk-lib/aws-s3-deployment');
const cloudfront = require('aws-cdk-lib/aws-cloudfront');
const origins = require('aws-cdk-lib/aws-cloudfront-origins');
const dynamodb = require('aws-cdk-lib/aws-dynamodb');
const lambda = require('aws-cdk-lib/aws-lambda');
const logs = require('aws-cdk-lib/aws-logs');
const iam = require('aws-cdk-lib/aws-iam');
const secretsmanager = require('aws-cdk-lib/aws-secretsmanager');
const apigwv2 = require('aws-cdk-lib/aws-apigatewayv2');
const integrations = require('aws-cdk-lib/aws-apigatewayv2-integrations');
const path = require('path');

/**
 * D1 skeleton only: site host, turn API front door, game-state table.
 * Bedrock/Polly/Transcribe permissions are wired but the game brain (D2)
 * and voice pipeline (D4) land in later slices. Everything is DESTROY-
 * friendly: this stack is a demo, `cdk destroy` must leave nothing behind.
 */
class AoSimDemoStack extends cdk.Stack {
  constructor(scope, id, props) {
    super(scope, id, props);

    // --- Game state -------------------------------------------------------
    // Single-table design: RUN#<id> / TURN#<n> / REPORT#<id>. TTL so demo
    // data self-deletes even if teardown is forgotten (best practice).
    const table = new dynamodb.Table(this, 'RunsTable', {
      partitionKey: { name: 'PK', type: dynamodb.AttributeType.STRING },
      sortKey: { name: 'SK', type: dynamodb.AttributeType.STRING },
      billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
      timeToLiveAttribute: 'expiresAt',
      removalPolicy: RemovalPolicy.DESTROY,
    });

    // OpenAI Platform key holder. CDK creates the secret EMPTY of any real
    // key (generated placeholder); the owner pastes the Platform key in the
    // console before first AI use. The key never appears in code, template
    // values, or the browser. Rotation = console update + Lambda restart.
    const openAiSecret = new secretsmanager.Secret(this, 'OpenAiApiKey', {
      secretName: 'ao-sim-demo/openai-api-key',
      description: 'OpenAI Platform API key for the AO sim demo brain. Paste the real key in the console.',
      removalPolicy: RemovalPolicy.DESTROY,
    });

    // --- Game brain (Lambda) ---------------------------------------------
    // Python to match the team's Frappe/Bedrock (boto3 Converse) stack.
    // IAM role only — no API keys anywhere in this demo.
    const api = new lambda.Function(this, 'ApiFunction', {
      runtime: lambda.Runtime.PYTHON_3_12,
      handler: 'api.handler',
      code: lambda.Code.fromAsset(path.join(__dirname, '..', 'lambda')),
      memorySize: 512,
      timeout: Duration.seconds(60),
      logGroup: new logs.LogGroup(this, 'ApiLogGroup', {
        retention: logs.RetentionDays.ONE_WEEK,
        removalPolicy: RemovalPolicy.DESTROY,
      }),
      environment: {
        TABLE_NAME: table.tableName,
        // Retained Bedrock path (quotas are 0 on this FREE project today);
        // handler must send an explicit maxTokens on every Converse call.
        BEDROCK_MODEL_ID: process.env.AO_SIM_MODEL_ID || 'PLACEHOLDER_SET_AT_PREDEPLOY_GATE',
        // Primary demo brain: OpenAI Platform key from Secrets Manager.
        OPENAI_SECRET_ARN: openAiSecret.secretArn,
        OPENAI_MODEL: process.env.AO_SIM_OPENAI_MODEL || 'gpt-4o-mini',
        GAME_REGION: this.region,
      },
    });
    table.grantReadWriteData(api);
    openAiSecret.grantRead(api);
    // Scope to the verified model ARN at the pre-deploy gate; '*' is a
    // demo-skeleton placeholder, never a production permission.
    api.addToRolePolicy(
      new iam.PolicyStatement({
        actions: ['bedrock:InvokeModel', 'bedrock:InvokeModelWithResponseStream', 'bedrock:Converse'],
        resources: ['*'],
      }),
    );
    // --- Turn API ----------------------------------------------------------
    // HTTP API (not REST): ~70% cheaper per request, lower latency, and the
    // game needs no API keys/usage plans. CORS is wide-open ONLY because
    // this is a disposable demo; production narrows to the real origin.
    const httpApi = new apigwv2.HttpApi(this, 'GameApi', {
      apiName: 'ao-sim-demo',
      corsPreflight: {
        allowOrigins: ['*'],
        allowMethods: [apigwv2.CorsHttpMethod.GET, apigwv2.CorsHttpMethod.POST],
        allowHeaders: ['content-type'],
      },
    });
    const apiIntegration = new integrations.HttpLambdaIntegration('ApiIntegration', api);
    httpApi.addRoutes({ path: '/health', methods: [apigwv2.HttpMethod.GET], integration: apiIntegration });
    httpApi.addRoutes({ path: '/runs', methods: [apigwv2.HttpMethod.POST], integration: apiIntegration });
    httpApi.addRoutes({ path: '/runs/{runId}/turns', methods: [apigwv2.HttpMethod.POST], integration: apiIntegration });
    httpApi.addRoutes({ path: '/runs/{runId}/end', methods: [apigwv2.HttpMethod.POST], integration: apiIntegration });
    // --- Open-source voice (D4 revised, opt-in) ----------------------------
    // Kokoro TTS + faster-whisper STT in a container Lambda. Building the
    // image needs Docker, so it is behind AO_SIM_VOICE=1: the default stack
    // synths/deploys without it, voice routes appear when enabled.
    if (process.env.AO_SIM_VOICE === '1') {
      const voiceFn = new lambda.DockerImageFunction(this, 'VoiceFunction', {
        code: lambda.DockerImageCode.fromImageAsset(path.join(__dirname, '..', 'lambda-voice')),
        memorySize: 3008,
        timeout: Duration.seconds(120),
        ephemeralStorageSize: cdk.Size.gibibytes(2),
        logGroup: new logs.LogGroup(this, 'VoiceLogGroup', {
          retention: logs.RetentionDays.ONE_WEEK,
          removalPolicy: RemovalPolicy.DESTROY,
        }),
        environment: { TABLE_NAME: table.tableName },
      });
      table.grantReadData(voiceFn);
      const voiceIntegration = new integrations.HttpLambdaIntegration('VoiceIntegration', voiceFn);
      httpApi.addRoutes({ path: '/runs/{runId}/voice-out', methods: [apigwv2.HttpMethod.POST], integration: voiceIntegration });
      httpApi.addRoutes({ path: '/runs/{runId}/voice-in', methods: [apigwv2.HttpMethod.POST], integration: voiceIntegration });
    }

    // --- Demo site ---------------------------------------------------------
    // DESTROY + autoDeleteObjects together, or a non-empty bucket survives
    // `cdk destroy` (CDK pitfall flagged in the aws-cdk skill).
    const siteBucket = new s3.Bucket(this, 'SiteBucket', {
      blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
      encryption: s3.BucketEncryption.S3_MANAGED,
      removalPolicy: RemovalPolicy.DESTROY,
      autoDeleteObjects: true,
    });
    const distribution = new cloudfront.Distribution(this, 'SiteDistribution', {
      defaultRootObject: 'index.html',
      defaultBehavior: {
        origin: origins.S3BucketOrigin.withOriginAccessControl(siteBucket),
        viewerProtocolPolicy: cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
      },
      // SPA fallback: game routes are client-side in D3.
      errorResponses: [{ httpStatus: 403, responseHttpStatus: 200, responsePagePath: '/index.html' }],
    });
    new s3deploy.BucketDeployment(this, 'DeploySite', {
      sources: [s3deploy.Source.asset(path.join(__dirname, '..', 'web'))],
      destinationBucket: siteBucket,
      distribution,
      distributionPaths: ['/*'],
    });

    new cdk.CfnOutput(this, 'ApiUrl', { value: httpApi.apiEndpoint });
    new cdk.CfnOutput(this, 'SiteUrl', { value: `https://${distribution.domainName}` });
    new cdk.CfnOutput(this, 'RunsTableName', { value: table.tableName });
    new cdk.CfnOutput(this, 'Region', { value: this.region });
  }
}

module.exports = { AoSimDemoStack };
