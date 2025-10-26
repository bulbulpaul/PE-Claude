# 設計文書

## 概要

この設計は、PE-GPTアプリケーションの既存のRAGシステムにAmazon Bedrock KnowledgeBase統合を追加します。現在のシステムは`rag_load`関数を通じてローカルファイルベースの文書インデックス化を使用しており、llama_indexとBedrock Claudeモデルを活用しています。この拡張により、ユーザーはローカルファイル、Bedrock KnowledgeBase、またはハイブリッドモードを選択できるようになります。

## アーキテクチャ

### 現在のアーキテクチャ
```
main.py
├── rag_load() → VectorStoreIndex (ローカルファイル)
├── chat_engine0 (database)
├── chat_engine1 (database1) 
└── chat_engine2 (introduction)
```

### 新しいアーキテクチャ
```
main.py
├── enhanced_rag_load() → HybridIndex
│   ├── LocalVectorStoreIndex (既存)
│   └── BedrockKnowledgeBaseRetriever (新規)
├── chat_engine0 (ハイブリッド対応)
├── chat_engine1 (ハイブリッド対応)
└── chat_engine2 (ハイブリッド対応)
```

## コンポーネントとインターフェース

### 1. BedrockKnowledgeBaseRetriever クラス
```python
class BedrockKnowledgeBaseRetriever:
    """Amazon Bedrock KnowledgeBase用のカスタム検索クラス"""
    
    def __init__(self, knowledge_base_id: str, region: str, top_k: int = 5)
    def retrieve(self, query: str) -> List[NodeWithScore]
    def _validate_config(self) -> bool
    def _handle_api_errors(self, error: Exception) -> List[NodeWithScore]
    
    # 注意: 各KnowledgeBaseは単一のリージョンに存在し、
    # 複数リージョンにまたがる検索は行わない
```

### 2. HybridRetriever クラス
```python
class HybridRetriever:
    """ローカルとBedrock KnowledgeBaseの結果を統合する検索クラス"""
    
    def __init__(self, local_retriever, bedrock_retriever, mode: str = "hybrid")
    def retrieve(self, query: str) -> List[NodeWithScore]
    def _merge_results(self, local_results, bedrock_results) -> List[NodeWithScore]
    def _rank_by_relevance(self, results: List[NodeWithScore]) -> List[NodeWithScore]
```

### 3. KnowledgeBaseConfig クラス
```python
class KnowledgeBaseConfig:
    """Bedrock KnowledgeBase設定管理"""
    
    knowledge_base_id: str
    region: str
    similarity_top_k: int
    confidence_threshold: float
    mode: str  # "local", "bedrock", "hybrid"
```

### 4. 拡張されたrag_load関数
```python
def enhanced_rag_load(
    database_folder: str = None,
    knowledge_base_config: KnowledgeBaseConfig = None,
    llm_model: str = None,
    temperature: float = None,
    chunk_size: int = None,
    system_prompt: str = None,
    use_bedrock: bool = True
) -> VectorStoreIndex:
```

## データモデル

### KnowledgeBaseConfig
```python
@dataclass
class KnowledgeBaseConfig:
    knowledge_base_id: str
    region: str = "us-east-1"  # 単一リージョンのみ指定可能
    similarity_top_k: int = 5
    confidence_threshold: float = 0.0
    mode: str = "hybrid"  # "local", "bedrock", "hybrid"
    enable_fallback: bool = True
    retry_attempts: int = 3
    
    def __post_init__(self):
        """設定検証: 単一リージョンのみ許可"""
        if not isinstance(self.region, str) or not self.region:
            raise ValueError("リージョンは単一の文字列で指定してください")
```

### RetrievalResult
```python
@dataclass
class RetrievalResult:
    content: str
    score: float
    source: str  # "local" or "bedrock"
    metadata: Dict[str, Any]
```

## エラーハンドリング

### 1. 設定検証エラー
- 無効なKnowledgeBase ID
- 無効なリージョン設定
- 認証エラー

### 2. API呼び出しエラー
- ネットワーク接続エラー
- レート制限エラー
- サービス利用不可エラー

