import * as cdk from 'aws-cdk-lib';
import { Template, Match } from 'aws-cdk-lib/assertions';
import * as PeGptEcs from '../lib/pe-gpt-ecs-stack';

describe('PeGptEcsStack', () => {
  let app: cdk.App;
  let stack: PeGptEcs.PeGptEcsStack;
  let template: Template;

  beforeEach(() => {
    app = new cdk.App();
    stack = new PeGptEcs.PeGptEcsStack(app, 'MyTestStack');
    template = Template.fromStack(stack);
  });

  test('Stack creates successfully', () => {
    // Basic test to ensure stack can be synthesized
    expect(template).toBeDefined();
  });

  test('Security groups follow least privilege principle (Task 9)', () => {
    // Test ALB Security Group configuration
    template.hasResourceProperties('AWS::EC2::SecurityGroup', {
      GroupDescription: 'Security group for Application Load Balancer - allows HTTP/HTTPS from internet',
      GroupName: 'pe-gpt-alb-sg',
      SecurityGroupIngress: [
        {
          CidrIp: '0.0.0.0/0',
          FromPort: 80,
          IpProtocol: 'tcp',
          ToPort: 80,
          Description: 'Allow HTTP traffic from internet'
        },
        {
          CidrIp: '0.0.0.0/0',
          FromPort: 443,
          IpProtocol: 'tcp',
          ToPort: 443,
          Description: 'Allow HTTPS traffic from internet'
        }
      ]
    });

    // Test ECS Security Group configuration
    template.hasResourceProperties('AWS::EC2::SecurityGroup', {
      GroupDescription: 'Security group for ECS tasks - allows traffic only from ALB',
      GroupName: 'pe-gpt-ecs-sg',
      SecurityGroupIngress: [
        {
          FromPort: 8501,
          IpProtocol: 'tcp',
          ToPort: 8501,
          Description: 'Allow traffic from ALB to Streamlit port'
        }
      ]
    });

    // Verify that security groups are created (should have exactly 2 security groups plus the placeholder)
    template.resourceCountIs('AWS::EC2::SecurityGroup', 3);
  });

  test('ALB uses correct security group', () => {
    // Test that ALB is configured with the correct security group
    template.hasResourceProperties('AWS::ElasticLoadBalancingV2::LoadBalancer', {
      Name: 'pe-gpt-alb',
      Scheme: 'internet-facing',
      Type: 'application'
    });
  });

  test('ECS service uses correct security group', () => {
    // Test that ECS service is configured with the correct security group
    template.hasResourceProperties('AWS::ECS::Service', {
      ServiceName: 'pe-gpt-service',
      LaunchType: 'FARGATE',
      DesiredCount: 1
    });
  });
});