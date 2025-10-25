# AWS認証情報設定ガイド

このドキュメントでは、PE-GPTアプリケーションでAmazon Bedrockを使用するために必要なAWS認証情報の設定方法について説明します。

## 前提条件

- AWSアカウントを持っていること
- Amazon Bedrockサービスへのアクセス権限があること
- 使用するリージョン（us-east-1）でBedrockが利用可能であること

## 認証情報の設定方法

### 方法1: 環境変数を使用（推奨）

環境変数を設定してAWS認証情報を提供します：

```bash
export AWS_ACCESS_KEY_ID=your_access_key_id
export AWS_SECRET_ACCESS_KEY=your_secret_access_key
export AWS_REGION=us-east-1
```

### 方法2: AWS CLIプロファイルを使用

AWS CLIがインストールされている場合：

```bash
# AWS CLIの設定
aws configure

# または特定のプロファイルを設定
aws configure --profile pe-gpt
```

設定後、プロファイルを使用する場合は環境変数を設定：

```bash
export AWS_PROFILE=pe-gpt
```

### 方法3: IAMロールを使用（EC2/ECS環境）

EC2インスタンスやECSタスクで実行する場合、IAMロールを使用できます。インスタンスまたはタスクに適切なIAMロールをアタッチしてください。

## 必要なIAM権限

PE-GPTアプリケーションが正常に動作するために、以下のIAM権限が必要です：

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "bedrock:InvokeModel",
                "bedrock:InvokeModelWithResponseStream",
                "bedrock:ListFoundationModels"
            ],
            "Resource": [
                "arn:aws:bedrock:us-east-1::foundation-model/anthropic.claude-*",
                "arn:aws:bedrock:us-east-1::foundation-model/amazon.titan-embed-*"
            ]
        }
    ]
}
```

## 環境変数の設定

アプリケーションで使用される環境変数：

| 環境変数名 | デフォルト値 | 説明 |
|-----------|-------------|------|
| `AWS_REGION` | `us-east-1` | 使用するAWSリージョン |
| `BEDROCK_MODEL_ID` | `anthropic.claude-3-sonnet-20240229-v1:0` | 使用するClaudeモデルID |
| `BEDROCK_EMBEDDING_MODEL_ID` | `amazon.titan-embed-text-v1` | 使用する埋め込みモデルID |

### 設定例

```bash
# 基本設定
export AWS_REGION=us-east-1
export BEDROCK_MODEL_ID=anthropic.claude-3-sonnet-20240229-v1:0
export BEDROCK_EMBEDDING_MODEL_ID=amazon.titan-embed-text-v1

# AWS認証情報
export AWS_ACCESS_KEY_ID=your_access_key_id
export AWS_SECRET_ACCESS_KEY=your_secret_access_key
```

## 利用可能なClaudeモデル

以下のClaudeモデルが利用可能です：

- `anthropic.claude-3-haiku-20240307-v1:0` - Claude 3 Haiku
- `anthropic.claude-3-sonnet-20240229-v1:0` - Claude 3 Sonnet
- `anthropic.claude-3-5-sonnet-20240620-v1:0` - Claude 3.5 Sonnet

## トラブルシューティング

### 認証エラーが発生する場合

1. AWS認証情報が正しく設定されているか確認
2. IAM権限が適切に設定されているか確認
3. 使用するリージョンでBedrockが利用可能か確認

### モデルが見つからないエラーが発生する場合

1. 指定したモデルIDが正しいか確認
2. 使用するリージョンで該当モデルが利用可能か確認
3. Bedrockコンソールでモデルアクセスが有効になっているか確認

### 権限エラーが発生する場合

1. IAMポリシーが正しく設定されているか確認
2. 必要な権限がすべて含まれているか確認
3. リソースARNが正しく指定されているか確認

## セキュリティのベストプラクティス

1. **最小権限の原則**: 必要最小限の権限のみを付与
2. **認証情報の保護**: 認証情報をコードに直接埋め込まない
3. **定期的なローテーション**: アクセスキーを定期的にローテーション
4. **監査ログ**: CloudTrailを使用してAPI呼び出しを監査

## 参考リンク

- [Amazon Bedrock ユーザーガイド](https://docs.aws.amazon.com/bedrock/)
- [AWS CLI設定ガイド](https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-files.html)
- [IAM ユーザーガイド](https://docs.aws.amazon.com/IAM/latest/UserGuide/)