import * as cdk from 'aws-cdk-lib';
import * as ec2 from 'aws-cdk-lib/aws-ec2';
import * as ecs from 'aws-cdk-lib/aws-ecs';
import * as ecr from 'aws-cdk-lib/aws-ecr';
import * as elbv2 from 'aws-cdk-lib/aws-elasticloadbalancingv2';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as logs from 'aws-cdk-lib/aws-logs';
import * as cognito from 'aws-cdk-lib/aws-cognito';
import * as cloudfront from 'aws-cdk-lib/aws-cloudfront';
import * as origins from 'aws-cdk-lib/aws-cloudfront-origins';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import { Construct } from 'constructs';
import { EnvironmentConfig } from '../config/environments';

export interface PeGptEcsStackProps extends cdk.StackProps {
  environment: string;
  config: EnvironmentConfig;
  repository: ecr.IRepository;
}

export class PeGptEcsStack extends cdk.Stack {
  public readonly vpc: ec2.Vpc;
  public readonly cluster: ecs.Cluster;
  public readonly repository: ecr.IRepository;
  public readonly loadBalancer: elbv2.ApplicationLoadBalancer;
  public readonly service: ecs.FargateService;
  public readonly userPool: cognito.UserPool;
  public readonly userPoolClient: cognito.UserPoolClient;
  public readonly userPoolDomain: cognito.UserPoolDomain;
  public readonly distribution: cloudfront.Distribution;

  constructor(scope: Construct, id: string, props: PeGptEcsStackProps) {
    super(scope, id, props);

    // VPCの作成
    this.vpc = this.createVpc();

    // ECRリポジトリの参照（ECRスタックから渡される）
    this.repository = props.repository;

    // ECSクラスターの作成
    this.cluster = this.createEcsCluster();

    // Application Load Balancerの作成
    this.loadBalancer = this.createApplicationLoadBalancer();

    // Cognito User Poolの作成
    this.userPool = this.createUserPool();
    this.userPoolDomain = this.createUserPoolDomain(props.config);

    // CloudFront Distribution（認証なしで先に作成）
    this.distribution = this.createCloudFrontDistribution();
    
    // User Pool Clientの作成（CloudFrontドメイン確定後）
    this.userPoolClient = this.createUserPoolClient();

    // Lambda@EdgeをCloudFrontに追加
    this.addAuthToCloudFront(props.config);

    // ECSサービスの作成
    this.service = this.createEcsService(props.config);

    // 出力
    this.createOutputs(props.config);
  }

  private createVpc(): ec2.Vpc {
    return new ec2.Vpc(this, 'PeGptVpc', {
      maxAzs: 2,
      natGateways: 1,
      subnetConfiguration: [
        {
          cidrMask: 24,
          name: 'Public',
          subnetType: ec2.SubnetType.PUBLIC,
        },
        {
          cidrMask: 24,
          name: 'Private',
          subnetType: ec2.SubnetType.PRIVATE_WITH_EGRESS,
        },
      ],
    });
  }

  private createUserPool(): cognito.UserPool {
    return new cognito.UserPool(this, 'PeGptUserPool', {
      userPoolName: 'pe-gpt-user-pool',
      signInAliases: { email: true },
      selfSignUpEnabled: false,
      userVerification: {
        emailSubject: 'PE-Claude アカウント認証',
        emailBody: 'PE-Claudeへようこそ！認証コード: {####}',
        emailStyle: cognito.VerificationEmailStyle.CODE,
      },
      passwordPolicy: {
        minLength: 8,
        requireLowercase: true,
        requireUppercase: true,
        requireDigits: true,
        requireSymbols: true,
      },
      standardAttributes: {
        email: { required: true, mutable: true },
      },
      accountRecovery: cognito.AccountRecovery.EMAIL_ONLY,
      removalPolicy: cdk.RemovalPolicy.DESTROY,
    });
  }

