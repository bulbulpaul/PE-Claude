import * as cdk from 'aws-cdk-lib';
import * as ecr from 'aws-cdk-lib/aws-ecr';
import { Construct } from 'constructs';
import { EnvironmentConfig } from '../config/environments';

export interface PeGptEcrStackProps extends cdk.StackProps {
  environment: string;
  config: EnvironmentConfig;
}

export class PeGptEcrStack extends cdk.Stack {
  public readonly repository: ecr.IRepository;

  constructor(scope: Construct, id: string, props: PeGptEcrStackProps) {
    super(scope, id, props);

    // 既存のECRリポジトリをインポート
    this.repository = ecr.Repository.fromRepositoryName(
      this, 'PeGptRepository', props.config.ecrConfig.repositoryName
    );

    new cdk.CfnOutput(this, 'RepositoryUri', {
      value: this.repository.repositoryUri,
      description: 'ECR Repository URI',
    });
  }
}
