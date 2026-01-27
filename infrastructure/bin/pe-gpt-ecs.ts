#!/usr/bin/env node
import 'source-map-support/register';
import * as cdk from 'aws-cdk-lib';
import { PeGptEcrStack } from '../lib/pe-gpt-ecr-stack';
import { PeGptEcsStack } from '../lib/pe-gpt-ecs-stack';
import { getEnvironmentConfig } from '../config/environments';

const app = new cdk.App();

// 環境設定を取得
const environment = app.node.tryGetContext('environment') || 'development';
const config = getEnvironmentConfig(environment);

const envProps = {
  account: process.env.CDK_DEFAULT_ACCOUNT,
  region: process.env.CDK_DEFAULT_REGION || config.region,
};

// ECR スタック（リポジトリのみ）
const ecrStack = new PeGptEcrStack(app, `PeGptEcrStack-${environment}`, {
  env: envProps,
  environment: environment,
  config: config,
});

// ECS スタック（アプリケーション）
new PeGptEcsStack(app, `PeGptEcsStack-${environment}`, {
  env: envProps,
  environment: environment,
  config: config,
  repository: ecrStack.repository,
});
