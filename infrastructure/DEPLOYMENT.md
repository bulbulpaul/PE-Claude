# PE-GPT ECS デプロイメントガイド

## 概要

このドキュメントでは、PE-GPTアプリケーションをAmazon ECS Fargateにデプロイする手順を説明します。

## 前提条件

### 必要なツール
- AWS CLI (v2.0以上)
- Docker
- Node.js (v18以上)
- npm

### AWS設定
```bash
# AWS認証情報の設定
aws configure

# 必要な権限
# - ECS、ECR、VPC、ALB、IAM、CloudFormation の管理権限
```

## デプロイメント手順

### 1. 環境変数の設定

#### 基本環境変数
```bash
# 必須環境変数
export AWS_DEFAULT_REGION=us-east-1
export BEDROCK_KB_ID=your-knowledge-base-id

# オプション環境変数
export CDK_DEFAULT_ACCOUNT=$(aws sts get-caller-identity --query Account --output text)
```

#### HTTPS対応環境（staging/production）の追加設定
```bash
# 証明書ARN（必須）
export CERTIFICATE_ARN=arn:aws:acm:us-east-1:123456789012:certificate/12345678-1234-1234-1234-123456789012

# カスタムドメイン設定（オプション）
export DOMAIN_NAME=your-custom-domain.com

# Cognito認証URL設定（オプション）
export CALLBACK_URLS=https://your-domain.com/oauth2/idpresponse
export LOGOUT_URLS=https://your-domain.com/

# 複数URL指定の場合（カンマ区切り）
export CALLBACK_URLS=https://domain1.com/oauth2/idpresponse,https://domain2.com/oauth2/idpresponse
export LOGOUT_URLS=https://domain1.com/,https://domain2.com/
```

#### 環境変数設定支援スクリプト
対話的に環境変数を設定するためのスクリプトを使用できます：
```bash
./scripts/set-env-vars.sh
```

### 2. CDKブートストラップ（初回のみ）

```bash
cd infrastructure
npm install
npx cdk bootstrap
```

### 3. Dockerイメージのビルドとプッシュ

```bash
# ECRリポジトリの作成（CDKデプロイ前に必要な場合）
aws ecr create-repository --repository-name pe-gpt --region $AWS_DEFAULT_REGION

# イメージのビルドとプッシュ
./scripts/build-and-push.sh latest
```

### 4. CDKスタックのデプロイ

#### 開発環境
```bash
npm run deploy:dev
```

#### 本番環境
```bash
export BEDROCK_KB_ID=your-production-kb-id
npm run deploy:prod
```

#### 手動デプロイ
```bash
# 差分確認
npm run diff

# デプロイ実行
npm run deploy
```

#### 環境別デプロイスクリプト使用
```bash
# 開発環境（HTTPS無効）
./scripts/deploy-with-env.sh -e development

# ステージング環境（HTTPS有効）
export CERTIFICATE_ARN=arn:aws:acm:us-east-1:account:certificate/cert-id
./scripts/deploy-with-env.sh -e staging

# 本番環境（HTTPS有効）
export CERTIFICATE_ARN=arn:aws:acm:us-east-1:account:certificate/cert-id
export DOMAIN_NAME=test.demo.pe.merrylab.jp
./scripts/deploy-with-env.sh -e production

# 強制デプロイ（確認プロンプトをスキップ）
./scripts/deploy-with-env.sh -e production --force-deploy
```

### 5. デプロイメント検証

```bash
# 自動検証スクリプト
./scripts/validate-deployment.sh development

# 手動確認
aws ecs describe-services --cluster pe-gpt-cluster --services pe-gpt-service
```

## 設定パラメータ

### 環境設定ファイル
`config/environments.ts` で環境別の設定を管理：

```typescript
{
  region: 'us-east-1',
  bedrockKnowledgeBaseId: 'your-kb-id',
  ecsConfig: {
    cpu: 1024,        // CPU単位 (1024 = 1 vCPU)
    memory: 2048,     // メモリ (MB)
    desiredCount: 1   // 実行タスク数
  }
}
```

### リソース制限
- **開発環境**: 1 vCPU, 2GB RAM, 1タスク
- **本番環境**: 2 vCPU, 4GB RAM, 2タスク

## 運用手順

### アプリケーションの更新

1. 新しいDockerイメージをビルド・プッシュ
```bash
./scripts/build-and-push.sh v1.2.0
```

2. ECSサービスの更新
```bash
aws ecs update-service --cluster pe-gpt-cluster --service pe-gpt-service --force-new-deployment
```

### ログの確認

```bash
# CloudWatch Logsでログ確認
aws logs tail /ecs/pe-gpt --follow

# 特定期間のログ
aws logs filter-log-events --log-group-name /ecs/pe-gpt --start-time 1640995200000
```

### スケーリング

```bash
# タスク数の変更
aws ecs update-service --cluster pe-gpt-cluster --service pe-gpt-service --desired-count 3
```

## トラブルシューティング

### よくある問題

#### 1. タスクが起動しない
```bash
# タスクの状態確認
aws ecs describe-tasks --cluster pe-gpt-cluster --tasks $(aws ecs list-tasks --cluster pe-gpt-cluster --service-name pe-gpt-service --query 'taskArns[0]' --output text)

# ログ確認
aws logs tail /ecs/pe-gpt --follow
```

#### 2. ALBヘルスチェック失敗
- Streamlitアプリケーションの起動時間を確認
- セキュリティグループの設定を確認
- ターゲットグループのヘルスチェック設定を確認

#### 3. Bedrock接続エラー
- IAMロールの権限を確認
- 環境変数 `BEDROCK_KB_ID` の設定を確認
- リージョン設定を確認

### デバッグコマンド

```bash
# ECSサービスの詳細確認
aws ecs describe-services --cluster pe-gpt-cluster --services pe-gpt-service

# タスク定義の確認
aws ecs describe-task-definition --task-definition pe-gpt-task

# ALBターゲットの健全性確認
aws elbv2 describe-target-health --target-group-arn $(aws elbv2 describe-target-groups --names pe-gpt-tg --query 'TargetGroups[0].TargetGroupArn' --output text)
```

## セキュリティ考慮事項

### ネットワークセキュリティ
- ECSタスクはプライベートサブネットで実行
- ALBのみがインターネットからアクセス可能
- セキュリティグループで最小権限の原則を適用

### IAM権限
- タスクロールはBedrock操作のみに制限
- 実行ロールはECS操作とログ出力のみに制限

### データ保護
- CloudWatch Logsは7日間保持
- ECRイメージは最新10個のみ保持

## コスト最適化

### リソース使用量の監視
```bash
# ECSサービスのメトリクス確認
aws cloudwatch get-metric-statistics --namespace AWS/ECS --metric-name CPUUtilization --dimensions Name=ServiceName,Value=pe-gpt-service Name=ClusterName,Value=pe-gpt-cluster --start-time 2023-01-01T00:00:00Z --end-time 2023-01-02T00:00:00Z --period 3600 --statistics Average
```

### コスト削減のヒント
- 開発環境では必要時のみタスクを実行
- 本番環境でもトラフィックに応じてスケーリング
- 不要なログの保持期間を短縮

## 削除手順

```bash
# スタックの削除
npm run destroy

# ECRイメージの削除（必要に応じて）
aws ecr delete-repository --repository-name pe-gpt --force
```

## サポート

問題が発生した場合は、以下の情報を収集してください：
- CloudFormationスタックのイベント
- ECSサービスとタスクの状態
- CloudWatch Logs
- ALBのアクセスログ