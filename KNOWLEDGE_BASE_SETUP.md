# Amazon Bedrock KnowledgeBase Integration Setup Guide

## 概要

PE-GPTは、Amazon Bedrock KnowledgeBaseとの統合により、より強力で拡張可能な知識検索機能を提供します。この機能により、ローカルファイル、Bedrock KnowledgeBase、またはその両方を組み合わせたハイブリッドモードで文書検索を行うことができます。

## 前提条件

### AWS設定
1. **AWS認証情報の設定**
   ```bash
   # AWS CLIを使用した設定
   aws configure
   
   # または環境変数での設定
   export AWS_ACCESS_KEY_ID=your_access_key
   export AWS_SECRET_ACCESS_KEY=your_secret_key
   export AWS_DEFAULT_REGION=us-east-1
   ```

2. **必要なAWS権限**
   - `bedrock:Retrieve` - KnowledgeBaseからの文書検索
   - `bedrock:RetrieveAndGenerate` - 検索と生成の実行

### Bedrock KnowledgeBaseの準備
1. AWS BedrockコンソールでKnowledgeBaseを作成
2. 文書をアップロードしてインデックス化
3. KnowledgeBase IDとリージョンを記録

## 設定方法

### 環境変数での設定

PE-GPTのBedrock KnowledgeBase統合は、環境変数を使用して設定します：

#### 必須環境変数
```bash
export BEDROCK_KB_ID=your_knowledge_base_id
export BEDROCK_KB_REGION=us-east-1
```

#### オプション環境変数
```bash
export BEDROCK_KB_MODE=hybrid                    # local, bedrock, hybrid (デフォルト: hybrid)
export BEDROCK_KB_TOP_K=5                       # 取得文書数 (デフォルト: 5)
export BEDROCK_KB_CONFIDENCE_THRESHOLD=0.0      # 信頼度閾値 (デフォルト: 0.0)
export BEDROCK_KB_ENABLE_FALLBACK=true          # フォールバック有効 (デフォルト: true)
export BEDROCK_KB_RETRY_ATTEMPTS=3              # リトライ回数 (デフォルト: 3)
```

#### 設定の永続化
設定を永続化するには、シェルの設定ファイルに追加します：

**Bash (.bashrc または .bash_profile):**
```bash
echo 'export BEDROCK_KB_ID=your_knowledge_base_id' >> ~/.bashrc
echo 'export BEDROCK_KB_REGION=us-east-1' >> ~/.bashrc
source ~/.bashrc
```

**Zsh (.zshrc):**
```bash
echo 'export BEDROCK_KB_ID=your_knowledge_base_id' >> ~/.zshrc
echo 'export BEDROCK_KB_REGION=us-east-1' >> ~/.zshrc
source ~/.zshrc
```

**または .env ファイル:**
```bash
# プロジェクトルートに .env ファイルを作成
BEDROCK_KB_ID=your_knowledge_base_id
BEDROCK_KB_REGION=us-east-1
BEDROCK_KB_MODE=hybrid
```

## 使用方法

### モード別の使い分けガイド

#### 1. ローカルモード (`BEDROCK_KB_MODE=local`)
**使用場面:**
- インターネット接続が不安定な環境
- AWS使用料金を抑えたい場合
- 機密性の高い文書のみを使用する場合

**設定:**
```bash
export BEDROCK_KB_MODE=local
# BEDROCK_KB_IDの設定は不要
```

**特徴:**
- 既存のローカルファイルベースの検索のみ
- オフラインでの動作が可能
- レスポンス時間が高速

#### 2. Bedrockモード (`BEDROCK_KB_MODE=bedrock`)
**使用場面:**
- 大規模な文書コレクションを活用したい場合
- 最新の文書情報にアクセスしたい場合
- ローカルストレージ容量を節約したい場合

**設定:**
```bash
export BEDROCK_KB_MODE=bedrock
export BEDROCK_KB_ID=your_knowledge_base_id
export BEDROCK_KB_REGION=us-east-1
```

**特徴:**
- Bedrock KnowledgeBaseの文書のみを検索
- スケーラブルな文書管理
- AWS管理による高可用性

#### 3. ハイブリッドモード (`BEDROCK_KB_MODE=hybrid`) - 推奨
**使用場面:**
- 最も包括的な検索結果が必要な場合
- ローカルとクラウドの文書を組み合わせたい場合
- 検索精度を最大化したい場合

