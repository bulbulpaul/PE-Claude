import * as cdk from 'aws-cdk-lib';
import { Template } from 'aws-cdk-lib/assertions';
import * as PeGptEcs from '../lib/pe-gpt-ecs-stack';
import * as PeGptEcr from '../lib/pe-gpt-ecr-stack';
import { getEnvironmentConfig } from '../config/environments';

describe('PeGptEcrStack', () => {
  let app: cdk.App;
  let stack: PeGptEcr.PeGptEcrStack;
  let template: Template;

  beforeEach(() => {
    app = new cdk.App();
    const config = getEnvironmentConfig('development');
    stack = new PeGptEcr.PeGptEcrStack(app, 'EcrTestStack', {
      environment: 'development',
      config: config,
    });
    template = Template.fromStack(stack);
  });

  test('ECR repository is created', () => {
    template.hasResourceProperties('AWS::ECR::Repository', {
      RepositoryName: 'pe-gpt',
    });
  });
});

describe('PeGptEcsStack', () => {
  let app: cdk.App;
  let ecrStack: PeGptEcr.PeGptEcrStack;
  let ecsStack: PeGptEcs.PeGptEcsStack;
  let template: Template;

  beforeEach(() => {
    app = new cdk.App();
    const config = getEnvironmentConfig('development');
    
    ecrStack = new PeGptEcr.PeGptEcrStack(app, 'EcrTestStack', {
      environment: 'development',
      config: config,
    });
    
    ecsStack = new PeGptEcs.PeGptEcsStack(app, 'EcsTestStack', {
      environment: 'development',
      config: config,
      repository: ecrStack.repository,
    });
    template = Template.fromStack(ecsStack);
  });

  test('Stack creates successfully', () => {
    expect(template).toBeDefined();
  });

  test('ALB is configured correctly', () => {
    template.hasResourceProperties('AWS::ElasticLoadBalancingV2::LoadBalancer', {
      Scheme: 'internet-facing',
      Type: 'application',
    });
  });

  test('ECS service is configured correctly', () => {
    template.hasResourceProperties('AWS::ECS::Service', {
      ServiceName: 'pe-gpt-service',
      LaunchType: 'FARGATE',
      DesiredCount: 1,
    });
  });

  test('ECS cluster is created', () => {
    template.hasResourceProperties('AWS::ECS::Cluster', {
      ClusterName: 'pe-gpt-cluster',
    });
  });

  test('CloudFront distribution is created', () => {
    template.hasResourceProperties('AWS::CloudFront::Distribution', {
      DistributionConfig: {
        Comment: 'PE-GPT CloudFront Distribution',
      },
    });
  });
});
