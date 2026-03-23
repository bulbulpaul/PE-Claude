import * as cdk from 'aws-cdk-lib';
import * as ecr from 'aws-cdk-lib/aws-ecr';
import { Construct } from 'constructs';
import { EnvironmentConfig } from '../config/environments';

export interface PeGptEcrStackProps extends cdk.StackProps {
  environment: string;
  config: EnvironmentConfig;
}

export class PeGptEcrStack extends cdk.Stack {
  public readonly repository: ecr.Repository;

  constructor(scope: Construct, id: string, props: PeGptEcrStackProps) {
    super(scope, id, props);

    this.repository = new ecr.Repository(this, 'PeGptRepository', {
      repositoryName: props.config.ecrConfig.repositoryName,
      removalPolicy: cdk.RemovalPolicy.RETAIN,
      lifecycleRules: [
        {
          maxImageCount: props.config.ecrConfig.imageRetentionCount,
          description: 'Keep only recent images',
        },
      ],
    });

    new cdk.CfnOutput(this, 'RepositoryUri', {
      value: this.repository.repositoryUri,
      description: 'ECR Repository URI',
      exportName: `${props.environment}-PeGptRepositoryUri`,
    });

    new cdk.CfnOutput(this, 'RepositoryArn', {
      value: this.repository.repositoryArn,
      description: 'ECR Repository ARN',
      exportName: `${props.environment}-PeGptRepositoryArn`,
    });
  }
}
