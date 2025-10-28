export interface EnvironmentConfig {
  account?: string;
  region: string;
  bedrockKnowledgeBaseId?: string;
  ecsConfig: {
    cpu: number;
    memory: number;
    desiredCount: number;
  };
  albConfig: {
    enableHttps: boolean;
    certificateArn?: string;
    domainName: string;
    cognitoConfig?: {
      userPoolDomainPrefix: string;
      callbackUrls: string[];
      logoutUrls: string[];
    };
  };
  ecrConfig: {
    repositoryName: string;
    imageRetentionCount: number;
  };
}

export const environments: { [key: string]: EnvironmentConfig } = {
  development: {
    region: 'us-east-1',
    bedrockKnowledgeBaseId: undefined, // Set via environment variable BEDROCK_KB_ID
    ecsConfig: {
      cpu: 1024,
      memory: 2048,
      desiredCount: 1,
    },
    albConfig: {
      enableHttps: true,
      domainName: 'test.demo.pe.merrylab.jp',
      cognitoConfig: {
        userPoolDomainPrefix: 'pe-gpt-auth-development',
        callbackUrls: ['https://test.demo.pe.merrylab.jp/oauth2/idpresponse'],
        logoutUrls: ['https://test.demo.pe.merrylab.jp/'],
      },
    },
    ecrConfig: {
      repositoryName: 'pe-gpt',
      imageRetentionCount: 10,
    },
  },
  staging: {
    region: 'us-east-1',
    bedrockKnowledgeBaseId: undefined, // Set via environment variable BEDROCK_KB_ID
    ecsConfig: {
      cpu: 1024,
      memory: 2048,
      desiredCount: 1,
    },
    albConfig: {
      enableHttps: true,
      certificateArn: 'arn:aws:acm:us-east-1:ACCOUNT:certificate/CERTIFICATE_ID', // To be set with actual certificate ARN
      domainName: 'staging.demo.pe.merrylab.jp',
      cognitoConfig: {
        userPoolDomainPrefix: 'pe-gpt-auth-staging',
        callbackUrls: ['https://staging.demo.pe.merrylab.jp/oauth2/idpresponse'],
        logoutUrls: ['https://staging.demo.pe.merrylab.jp/'],
      },
    },
    ecrConfig: {
      repositoryName: 'pe-gpt',
      imageRetentionCount: 15,
    },
  },
  production: {
    region: 'us-east-1',
    bedrockKnowledgeBaseId: undefined, // Set via environment variable BEDROCK_KB_ID
    ecsConfig: {
      cpu: 2048,
      memory: 4096,
      desiredCount: 2,
    },
    albConfig: {
      enableHttps: true,
      certificateArn: 'arn:aws:acm:us-east-1:ACCOUNT:certificate/CERTIFICATE_ID', // To be set with actual certificate ARN
      domainName: 'test.demo.pe.merrylab.jp',
      cognitoConfig: {
        userPoolDomainPrefix: 'pe-gpt-auth-production',
        callbackUrls: ['https://test.demo.pe.merrylab.jp/oauth2/idpresponse'],
        logoutUrls: ['https://test.demo.pe.merrylab.jp/'],
      },
    },
    ecrConfig: {
      repositoryName: 'pe-gpt',
      imageRetentionCount: 20,
    },
  },
};

export function getEnvironmentConfig(envName: string = 'development'): EnvironmentConfig {
  const config = environments[envName];
  if (!config) {
    throw new Error(`Environment configuration not found for: ${envName}`);
  }

  // 環境変数から動的に設定を取得
  const updatedConfig = {
    ...config,
    bedrockKnowledgeBaseId: process?.env?.BEDROCK_KB_ID || config.bedrockKnowledgeBaseId,
    albConfig: {
      ...config.albConfig,
      // 証明書ARNを環境変数から取得（設定されている場合）
      certificateArn: process?.env?.CERTIFICATE_ARN || config.albConfig.certificateArn,
      // ドメイン名を環境変数から取得（設定されている場合）
      domainName: process?.env?.DOMAIN_NAME || config.albConfig.domainName,
      cognitoConfig: config.albConfig.cognitoConfig ? {
        ...config.albConfig.cognitoConfig,
        // コールバックURLとログアウトURLを環境変数から取得（設定されている場合）
        callbackUrls: process?.env?.CALLBACK_URLS ?
          process.env.CALLBACK_URLS.split(',').map(url => url.trim()) :
          config.albConfig.cognitoConfig.callbackUrls,
        logoutUrls: process?.env?.LOGOUT_URLS ?
          process.env.LOGOUT_URLS.split(',').map(url => url.trim()) :
          config.albConfig.cognitoConfig.logoutUrls,
      } : undefined,
    },
  };

  return updatedConfig;
}