# 設計書

## 概要

PE-GPTアプリケーションをOpenAI GPTからAmazon BedrockのClaudeモデルに移行するための設計書です。既存のアーキテクチャを最大限活用しながら、Bedrockとの統合を実現します。

## アーキテクチャ

### 現在のアーキテクチャ
```
main.py
├── core/llm/llm.py (OpenAI統合)
├── core/gui/gui.py (Streamlit UI)
├── core/gui/design_stages.py (設計フロー)
└── RAGエージェント (llama_index + OpenAI)
```

### 新しいアーキテクチャ
```
main.py
├── core/llm/llm.py (Bedrock統合に変更)
├── core/gui/gui.py (変更なし)
├── core/gui/design_stages.py (変更なし)
└── RAGエージェント (llama_index + Bedrock)
```

## コンポーネントと インターフェース

### 1. Bedrock統合レイヤー

既存の`llm.py`を直接Bedrock統合に変更し、同じインターフェースを維持します。

```python
def bedrock_init(model_id: str = None, region: str = None):
    """
    Amazon Bedrockクライアントを初期化
    """
    region = region or os.getenv("AWS_REGION", "us-east-1")
    model_id = model_id or os.getenv("BEDROCK_MODEL_ID", "anthropic.claude-3-sonnet-20240229-v1:0")
    
    bedrock_client = boto3.client('bedrock-runtime', region_name=region)
    
    if "bedrock_model" not in st.session_state:
        st.session_state["bedrock_model"] = model_id
    
    return bedrock_client

def bedrock_chat_completion(client, messages, model_id, **kwargs):
    """
    Bedrock APIを使用してClaude応答を生成
    """
    # OpenAI形式からBedrock形式に変換
    bedrock_messages = convert_messages_to_bedrock_format(messages)
    
    request_body = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": kwargs.get("max_tokens", 1000),
        "messages": bedrock_messages
    }
    
    response = client.invoke_model(
        modelId=model_id,
        body=json.dumps(request_body)
    )
    
    return parse_bedrock_response(response)
```

### 2. 設定管理

環境変数で設定を管理：

```python
# 環境変数
AWS_REGION = "us-east-1"
BEDROCK_MODEL_ID = "anthropic.claude-3-sonnet-20240229-v1:0"

# 設定クラス
class Config:
    def __init__(self):
        self.aws_region = os.getenv("AWS_REGION", "us-east-1")
        self.bedrock_model_id = os.getenv("BEDROCK_MODEL_ID", "anthropic.claude-3-sonnet-20240229-v1:0")
```

## データモデル

### Bedrockリクエスト/レスポンス形式

```python
# Claudeリクエスト形式
bedrock_request = {
    "anthropic_version": "bedrock-2023-05-31",
    "max_tokens": 1000,
    "messages": [
        {
            "role": "user",
            "content": "ユーザーメッセージ"
        }
    ]
}

# Claudeレスポンス形式
bedrock_response = {
    "content": [
        {
            "type": "text",
            "text": "Claude応答テキスト"
        }
    ],
    "id": "msg_xxx",
    "model": "claude-3-sonnet-20240229",
    "role": "assistant",
    "stop_reason": "end_turn",
    "stop_sequence": None,
    "type": "message",
    "usage": {
        "input_tokens": 10,
        "output_tokens": 20
    }
}
```

### メッセージ変換

OpenAI形式からBedrock形式への変換を行います：

```python
def convert_openai_to_bedrock_messages(openai_messages):
    bedrock_messages = []
    for msg in openai_messages:
        bedrock_messages.append({
            "role": msg["role"],
            "content": msg["content"]
        })
    return bedrock_messages
```

## エラーハンドリング

### 1. AWS認証エラー
- NoCredentialsError: AWS認証情報が見つからない
- ClientError: 権限不足またはサービスエラー

### 2. Bedrockサービスエラー
- ModelNotFoundError: 指定されたモデルが利用できない
- ThrottlingException: レート制限に達した
- ValidationException: リクエストパラメータが無効

### 3. エラーハンドリング戦略
```python
def robust_bedrock_call(client, model_id, messages, **kwargs):
    """
    再試行ロジック付きのBedrock呼び出し
    """
    max_retries = 3
    for attempt in range(max_retries):
        try:
            return bedrock_chat_completion(client, messages, model_id, **kwargs)
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'ThrottlingException' and attempt < max_retries - 1:
                time.sleep(2 ** attempt)  # 指数バックオフ
                continue
            else:
                raise e
```

## テスト戦略

### 1. 単体テスト
- Bedrock統合関数のテスト
- メッセージ変換関数のテスト
- エラーハンドリングのテスト

### 2. 統合テスト
- Bedrock APIとの実際の通信テスト
- RAGシステムとの統合テスト
- エンドツーエンドのチャットフローテスト

### 3. モックテスト
```python
@patch('boto3.client')
def test_bedrock_chat_completion(mock_boto_client):
    mock_response = {
        'body': StreamingBody(
            json.dumps(expected_response).encode(),
            len(json.dumps(expected_response))
        )
    }
    mock_boto_client.return_value.invoke_model.return_value = mock_response
    
    client = bedrock_init()
    result = bedrock_chat_completion(client, [{"role": "user", "content": "test"}], "claude-model")
    
    assert result["content"] == "expected response"
```

## 移行戦略

### フェーズ1: 基盤構築
1. 既存llm.pyのBedrock統合への変更
2. 設定管理システムの構築
3. メッセージ変換機能の実装

### フェーズ2: RAG統合
1. llama_indexとBedrockの統合
2. 埋め込みモデルの統合
3. チャットエンジンの更新

### フェーズ3: テストと最適化
1. 包括的なテストの実行
2. パフォーマンスの最適化
3. エラーハンドリングの改善

## セキュリティ考慮事項

### 1. AWS認証情報管理
- IAMロールの使用を推奨
- 環境変数での認証情報管理
- 最小権限の原則に従ったポリシー設定

### 2. ログ管理
- APIキーやトークンをログに出力しない
- リクエスト/レスポンスの適切なマスキング
- 監査ログの実装

### 3. 必要なIAM権限
```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "bedrock:InvokeModel",
                "bedrock:InvokeModelWithResponseStream"
            ],
            "Resource": [
                "arn:aws:bedrock:*::foundation-model/anthropic.claude-*"
            ]
        }
    ]
}
```