**設定:**
```bash
export BEDROCK_KB_MODE=hybrid
export BEDROCK_KB_ID=your_knowledge_base_id
export BEDROCK_KB_REGION=us-east-1
```

**特徴:**
- ローカルとBedrock両方から検索
- 関連性スコアによる結果の統合とランキング
- フォールバック機能による高い可用性

### 検索パラメータの調整

#### Top K Results
- **推奨値**: 5-10
- **低い値 (1-3)**: より関連性の高い少数の文書
- **高い値 (10-20)**: より多くの文書から幅広い情報

#### Confidence Threshold
- **推奨値**: 0.0-0.3
- **0.0**: すべての検索結果を含める
- **0.5以上**: 高い信頼度の結果のみ

## エラーハンドリングとフォールバック

### 自動フォールバック機能

システムは以下の状況で自動的にフォールバックを実行します：

1. **Bedrock KnowledgeBase接続エラー**
   - ネットワーク接続問題
   - 認証エラー
   - サービス利用不可

2. **検索結果なし**
   - KnowledgeBaseに関連文書が存在しない
   - 信頼度スコアが閾値を下回る

### フォールバック動作
- **ハイブリッドモード**: Bedrock失敗時にローカル検索を継続
- **Bedrockモード**: エラー時にローカル検索にフォールバック（利用可能な場合）
- **ローカルモード**: フォールバック不要

## パフォーマンス最適化

### 検索速度の向上
1. **適切なTop K値の設定**: 必要以上に多くの文書を取得しない
2. **信頼度スコア閾値の調整**: 低品質な結果をフィルタリング
3. **ハイブリッドモードでの並列検索**: ローカルとBedrockを同時実行

### コスト最適化
1. **モード選択の最適化**: 用途に応じたモード選択
2. **Top K値の調整**: 必要最小限の文書数に設定
3. **キャッシュ機能の活用**: 同一クエリの結果再利用

## セキュリティ考慮事項

### 認証情報の管理
- AWS認証情報を環境変数で管理
- IAMロールの最小権限原則を適用
- 認証情報をコードに直接記述しない

### データプライバシー
- 機密文書はローカルモードを使用
- Bedrock KnowledgeBaseへのデータアップロード時の暗号化確認
- ログファイルでの機密情報マスキング

## GUI での設定確認

PE-GPTを起動すると、サイドバーの「Knowledge Base Status」セクションで現在の設定状況を確認できます：

- **設定済みの場合**: ✅ Bedrock KnowledgeBase設定済み
- **未設定の場合**: ⚠️ Bedrock KnowledgeBase未設定

設定例も表示されるため、環境変数の設定方法を確認できます。

## 次のステップ

1. **環境変数の設定**: 必要な環境変数を設定
2. **PE-GPTの起動**: `streamlit run main.py`
3. **設定確認**: GUIで設定状況を確認
4. **テスト実行**: 各モードでの動作確認
5. **本格運用**: 実際の設計タスクでの活用

詳細なトラブルシューティング情報については、次のセクションを参照してください。
## 設定例


### 例1: 基本的なハイブリッド設定
```python
# GUI設定パネルでの設定例
Knowledge Source Mode: hybrid
Knowledge Base ID: ABCDEFGHIJ
Region: us-east-1
Top K Results: 5
Confidence Threshold: 0.0
```

### 例2: 高精度検索設定
```python
# より厳密な検索結果が必要な場合
Knowledge Source Mode: hybrid
Knowledge Base ID: ABCDEFGHIJ
Region: us-east-1
Top K Results: 3
Confidence Threshold: 0.5
```

### 例3: 大量文書検索設定
```python
# 幅広い情報収集が必要な場合
Knowledge Source Mode: hybrid
Knowledge Base ID: ABCDEFGHIJ
Region: us-east-1
Top K Results: 15
Confidence Threshold: 0.1
```

### 例4: 環境変数での設定
```bash
# .envファイルまたはシェル設定
export BEDROCK_KB_ID=ABCDEFGHIJ
export BEDROCK_KB_REGION=us-east-1
export BEDROCK_KB_TOP_K=5
export BEDROCK_KB_CONFIDENCE_THRESHOLD=0.0
export AWS_DEFAULT_REGION=us-east-1
```