  private createUserPoolClient(): cognito.UserPoolClient {
    const cloudFrontDomain = this.distribution.distributionDomainName;

    return new cognito.UserPoolClient(this, 'PeGptUserPoolClient', {
      userPool: this.userPool,
      userPoolClientName: 'pe-gpt-client',
      oAuth: {
        flows: { 
          authorizationCodeGrant: false,
          implicitCodeGrant: true,
        },
        scopes: [
          cognito.OAuthScope.EMAIL,
          cognito.OAuthScope.OPENID,
          cognito.OAuthScope.PROFILE,
        ],
        callbackUrls: [`https://${cloudFrontDomain}/callback`],
        logoutUrls: [`https://${cloudFrontDomain}/`],
      },
      generateSecret: false,
      preventUserExistenceErrors: true,
      authSessionValidity: cdk.Duration.minutes(3),
      idTokenValidity: cdk.Duration.hours(1),
      accessTokenValidity: cdk.Duration.hours(1),
      refreshTokenValidity: cdk.Duration.days(30),
      authFlows: { userSrp: true, userPassword: false, adminUserPassword: false },
    });
  }

  private createUserPoolDomain(config: EnvironmentConfig): cognito.UserPoolDomain {
    return new cognito.UserPoolDomain(this, 'PeGptUserPoolDomain', {
      userPool: this.userPool,
      cognitoDomain: {
        domainPrefix: config.albConfig.cognitoConfig?.userPoolDomainPrefix || 'pe-gpt-auth-default',
      },
    });
  }

  private createEcsCluster(): ecs.Cluster {
    return new ecs.Cluster(this, 'PeGptCluster', {
      vpc: this.vpc,
      clusterName: 'pe-gpt-cluster',
    });
  }

  private createApplicationLoadBalancer(): elbv2.ApplicationLoadBalancer {
    const albSecurityGroup = new ec2.SecurityGroup(this, 'ALBSecurityGroup', {
      vpc: this.vpc,
      description: 'Security group for ALB - CloudFront only',
      allowAllOutbound: true,
    });

    // CloudFront マネージドプレフィックスリストを使用して、CloudFront からのトラフィックのみ許可
    // これにより ALB への直接アクセスを防止
    // us-east-1 の CloudFront origin-facing プレフィックスリスト ID
    albSecurityGroup.addIngressRule(
      ec2.Peer.prefixList('pl-3b927c52'),
      ec2.Port.tcp(80),
      'Allow HTTP traffic from CloudFront only'
    );

    return new elbv2.ApplicationLoadBalancer(this, 'PeGptALB', {
      vpc: this.vpc,
      internetFacing: true,
      securityGroup: albSecurityGroup,
    });
  }

  private createCloudFrontDistribution(): cloudfront.Distribution {
    const albOrigin = new origins.HttpOrigin(this.loadBalancer.loadBalancerDnsName, {
      protocolPolicy: cloudfront.OriginProtocolPolicy.HTTP_ONLY,
      httpPort: 80,
    });

    return new cloudfront.Distribution(this, 'PeGptDistribution', {
      defaultBehavior: {
        origin: albOrigin,
        viewerProtocolPolicy: cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
        allowedMethods: cloudfront.AllowedMethods.ALLOW_ALL,
        cachePolicy: cloudfront.CachePolicy.CACHING_DISABLED,
        originRequestPolicy: cloudfront.OriginRequestPolicy.ALL_VIEWER,
      },
      comment: 'PE-GPT CloudFront Distribution',
      priceClass: cloudfront.PriceClass.PRICE_CLASS_100,
    });
  }

