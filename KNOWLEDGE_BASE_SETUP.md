# Amazon Bedrock KnowledgeBase Integration Setup Guide

## 概要

PE-GPTは、Amazon Bedrock KnowledgeBaseとの統合により、拡張可能な知識検索機能を提供します。ローカルファイル、Bedrock KnowledgeBase、またはその両方を組み合わせたハイブリッドモードで文書検索を行うことができます。

## 前提条件

### AWS設定

1. **AWS認証情報の設定**

   本番環境（Fargate）ではECSタスクロールによるIAMロール認証を使用します。
   ローカル開発時はAWS CLIプロファイルまたは環境変数を使用してください。

   ```bash
   # ローカル開発: AWS CLIプロファイル
   aws configure

   # または環境変数
   export AWS_ACCESS_KEY_ID=your_access_key
   export AWS_SECRET_ACCESS_KEY=your_secret_key
   export AWS_DEFAULT_REGION=us-east-1
   ```

2. **必要なAWS権限**
   - `bedrock:Retrieve` - KnowledgeBaseからの文書検索
   - `bedrock:InvokeModel` - LLMモデルの呼び出し
   - `bedrock:InvokeModelWithResponseStream` - ストリーミング応答

### Bedrock KnowledgeBaseの準備

1. AWS BedrockコンソールでKnowledgeBaseを作成
2. 文書をアップロードしてインデックス化
3. KnowledgeBase IDとリージョンを記録

## 設定方法

すべての設定は環境変数で行います。GUI上での設定変更機能はありません。

### 環境変数

#### 必須

```bash
export BEDROCK_KB_ID=your_knowledge_base_id
```

#### オプション

```bash
export BEDROCK_KB_REGION=us-east-1                  # デフォルト: us-east-1
export BEDROCK_KB_MODE=hybrid                       # local / bedrock / hybrid（デフォルト: hybrid）
export BEDROCK_KB_TOP_K=5                           # 取得文書数（デフォルト: 5）
export BEDROCK_KB_CONFIDENCE_THRESHOLD=0.0          # 信頼度閾値（デフォルト: 0.0）
export BEDROCK_KB_ENABLE_FALLBACK=true              # フォールバック有効（デフォルト: true）
export BEDROCK_KB_RETRY_ATTEMPTS=3                  # リトライ回数（デフォルト: 3）
```

### Fargate（本番）での設定

ECSタスク定義の環境変数として設定します。CDKスタック（`infrastructure/lib/pe-gpt-ecs-stack.ts`）の `environment` セクションで `BEDROCK_KB_ID` が設定されています。

### ローカル開発での設定

シェルの設定ファイルに追加するか、起動前に export してください。

```bash
export BEDROCK_KB_ID=your_knowledge_base_id
export BEDROCK_KB_REGION=us-east-1
streamlit run main.py
```

## モード別の使い分け

### 1. ローカルモード (`BEDROCK_KB_MODE=local`)

- ローカルファイルベースの検索のみ
- オフラインでの動作が可能
- `BEDROCK_KB_ID` の設定は不要

### 2. Bedrockモード (`BEDROCK_KB_MODE=bedrock`)

- Bedrock KnowledgeBaseの文書のみを検索
- `BEDROCK_KB_ID` の設定が必須

### 3. ハイブリッドモード (`BEDROCK_KB_MODE=hybrid`) — デフォルト・推奨

- ローカルとBedrock両方から並列検索し、結果を統合・ランキング
- フォールバック機能による高い可用性
- `BEDROCK_KB_ID` の設定が必須

## 検索パラメータの調整

### Top K Results

- 推奨値: 5〜10
- 低い値（1〜3）: より関連性の高い少数の文書
- 高い値（10〜20）: より多くの文書から幅広い情報

### Confidence Threshold

- 推奨値: 0.0〜0.3
- 0.0: すべての検索結果を含める
- 0.5以上: 高い信頼度の結果のみ

## エラーハンドリングとフォールバック

システムは以下の状況で自動的にフォールバックを実行します:

- Bedrock KnowledgeBase接続エラー（ネットワーク、認証、サービス利用不可）
- 検索結果なし（信頼度スコアが閾値を下回る場合を含む）

### フォールバック動作

- **ハイブリッドモード**: Bedrock失敗時にローカル検索を継続
- **Bedrockモード**: エラー時にローカル検索にフォールバック（利用可能な場合）
- **ローカルモード**: フォールバック不要

## デバッグ

環境変数 `DEBUG_MODE=true` を設定すると、GUI上にKnowledgeBaseの設定状況やステータスメッセージが表示されます。デフォルトでは非表示です。

```bash
export DEBUG_MODE=true
```

## トラブルシューティング

### 認証エラー

```
Error: Unable to locate credentials
```

- Fargate: ECSタスクロールに必要な権限が付与されているか確認
- ローカル: `aws configure list` で認証情報を確認

### KnowledgeBase ID不正エラー

```
Error: Knowledge base INVALID_ID not found
```

- AWS BedrockコンソールでKnowledgeBase IDを確認
- KnowledgeBaseが指定リージョンに存在するか確認

### 権限不足エラー

```
Error: User is not authorized to perform: bedrock:Retrieve
```

- IAMロール/ユーザーに `bedrock:Retrieve` 権限を追加

### レート制限エラー

```
Error: Rate exceeded
```

- システムが自動リトライを実行（設定された回数まで）
- Top K値を下げてAPI呼び出し回数を削減

### 検索結果なし

```
Warning: No results found from Bedrock KnowledgeBase
```

- KnowledgeBaseに関連文書が存在するか確認
- `BEDROCK_KB_CONFIDENCE_THRESHOLD` を下げる
- `BEDROCK_KB_TOP_K` を増やす
