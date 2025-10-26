# 要件仕様書

## 概要

この機能は、既存のPE-GPTアプリケーションのRAG（Retrieval Augmented Generation）システムにAmazon Bedrock KnowledgeBase統合を追加します。現在の実装では、llama_indexとBedrock Claudeモデルを使用したローカルファイルベースの文書インデックス化を行っています。この拡張により、ユーザーはAmazon Bedrock KnowledgeBaseを追加または代替の知識ソースとして使用できるようになり、よりスケーラブルで管理された文書検索機能を利用できます。

## 用語集

- **PE-GPT**: パワーエレクトロニクス設計用AIアシスタント
- **RAG_System**: ローカルファイルを使用する既存の検索拡張生成システム
- **Bedrock_KnowledgeBase**: 文書検索用のAmazon Bedrockマネージド知識ベースサービス
- **Chat_Engine**: 検索されたコンテキストでユーザークエリを処理するllama_indexチャットエンジン
- **Knowledge_Source**: ローカルファイルまたはBedrock KnowledgeBaseのいずれかの文書ソース
- **Hybrid_Mode**: ローカルとBedrockの知識ソースを同時に使用可能にする設定

## 要件

### 要件1

**ユーザーストーリー:** PE-GPTユーザーとして、Amazon Bedrock KnowledgeBaseを知識ソースとして設定したい。これにより、管理された文書検索機能を活用できる。

#### 受け入れ基準

1. ユーザーがBedrock KnowledgeBase設定を構成するとき、RAG_SystemはKnowledgeBase IDとリージョン設定を検証する
2. Bedrock KnowledgeBaseが有効な場合、RAG_Systemは適切な認証でBedrock KnowledgeBase検索機能を初期化する
3. KnowledgeBase初期化が失敗した場合、RAG_Systemはエラーをログに記録し、ローカルファイルモードにフォールバックする
4. RAG_Systemはチャットセッション間での再利用のためにKnowledgeBase設定をセッション状態に保存する

### 要件2

**ユーザーストーリー:** PE-GPTユーザーとして、ローカルファイル、Bedrock KnowledgeBase、または両方を知識ソースとして選択したい。これにより、特定のニーズに基づいて検索を最適化できる。

#### 受け入れ基準

1. RAG_Systemはローカルのみ、KnowledgeBaseのみ、またはハイブリッド知識ソースモードの設定オプションを提供する
2. ハイブリッドモードが選択されたとき、RAG_SystemはローカルファイルとBedrock KnowledgeBaseの両方から文書を検索する
3. RAG_Systemは関連性スコアに基づいて複数の知識ソースからの結果をマージし、ランク付けする
4. 利用可能な知識ソースがない場合、RAG_Systemはユーザーに明確なエラーメッセージを提供する

### 要件3

**ユーザーストーリー:** PE-GPTユーザーとして、システムがBedrock KnowledgeBase検索を既存のチャットエンジンとシームレスに統合してほしい。これにより、拡張された知識アクセスで同じインターフェースを継続使用できる。

#### 受け入れ基準

1. Chat_EngineはBedrock KnowledgeBaseから検索された文書をローカルファイル検索と同じ形式で受け入れる
2. ユーザークエリを処理するとき、Chat_Engineは既存のシステムプロンプトと併せてBedrock KnowledgeBase検索コンテキストを使用する
3. Chat_Engineは知識ソースに関係なく同じ応答形式と品質を維持する
4. RAG_Systemは後方互換性のために既存のチャットエンジン機能を保持する

### 要件4

**ユーザーストーリー:** PE-GPTユーザーとして、Bedrock KnowledgeBaseの検索パラメータを設定したい。これにより、検索された文書の関連性と数を最適化できる。

#### 受け入れ基準

1. RAG_SystemはKnowledgeBase検索のsimilarity_top_kパラメータの設定を許可する
2. RAG_Systemは検索された文書をフィルタリングするための信頼度スコア閾値をサポートする
3. カスタム検索パラメータが提供された場合、RAG_Systemはパラメータの範囲と型を検証する
4. RAG_Systemは検索パラメータが指定されていない場合に適切なデフォルト値を使用する

### 要件5

**ユーザーストーリー:** PE-GPTユーザーとして、Bedrock KnowledgeBase使用時の適切なエラーハンドリングとフォールバック機能がほしい。これにより、KnowledgeBaseサービスが利用できない場合でもシステムが機能し続ける。

#### 受け入れ基準

1. Bedrock KnowledgeBase API呼び出しが失敗した場合、RAG_Systemはエラーをログに記録し、ローカルファイル検索を試行する
2. KnowledgeBaseが結果を返さない場合、RAG_Systemは利用可能であればローカルファイル検索にフォールバックする
3. RAG_Systemは一般的なKnowledgeBase設定問題に対して情報的なエラーメッセージを提供する
4. RAG_Systemは一時的なKnowledgeBaseエラーに対して指数バックオフによる再試行ロジックを実装する