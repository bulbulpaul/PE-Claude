# PE-GPT ECS Deployment Guide

このドキュメントは、PE-GPTアプリケーションのAmazon ECS環境へのデプロイメント手順を説明します。

## 前提条件

### 必要なツール

- [AWS CLI](https://aws.amazon.com/cli/) v2.0以上
- [Docker](https://www.docker.com/) v20.0以上
- [Node.js](https://nodejs.org/) v18以上
- [npm](https://www.npmjs.com/) v8以上
- [Git](https://git-scm.com/) v2.0以上

### AWS認証情報

以下のいずれかの方法でAWS認証情報を設定してください：

```bash
# AWS CLIで設定
aws configure

# または環境変数で設定
export AWS_ACCESS_KEY_ID=your-access-key
export AWS_SECRET_ACCESS_KEY=your-secret-key
export AWS_DEFAULT_REGION=us-east-1

# またはAWSプロファイルを使用
export AWS_PROFILE=your-profile
```

### 必要なAWS権限

デプロイに必要な最小権限：

- CloudFormation: フルアクセス
- ECS: フルアクセス
- ECR: フルアクセス
- EC2: VPC、セキュリティグループ、ロードバランサー関連
- IAM: ロール作成・管理
- Logs: CloudWatch Logs管理
- SSM: Parameter Store管理

## クイックスタート

### 1. 環境変数とシークレットの設定

```bash
# 開発環境の設定
./infrastructure/scripts/manage-env.sh set-env development

# 本番環境の設定
./infrastructure/scripts/manage-env.sh set-env production
```

### 2. 完全デプロイ（推奨）

```bash
# 開発環境へのデプロイ
./infrastructure/scripts/deploy-with-env.sh -e development

# 本番環境へのデプロイ
./infrastructure/scripts/deploy-with-env.sh -e production --force-deploy
```

## 詳細なデプロイ手順

### Step 1: リポジトリのクローン

```bash
git clone <repository-url>
cd pe-gpt
```

### Step 2: 環境設定

#### 開発環境

```bash
# 環境変数の設定
./infrastructure/scripts/manage-env.sh set-env development

# 必要なシークレットの設定
./infrastructure/scripts/manage-env.sh set-secret bedrock-kb-id "YOUR_KB_ID" -e development --encrypt

# 設定の確認
./infrastructure/scripts/manage-env.sh validate-env development
```

#### 本番環境

```bash
# 環境変数の設定
./infrastructure/scripts/manage-env.sh set-env production

# 必要なシークレットの設定
./infrastructure/scripts/manage-env.sh set-secret bedrock-kb-id "YOUR_KB_ID" -e production --encrypt

# 設定の確認
./infrastructure/scripts/manage-env.sh validate-env production
```

### Step 3: Dockerイメージのビルドとプッシュ

```bash
# ECRリポジトリへのイメージプッシュ
./infrastructure/scripts/build-and-push.sh --region us-east-1 --latest
```

### Step 4: CDKインフラストラクチャのデプロイ

```bash
cd infrastructure

# 依存関係のインストール
npm install

# CDKブートストラップ（初回のみ）
npx cdk bootstrap

# デプロイ
npx cdk deploy --require-approval never \
  --context environment=development \
  --context imageTag=latest \
  --context bedrockKbId=YOUR_KB_ID
```

## 環境別設定

### 開発環境 (development)

- **CPU**: 1024 (1 vCPU)
- **Memory**: 2048 MB
- **Desired Count**: 1
- **HTTPS**: 無効
- **Image Retention**: 10個

### 本番環境 (production)

- **CPU**: 2048 (2 vCPU)
- **Memory**: 4096 MB
- **Desired Count**: 2
- **HTTPS**: 有効（証明書ARNが必要）
- **Image Retention**: 20個

## CI/CD パイプライン

### GitHub Actions

`.github/workflows/deploy.yml` ファイルが自動デプロイを設定します。

#### 必要なシークレット

GitHub リポジトリの Settings > Secrets で以下を設定：

```
AWS_ACCESS_KEY_ID=your-access-key
AWS_SECRET_ACCESS_KEY=your-secret-key
AWS_ACCOUNT_ID=123456789012
BEDROCK_KB_ID=your-knowledge-base-id
```

#### トリガー

- `main` ブランチへのプッシュ → 本番環境デプロイ
- `develop` ブランチへのプッシュ → 開発環境デプロイ
- 手動実行 → 指定環境デプロイ

## 運用コマンド

### ログの確認

```bash
# ECSタスクのログを確認
aws logs tail /ecs/pe-gpt --follow --region us-east-1

# 特定の時間範囲のログ
aws logs filter-log-events \
  --log-group-name /ecs/pe-gpt \
  --start-time 1640995200000 \
  --region us-east-1
```

### サービスの状態確認

```bash
# ECSサービスの状態
aws ecs describe-services \
  --cluster pe-gpt-cluster \
  --services pe-gpt-service \
  --region us-east-1

# タスクの状態
aws ecs list-tasks \
  --cluster pe-gpt-cluster \
  --service-name pe-gpt-service \
  --region us-east-1
```

### スケーリング

```bash
# サービスのスケーリング
aws ecs update-service \
  --cluster pe-gpt-cluster \
  --service pe-gpt-service \
  --desired-count 3 \
  --region us-east-1
```

### 新しいイメージのデプロイ

```bash
# 新しいイメージをビルド・プッシュ
./infrastructure/scripts/build-and-push.sh --tag v1.2.3

# サービスを更新（新しいタスク定義が必要な場合）
npx cdk deploy --context imageTag=v1.2.3
```

## トラブルシューティング

### よくある問題

#### 1. ECRリポジトリが存在しない

```bash
# CDKでECRリポジトリを作成
cd infrastructure
npx cdk deploy --context environment=development
```

#### 2. Parameter Storeにシークレットがない

```bash
# シークレットを設定
./infrastructure/scripts/manage-env.sh set-secret bedrock-kb-id "YOUR_KB_ID" -e development --encrypt
```

#### 3. タスクが起動しない

```bash
# タスクの詳細を確認
aws ecs describe-tasks \
  --cluster pe-gpt-cluster \
  --tasks TASK_ARN \
  --region us-east-1

# ログを確認
aws logs tail /ecs/pe-gpt --follow --region us-east-1
```

#### 4. ヘルスチェックが失敗する

```bash
# ALBターゲットグループの状態を確認
aws elbv2 describe-target-health \
  --target-group-arn TARGET_GROUP_ARN \
  --region us-east-1
```

### デバッグコマンド

```bash
# CDKの差分確認
cd infrastructure
npx cdk diff

# CloudFormationスタックの確認
aws cloudformation describe-stacks \
  --stack-name PeGptEcsStack \
  --region us-east-1

# セキュリティグループの確認
aws ec2 describe-security-groups \
  --filters "Name=group-name,Values=pe-gpt-*" \
  --region us-east-1
```

## セキュリティ考慮事項

### ネットワークセキュリティ

- ECSタスクはプライベートサブネットに配置
- ALBのみがインターネットからアクセス可能
- セキュリティグループで最小権限の原則を適用

### シークレット管理

- 機密情報はParameter Store（暗号化）で管理
- IAMロールで最小権限のアクセス制御
- 環境ごとに分離されたパラメータ

### 監査とログ

- VPCフローログが有効
- CloudWatch Logsでアプリケーションログを記録
- CloudTrailでAPI呼び出しを監査

## パフォーマンス最適化

### リソース設定

- 環境に応じたCPU/メモリ設定
- オートスケーリングの設定
- ヘルスチェック間隔の最適化

### コスト最適化

- 開発環境では最小リソース
- ECRライフサイクルポリシーで古いイメージを削除
- 不要な環境の定期的な削除

## サポート

問題が発生した場合は、以下の情報を含めてサポートに連絡してください：

1. エラーメッセージ
2. 実行したコマンド
3. 環境情報（development/production）
4. CloudFormationスタックの状態
5. ECSタスクのログ