  private addAuthToCloudFront(config: EnvironmentConfig): void {
    // Lambda@Edge用のIAMロール
    const edgeRole = new iam.Role(this, 'AuthEdgeRole', {
      assumedBy: new iam.CompositePrincipal(
        new iam.ServicePrincipal('lambda.amazonaws.com'),
        new iam.ServicePrincipal('edgelambda.amazonaws.com'),
      ),
      managedPolicies: [
        iam.ManagedPolicy.fromAwsManagedPolicyName('service-role/AWSLambdaBasicExecutionRole'),
      ],
    });

    // Cognito設定値
    const cognitoDomain = `${config.albConfig.cognitoConfig?.userPoolDomainPrefix}.auth.${config.region}.amazoncognito.com`;
    
    // UserPoolClientIdをハードコード（循環依存を回避）
    // 注意: 初回デプロイ後にこの値を更新する必要があります
    const hardcodedClientId = 'rbo9ej45uk2nji5jotb7fqdlh';

    // Lambda@Edge関数（認証チェック）
    const authFunction = new lambda.Function(this, 'AuthEdgeFunction', {
      runtime: lambda.Runtime.NODEJS_18_X,
      handler: 'index.handler',
      code: lambda.Code.fromInline(this.getAuthFunctionCode(hardcodedClientId, cognitoDomain)),
      role: edgeRole,
      timeout: cdk.Duration.seconds(5),
      memorySize: 128,
    });

    // Lambda@EdgeをCloudFrontに関連付け
    const cfnDistribution = this.distribution.node.defaultChild as cloudfront.CfnDistribution;
    const authVersion = authFunction.currentVersion;

    cfnDistribution.addPropertyOverride(
      'DistributionConfig.DefaultCacheBehavior.LambdaFunctionAssociations',
      [{
        EventType: 'viewer-request',
        LambdaFunctionARN: authVersion.functionArn,
        IncludeBody: false,
      }]
    );
  }

  private getAuthFunctionCode(clientId: string, cognitoDomain: string): string {
    return `
'use strict';

const CLIENT_ID = '${clientId}';
const COGNITO_DOMAIN = '${cognitoDomain}';

function parseCookies(headers) {
  const cookies = {};
  if (headers.cookie) {
    headers.cookie[0].value.split(';').forEach(cookie => {
      const parts = cookie.split('=');
      cookies[parts[0].trim()] = parts.slice(1).join('=').trim();
    });
  }
  return cookies;
}

function generateLoginRedirect(request) {
  const host = request.headers.host[0].value;
  const uri = request.uri;
  const qs = request.querystring ? '?' + request.querystring : '';
  const redirectUri = 'https://' + host + '/callback';
  const state = Buffer.from(JSON.stringify({ returnTo: uri + qs })).toString('base64');
  
  const loginUrl = 'https://' + COGNITO_DOMAIN + '/login?' +
    'client_id=' + CLIENT_ID + '&' +
    'response_type=token&' +
    'scope=email+openid+profile&' +
    'redirect_uri=' + encodeURIComponent(redirectUri) + '&' +
    'state=' + encodeURIComponent(state);

  return {
    status: '302',
    statusDescription: 'Found',
    headers: {
      location: [{ key: 'Location', value: loginUrl }],
      'cache-control': [{ key: 'Cache-Control', value: 'no-cache' }],
    },
  };
}

function generateCallbackPage() {
  const html = \`<!DOCTYPE html>
<html>
<head><title>Authenticating...</title></head>
<body>
<script>
  const hash = window.location.hash.substring(1);
  const params = new URLSearchParams(hash);
  const idToken = params.get('id_token');
  const accessToken = params.get('access_token');
  const state = params.get('state');
  
  if (idToken) {
    document.cookie = 'id_token=' + idToken + '; path=/; secure; samesite=lax; max-age=3600';
    document.cookie = 'access_token=' + accessToken + '; path=/; secure; samesite=lax; max-age=3600';
    
    let returnTo = '/';
    if (state) {
      try {
        const stateObj = JSON.parse(atob(state));
        returnTo = stateObj.returnTo || '/';
      } catch(e) {}
    }
    window.location.href = returnTo;
  } else {
    document.body.innerHTML = 'Authentication failed. <a href="/">Try again</a>';
  }
</script>
<noscript>JavaScript is required for authentication.</noscript>
</body>
</html>\`;

  return {
    status: '200',
    statusDescription: 'OK',
    headers: {
      'content-type': [{ key: 'Content-Type', value: 'text/html' }],
      'cache-control': [{ key: 'Cache-Control', value: 'no-cache, no-store' }],
    },
    body: html,
  };
}

exports.handler = async (event) => {
  const request = event.Records[0].cf.request;
  const headers = request.headers;
  
  if (request.uri === '/_stcore/health' || request.uri.startsWith('/_stcore/')) {
    return request;
  }

  if (request.uri === '/callback') {
    return generateCallbackPage();
  }

  const cookies = parseCookies(headers);
  const idToken = cookies['id_token'];

  if (!idToken) {
    return generateLoginRedirect(request);
  }

  try {
    const parts = idToken.split('.');
    if (parts.length !== 3) throw new Error('Invalid token');
    const payload = JSON.parse(Buffer.from(parts[1], 'base64').toString());
    if (payload.exp * 1000 < Date.now()) throw new Error('Token expired');
    return request;
  } catch (err) {
    return generateLoginRedirect(request);
  }
};
`;
  }

