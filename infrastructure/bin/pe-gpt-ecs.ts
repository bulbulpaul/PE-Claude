#!/usr/bin/env node
import 'source-map-support/register';
import * as cdk from 'aws-cdk-lib';
import { PeGptEcsStack } from '../lib/pe-gpt-ecs-stack';
import { getEnvironmentConfig } from '../config/environments';

const app = new cdk.App();

// 環境設定を取得
const environment = app.node.tryGetContext('environment') || 'development';
const config = getEnvironmentConfig(environment);

new PeGptEcsStack(app, `PeGptEcsStack-${environment}`, {
  env: {
    account: process.env.CDK_DEFAULT_ACCOUNT,
    region: process.env.CDK_DEFAULT_REGION || config.region,
  },
  environment: environment,
  config: config,
});