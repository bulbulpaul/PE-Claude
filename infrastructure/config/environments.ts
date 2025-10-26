export interface EnvironmentConfig {
  account?: string;
  region: string;
  ecsConfig: {
    cpu: number;
    memory: number;
    desiredCount: number;
  };
  albConfig: {
    enableHttps: boolean;
    certificateArn?: string;
  };
  ecrConfig: {
    repositoryName: string;
    imageRetentionCount: number;
  };
}

export const environments: { [key: string]: EnvironmentConfig } = {
  development: {
    region: 'us-east-1',
    ecsConfig: {
      cpu: 1024,
      memory: 2048,
      desiredCount: 1,
    },
    albConfig: {
      enableHttps: false,
    },
    ecrConfig: {
      repositoryName: 'pe-gpt',
      imageRetentionCount: 10,
    },
  },
  production: {
    region: 'us-east-1',
    ecsConfig: {
      cpu: 2048,
      memory: 4096,
      desiredCount: 2,
    },
    albConfig: {
      enableHttps: true,
      // certificateArn: 'arn:aws:acm:us-east-1:ACCOUNT:certificate/CERTIFICATE_ID',
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