  private createEcsService(config: EnvironmentConfig): ecs.FargateService {
    const ecsSecurityGroup = new ec2.SecurityGroup(this, 'ECSSecurityGroup', {
      vpc: this.vpc,
      description: 'Security group for ECS tasks',
      allowAllOutbound: true,
    });

    ecsSecurityGroup.addIngressRule(
      this.loadBalancer.connections.securityGroups[0],
      ec2.Port.tcp(8501),
      'Allow traffic from ALB'
    );

    const executionRole = new iam.Role(this, 'TaskExecutionRole', {
      assumedBy: new iam.ServicePrincipal('ecs-tasks.amazonaws.com'),
      managedPolicies: [
        iam.ManagedPolicy.fromAwsManagedPolicyName('service-role/AmazonECSTaskExecutionRolePolicy'),
      ],
    });

    const taskRole = new iam.Role(this, 'TaskRole', {
      assumedBy: new iam.ServicePrincipal('ecs-tasks.amazonaws.com'),
      inlinePolicies: {
        BedrockAccess: new iam.PolicyDocument({
          statements: [
            new iam.PolicyStatement({
              effect: iam.Effect.ALLOW,
              actions: [
                'bedrock:InvokeModel',
                'bedrock:InvokeModelWithResponseStream',
                'bedrock:Retrieve',
                'bedrock:RetrieveAndGenerate',
              ],
              resources: ['*'],
            }),
          ],
        }),
      },
    });

    const logGroup = new logs.LogGroup(this, 'PeGptLogGroup', {
      logGroupName: '/ecs/pe-gpt',
      retention: logs.RetentionDays.ONE_WEEK,
      removalPolicy: cdk.RemovalPolicy.DESTROY,
    });

    const taskDefinition = new ecs.FargateTaskDefinition(this, 'PeGptTaskDefinition', {
      memoryLimitMiB: config.ecsConfig.memory,
      cpu: config.ecsConfig.cpu,
      executionRole: executionRole,
      taskRole: taskRole,
      ephemeralStorageGiB: 50,
      runtimePlatform: {
        cpuArchitecture: ecs.CpuArchitecture.ARM64,
        operatingSystemFamily: ecs.OperatingSystemFamily.LINUX,
      },
    });

    const container = taskDefinition.addContainer('PeGptContainer', {
      image: ecs.ContainerImage.fromEcrRepository(this.repository, 'latest'),
      environment: {
        AWS_DEFAULT_REGION: config.region,
        STREAMLIT_SERVER_HEADLESS: 'true',
        BEDROCK_KB_ID: config.bedrockKnowledgeBaseId,
        APP_URL: `https://${this.distribution.distributionDomainName}`,
      },
      logging: ecs.LogDrivers.awsLogs({
        streamPrefix: 'pe-gpt',
        logGroup: logGroup,
      }),
      healthCheck: {
        command: ['CMD-SHELL', 'curl -f http://localhost:8501/_stcore/health || exit 1'],
        interval: cdk.Duration.seconds(30),
        timeout: cdk.Duration.seconds(10),
        retries: 5,
        startPeriod: cdk.Duration.seconds(180),
      },
    });

    container.addPortMappings({
      containerPort: 8501,
      protocol: ecs.Protocol.TCP,
    });

    const targetGroup = new elbv2.ApplicationTargetGroup(this, 'PeGptTargetGroup', {
      port: 8501,
      protocol: elbv2.ApplicationProtocol.HTTP,
      vpc: this.vpc,
      targetType: elbv2.TargetType.IP,
      healthCheck: {
        enabled: true,
        path: '/_stcore/health',
        interval: cdk.Duration.seconds(60),
        timeout: cdk.Duration.seconds(10),
        healthyThresholdCount: 2,
        unhealthyThresholdCount: 5,
        protocol: elbv2.Protocol.HTTP,
      },
      targetGroupName: 'pe-gpt-targets',
      deregistrationDelay: cdk.Duration.seconds(30),
    });

    this.loadBalancer.addListener('PeGptHttpListener', {
      port: 80,
      protocol: elbv2.ApplicationProtocol.HTTP,
      defaultTargetGroups: [targetGroup],
    });

    const service = new ecs.FargateService(this, 'PeGptService', {
      cluster: this.cluster,
      taskDefinition: taskDefinition,
      desiredCount: config.ecsConfig.desiredCount,
      securityGroups: [ecsSecurityGroup],
      vpcSubnets: { subnetType: ec2.SubnetType.PRIVATE_WITH_EGRESS },
      healthCheckGracePeriod: cdk.Duration.seconds(600),
      serviceName: 'pe-gpt-service',
    });

    service.attachToApplicationTargetGroup(targetGroup);

    return service;
  }