## トラブルシューティング

### よくあるエラーと解決方法

#### 1. 認証エラー
**エラーメッセージ:**
```
Error: Unable to locate credentials. You can configure credentials by running "aws configure"
```

**解決方法:**
1. AWS CLIの設定確認
   ```bash
   aws configure list
   ```
2. 認証情報の再設定
   ```bash
   aws configure
   ```
3. 環境変数の確認
   ```bash
   echo $AWS_ACCESS_KEY_ID
   echo $AWS_SECRET_ACCESS_KEY
   ```

#### 2. KnowledgeBase ID不正エラー
**エラーメッセージ:**
```
Error: Knowledge base INVALID_ID not found
```

**解決方法:**
1. AWS BedrockコンソールでKnowledgeBase IDを確認
2. 正しいリージョンでKnowledgeBaseが作成されているか確認
3. KnowledgeBaseのステータスが「Available」であることを確認

#### 3. リージョン設定エラー
**エラーメッセージ:**
```
Error: The security token included in the request is invalid
```

**解決方法:**
1. KnowledgeBaseが存在するリージョンと設定リージョンの一致確認
2. AWS認証情報のリージョン設定確認
   ```bash
   aws configure get region
   ```

#### 4. 権限不足エラー
**エラーメッセージ:**
```
Error: User is not authorized to perform: bedrock:Retrieve
```

**解決方法:**
1. IAMユーザーまたはロールに必要な権限を追加
   ```json
   {
     "Version": "2012-10-17",
     "Statement": [
       {
         "Effect": "Allow",
         "Action": [
           "bedrock:Retrieve",
           "bedrock:RetrieveAndGenerate"
         ],
         "Resource": "*"
       }
     ]
   }
   ```

#### 5. ネットワーク接続エラー
**エラーメッセージ:**
```
Error: Connection timeout
```

**解決方法:**
1. インターネット接続の確認
2. プロキシ設定の確認（企業環境の場合）
3. ファイアウォール設定の確認
4. 一時的にローカルモードに切り替え

#### 6. 検索結果なしエラー
**エラーメッセージ:**
```
Warning: No results found from Bedrock KnowledgeBase, falling back to local search
```

**解決方法:**
1. KnowledgeBaseに関連文書が存在するか確認
2. 検索クエリの見直し
3. Confidence Thresholdの調整（より低い値に設定）
4. Top K Resultsの増加

#### 7. レート制限エラー
**エラーメッセージ:**
```
Error: Rate exceeded. Please retry after some time
```

**解決方法:**
1. 検索頻度の調整
2. 自動再試行の待機（システムが自動的に処理）
3. Top K値の削減でAPI呼び出し回数を減らす

### パフォーマンス問題の診断

#### 検索が遅い場合
1. **ネットワーク遅延の確認**
   ```bash
   ping bedrock.us-east-1.amazonaws.com
   ```

2. **Top K値の最適化**
   - 必要以上に多くの文書を取得していないか確認
   - 推奨値: 3-10

3. **リージョンの最適化**
   - 物理的に近いリージョンの使用を検討

#### メモリ使用量が多い場合
1. **文書サイズの確認**
   - KnowledgeBaseの文書サイズを確認
   - 大きな文書の場合はTop K値を削減

2. **キャッシュの管理**
   - ブラウザキャッシュのクリア
   - Streamlitセッション状態のリセット

### ログとデバッグ

#### ログレベルの設定
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

#### 詳細なエラー情報の取得
1. Streamlitアプリの開発者モードで実行
   ```bash
   streamlit run main.py --logger.level=debug
   ```

2. ブラウザの開発者ツールでコンソールエラーを確認

### サポートとヘルプ

#### 追加リソース
- [AWS Bedrock Documentation](https://docs.aws.amazon.com/bedrock/)
- [AWS CLI Configuration Guide](https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-files.html)
- [PE-GPT GitHub Issues](https://github.com/XinzeLee/PE-GPT/issues)

#### 問題報告時の情報
問題を報告する際は、以下の情報を含めてください：
1. エラーメッセージの全文
2. 使用している設定（KnowledgeBase ID以外）
3. 実行環境（OS、Python版本）
4. 実行したクエリの例
5. ログファイルの関連部分

これらの情報により、より迅速で正確なサポートを提供できます。