export interface EnvironmentConfig {
  account?: string;
  region: string;
  bedrockKnowledgeBaseId: string;
  ecsConfig: {
    cpu: number;
    memory: number;
    desiredCount: number;
  };
  albConfig: {
    cognitoConfig?: {
      userPoolDomainPrefix: string;
    };
  };
  cloudFrontConfig: {
    enabled: boolean;
  };
  ecrConfig: {
    repositoryName: string;
    imageRetentionCount: number;
  };
}

// 環境変数から Bedrock Knowledge Base ID を取得
const BEDROCK_KB_ID = process.env.BEDROCK_KB_ID;

if (!BEDROCK_KB_ID) {
  throw new Error('BEDROCK_KB_ID environment variable is required');
}

export const environments: { [key: string]: EnvironmentConfig } = {
  development: {
    region: 'us-east-1',
    bedrockKnowledgeBaseId: BEDROCK_KB_ID,
    ecsConfig: {
      cpu: 1024,
      memory: 2048,
      desiredCount: 1,
    },
    albConfig: {
      cognitoConfig: {
        userPoolDomainPrefix: 'pe-gpt-auth-dev-072918826049',
      },
    },
    cloudFrontConfig: {
      enabled: true,
    },
    ecrConfig: {
      repositoryName: 'pe-gpt',
      imageRetentionCount: 10,
    },
  },
  staging: {
    region: 'us-east-1',
    bedrockKnowledgeBaseId: BEDROCK_KB_ID,
    ecsConfig: {
      cpu: 1024,
      memory: 2048,
      desiredCount: 1,
    },
    albConfig: {
      cognitoConfig: {
        userPoolDomainPrefix: 'pe-gpt-auth-staging',
      },
    },
    cloudFrontConfig: {
      enabled: true,
    },
    ecrConfig: {
      repositoryName: 'pe-gpt',
      imageRetentionCount: 15,
    },
  },
  production: {
    region: 'us-east-1',
    bedrockKnowledgeBaseId: BEDROCK_KB_ID,
    ecsConfig: {
      cpu: 2048,
      memory: 4096,
      desiredCount: 2,
    },
    albConfig: {
      cognitoConfig: {
        userPoolDomainPrefix: 'pe-gpt-auth-production',
      },
    },
    cloudFrontConfig: {
      enabled: true,
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
  return config;
}