  private createOutputs(config: EnvironmentConfig): void {
    new cdk.CfnOutput(this, 'CloudFrontURL', {
      value: `https://${this.distribution.distributionDomainName}`,
      description: 'CloudFront Distribution URL (use this for HTTPS access)',
    });

    new cdk.CfnOutput(this, 'CloudFrontDistributionId', {
      value: this.distribution.distributionId,
      description: 'CloudFront Distribution ID',
    });

    new cdk.CfnOutput(this, 'LoadBalancerDNS', {
      value: this.loadBalancer.loadBalancerDnsName,
      description: 'DNS name of the load balancer (internal use)',
    });

    new cdk.CfnOutput(this, 'ECRRepositoryURI', {
      value: this.repository.repositoryUri,
      description: 'ECR Repository URI',
    });

    new cdk.CfnOutput(this, 'VpcId', {
      value: this.vpc.vpcId,
      description: 'VPC ID',
    });

    new cdk.CfnOutput(this, 'ClusterName', {
      value: this.cluster.clusterName,
      description: 'ECS Cluster Name',
    });

    new cdk.CfnOutput(this, 'UserPoolId', {
      value: this.userPool.userPoolId,
      description: 'Cognito User Pool ID',
    });

    new cdk.CfnOutput(this, 'UserPoolClientId', {
      value: this.userPoolClient.userPoolClientId,
      description: 'Cognito User Pool Client ID',
    });

    new cdk.CfnOutput(this, 'UserPoolDomainUrl', {
      value: this.userPoolDomain.domainName,
      description: 'Cognito User Pool Domain URL',
    });

    new cdk.CfnOutput(this, 'KnowledgeBaseId', {
      value: config.bedrockKnowledgeBaseId,
      description: 'Bedrock Knowledge Base ID (existing)',
    });
  }
}