### 3. フォールバック戦略
```python
def handle_bedrock_error(error: Exception, fallback_enabled: bool) -> List[NodeWithScore]:
    """
    Bedrock KnowledgeBaseエラー時のフォールバック処理
    1. エラーログ記録
    2. ローカル検索へのフォールバック（有効な場合）
    3. 空の結果返却（フォールバック無効時）
    """
```

### 4. 再試行ロジック
```python
def retry_with_backoff(func, max_retries: int = 3, base_delay: float = 1.0):
    """指数バックオフによる再試行実装"""
```

## テスト戦略

### 1. 単体テスト
- `BedrockKnowledgeBaseRetriever`の各メソッド
- `HybridRetriever`の結果マージロジック
- 設定検証機能
- エラーハンドリング機能

### 2. 統合テスト
- ローカルファイルとBedrock KnowledgeBaseの統合
- 既存のチャットエンジンとの互換性
- エンドツーエンドのクエリ処理

### 3. エラーシナリオテスト
- Bedrock KnowledgeBase利用不可時のフォールバック
- 無効な設定での動作
- ネットワークエラー時の再試行

## 実装詳細

### 1. ファイル構造
```
core/
├── llm/
│   ├── llm.py (既存)
│   ├── bedrock_kb_retriever.py (新規)
│   └── hybrid_retriever.py (新規)
└── knowledge/
    └── kb_config.py (新規)
```

### 2. 設定管理
- セッション状態での設定保存
- 環境変数からのデフォルト値読み込み
- GUI設定パネル（サイドバー）

### 3. 既存コードとの統合
- `main.py`の`rag_load`呼び出しを`enhanced_rag_load`に置換
- 既存のチャットエンジン作成ロジックの保持
- 後方互換性の確保

### 4. パフォーマンス考慮事項
- 並列検索実行（ローカルとBedrock）
- 結果キャッシュ機能
- 検索結果の効率的なマージ

## セキュリティ考慮事項

### 1. 認証情報管理
- AWS認証情報の安全な取り扱い
- セッション状態での機密情報の適切な管理

### 2. 入力検証
- KnowledgeBase ID形式の検証
- クエリ文字列のサニタイゼーション

### 3. エラー情報の適切な処理
- 機密情報を含まないエラーメッセージ
- ログでの適切な情報マスキング

## 設定インターフェース

### GUI設定パネル（サイドバー追加）
```python
# Streamlitサイドバーに追加される設定UI
with st.sidebar:
    st.markdown("### Knowledge Base Settings")
    
    # モード選択
    kb_mode = st.selectbox(
        "Knowledge Source Mode",
        ["local", "bedrock", "hybrid"],
        index=2
    )
    
    # Bedrock KnowledgeBase設定
    if kb_mode in ["bedrock", "hybrid"]:
        kb_id = st.text_input("Knowledge Base ID")
        # 単一リージョン選択（デフォルトはus-east-1）
        kb_region = st.text_input("Region", value="us-east-1", 
                                  help="KnowledgeBaseが存在するAWSリージョンを指定")
        similarity_top_k = st.slider("Top K Results", 1, 20, 5)
        confidence_threshold = st.slider("Confidence Threshold", 0.0, 1.0, 0.0)
        
        # リージョン形式の簡単な検証
        if kb_region and not re.match(r'^[a-z]{2}-[a-z]+-\d+$', kb_region):
            st.warning("リージョン形式が正しくありません（例: us-east-1）")
```

## 移行戦略

### フェーズ1: 基盤実装
1. `BedrockKnowledgeBaseRetriever`クラス実装
2. 基本的な設定管理機能
3. 単体テスト作成

### フェーズ2: 統合実装
1. `HybridRetriever`クラス実装
2. `enhanced_rag_load`関数実装
3. 既存システムとの統合

### フェーズ3: UI・UX改善
1. GUI設定パネル実装
2. エラーハンドリング強化
3. パフォーマンス最適化

### フェーズ4: テスト・検証
1. 統合テスト実行
2. エラーシナリオテスト
3. ドキュメント更新