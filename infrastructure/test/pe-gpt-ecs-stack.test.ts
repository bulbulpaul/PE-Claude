import * as cdk from 'aws-cdk-lib';
import { Template, Match } from 'aws-cdk-lib/assertions';
import * as PeGptEcs from '../lib/pe-gpt-ecs-stack';
import { getEnvironmentConfig } from '../config/environments';

describe('PeGptEcsStack', () => {
  let app: cdk.App;
  let stack: PeGptEcs.PeGptEcsStack;
  let template: Template;

  beforeEach(() => {
    app = new cdk.App();
    const config = getEnvironmentConfig('development');
    stack = new PeGptEcs.PeGptEcsStack(app, 'MyTestStack', {
      environment: 'development',
      config: config,
    });
    template = Template.fromStack(stack);
  });

  test('Stack creates successfully', () => {
    // Basic test to ensure stack can be synthesized
    expect(template).toBeDefined();
  });

  test('Security groups follow least privilege principle (Task 9)', () => {
    // Test ALB Security Group configuration
    template.hasResourceProperties('AWS::EC2::SecurityGroup', {
      GroupDescription: 'Security group for ALB',
      SecurityGroupIngress: [
        {
          CidrIp: '0.0.0.0/0',
          FromPort: 80,
          IpProtocol: 'tcp',
          ToPort: 80,
          Description: 'Allow HTTP traffic from internet'
        }
      ]
    });

    // Test ECS Security Group configuration
    template.hasResourceProperties('AWS::EC2::SecurityGroup', {
      GroupDescription: 'Security group for ECS tasks',
      SecurityGroupIngress: [
        {
          FromPort: 8501,
          IpProtocol: 'tcp',
          ToPort: 8501,
          Description: 'Allow traffic from ALB'
        }
      ]
    });

    // Verify that security groups are created (ALB + ECS + VPC default)
    // We expect at least 2 security groups (ALB and ECS)
    const sgCount = template.findResources('AWS::EC2::SecurityGroup');
    expect(Object.keys(sgCount).length).toBeGreaterThanOrEqual(2);
  });

  test('ALB is configured correctly', () => {
    // Test that ALB is configured with the correct properties
    template.hasResourceProperties('AWS::ElasticLoadBalancingV2::LoadBalancer', {
      Scheme: 'internet-facing',
      Type: 'application'
    });
  });

  test('ECS service is configured correctly', () => {
    // Test that ECS service is configured with the correct properties
    template.hasResourceProperties('AWS::ECS::Service', {
      ServiceName: 'pe-gpt-service',
      LaunchType: 'FARGATE',
      DesiredCount: 1
    });
  });

  test('ECR repository is created', () => {
    template.hasResourceProperties('AWS::ECR::Repository', {
      RepositoryName: 'pe-gpt'
    });
  });

  test('ECS cluster is created', () => {
    template.hasResourceProperties('AWS::ECS::Cluster', {
      ClusterName: 'pe-gpt-cluster'
    });
  });
});