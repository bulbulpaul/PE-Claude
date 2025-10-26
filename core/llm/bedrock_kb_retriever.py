"""
Amazon Bedrock KnowledgeBase Retriever Module

This module provides integration with Amazon Bedrock KnowledgeBase for document retrieval.
It includes error handling, retry logic, and compatibility with llama_index.

@reference: PE-GPT: a New Paradigm for Power Electronics Design, by Fanfan Lin, Xinze Li, et al.
@code-author: Xinze Li, Fanfan Lin
@github: https://github.com/XinzeLee/PE-GPT
"""

import time
import logging
from typing import List, Dict, Any, Optional
import boto3
from botocore.exceptions import ClientError, NoCredentialsError, BotoCoreError

from llama_index.core.schema import NodeWithScore, TextNode
from llama_index.core.retrievers import BaseRetriever
from llama_index.core.base.base_query_engine import BaseQueryEngine

from core.knowledge.kb_config import KnowledgeBaseConfig
from core.llm.error_handler import get_error_handler, handle_error, format_error_for_user

logger = logging.getLogger(__name__)


class BedrockKnowledgeBaseRetriever(BaseRetriever):
    """
    Amazon Bedrock KnowledgeBase用のカスタム検索クラス
    
    This class provides integration with Amazon Bedrock KnowledgeBase API
    for document retrieval with error handling and retry logic.
    """
    
    def __init__(
        self,
        config: KnowledgeBaseConfig,
        aws_access_key_id: Optional[str] = None,
        aws_secret_access_key: Optional[str] = None,
        aws_session_token: Optional[str] = None
    ):
        """
        Initialize Bedrock KnowledgeBase retriever.
        
        Args:
            config: KnowledgeBase configuration
            aws_access_key_id: AWS access key (optional, uses default credentials if not provided)
            aws_secret_access_key: AWS secret key (optional)
            aws_session_token: AWS session token (optional)
        """
        super().__init__()
        self.config = config
        self._client = None
        self._aws_credentials = {
            'aws_access_key_id': aws_access_key_id,
            'aws_secret_access_key': aws_secret_access_key,
            'aws_session_token': aws_session_token
        }
        
        # Remove None values from credentials
        self._aws_credentials = {k: v for k, v in self._aws_credentials.items() if v is not None}
        
        # Validate configuration
        self._validate_config()
    
    @property
    def client(self):
        """Lazy initialization of Bedrock Agent Runtime client."""
        if self._client is None:
            try:
                # Create client with provided credentials or use default
                client_kwargs = {
                    'service_name': 'bedrock-agent-runtime',
                    'region_name': self.config.region
                }
                
                if self._aws_credentials:
                    client_kwargs.update(self._aws_credentials)
                
                self._client = boto3.client(**client_kwargs)
                logger.info(f"Bedrock Agent Runtime client initialized for region: {self.config.region}")
                
            except (NoCredentialsError, ClientError) as e:
                logger.error(f"AWS認証エラー: {e}")
                raise ValueError(f"AWS認証に失敗しました: {e}")
            except Exception as e:
                logger.error(f"Bedrockクライアント初期化エラー: {e}")
                raise ValueError(f"Bedrockクライアントの初期化に失敗しました: {e}")
        
        return self._client
    
    def _validate_config(self) -> bool:
        """
        Validate KnowledgeBase configuration.
        
        Returns:
            bool: True if configuration is valid
            
        Raises:
            ValueError: If configuration is invalid
        """
        if not self.config.knowledge_base_id:
            raise ValueError("KnowledgeBase IDが設定されていません")
        
        if not self.config.region:
            raise ValueError("AWSリージョンが設定されていません")
        
        if not self.config.is_bedrock_enabled():
            raise ValueError("Bedrockモードが有効になっていません")
        
        return True
    
    def _retrieve(self, query_bundle) -> List[NodeWithScore]:
        """
        Retrieve documents from Bedrock KnowledgeBase.
        
        Args:
            query_bundle: Query bundle containing the search query
            
        Returns:
            List[NodeWithScore]: Retrieved documents with scores
        """
        query_str = query_bundle.query_str if hasattr(query_bundle, 'query_str') else str(query_bundle)
        return self.retrieve(query_str)
    
    def retrieve(self, query: str) -> List[NodeWithScore]:
        """
        Retrieve documents from Bedrock KnowledgeBase with enhanced error handling and retry logic.
        
        Args:
            query: Search query string
            
        Returns:
            List[NodeWithScore]: Retrieved documents with scores
        """
        if not query or not query.strip():
            logger.warning("空のクエリが提供されました")
            return []
        
        error_handler = get_error_handler()
        
        for attempt in range(self.config.retry_attempts + 1):
            try:
                return self._perform_retrieval(query.strip())
                
            except Exception as e:
                # Use enhanced error handler
                error_info = error_handler.handle_error(e, f"Bedrock retrieval attempt {attempt + 1}")
                
                # Check if we should retry
                should_retry, delay = error_handler.should_retry(error_info, attempt, self.config.retry_attempts)
                
                if should_retry and attempt < self.config.retry_attempts:
                    logger.warning(f"Bedrock API呼び出し失敗 (試行 {attempt + 1}/{self.config.retry_attempts + 1}): "
                                 f"{error_info.category.value}. {delay}秒後に再試行します")
                    time.sleep(delay)
                    continue
                else:
                    # Final attempt failed or error is not retryable
                    logger.error(f"Bedrock API呼び出しが最終的に失敗: {error_info.message}")
                    
                    # Log user-friendly error message
                    user_message = error_handler.format_user_message(error_info, include_actions=True)
                    logger.info(f"ユーザー向けエラーメッセージ: {user_message}")
                    
                    return self._handle_api_errors(e)
        
        return []
    
    def _perform_retrieval(self, query: str) -> List[NodeWithScore]:
        """
        Perform the actual retrieval from Bedrock KnowledgeBase.
        
        Args:
            query: Search query string
            
        Returns:
            List[NodeWithScore]: Retrieved documents with scores
        """
        try:
            # Call Bedrock KnowledgeBase retrieve API
            response = self.client.retrieve(
                knowledgeBaseId=self.config.knowledge_base_id,
                retrievalQuery={
                    'text': query
                },
                retrievalConfiguration={
                    'vectorSearchConfiguration': {
                        'numberOfResults': self.config.similarity_top_k
                    }
                }
            )
            
            # Convert response to NodeWithScore format
            nodes = []
            retrieval_results = response.get('retrievalResults', [])
            
            logger.info(f"Bedrock KnowledgeBaseから{len(retrieval_results)}件の結果を取得しました")
            
            for result in retrieval_results:
                # Extract content and metadata
                content = result.get('content', {}).get('text', '')
                score = result.get('score', 0.0)
                
                # Apply confidence threshold filter
                if score < self.config.confidence_threshold:
                    logger.debug(f"信頼度スコア {score} が閾値 {self.config.confidence_threshold} を下回るため結果をスキップします")
                    continue
                
                # Extract metadata
                metadata = {
                    'source': 'bedrock',
                    'knowledge_base_id': self.config.knowledge_base_id,
                    'score': score
                }
                
                # Add location information if available
                if 'location' in result:
                    location = result['location']
                    if location.get('type') == 'S3':
                        s3_location = location.get('s3Location', {})
                        metadata['s3_uri'] = s3_location.get('uri', '')
                        metadata['file_name'] = s3_location.get('uri', '').split('/')[-1] if s3_location.get('uri') else ''
                
                # Create TextNode with content and metadata
                text_node = TextNode(
                    text=content,
                    metadata=metadata
                )
                
                # Create NodeWithScore
                node_with_score = NodeWithScore(
                    node=text_node,
                    score=score
                )
                
                nodes.append(node_with_score)
            
            logger.info(f"信頼度フィルタ後: {len(nodes)}件の結果を返します")
            return nodes
            
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')
            error_message = e.response.get('Error', {}).get('Message', str(e))
            logger.error(f"Bedrock KnowledgeBase API エラー [{error_code}]: {error_message}")
            raise
        
        except Exception as e:
            logger.error(f"文書検索中に予期しないエラーが発生しました: {e}")
            raise
    
    def _calculate_backoff_delay(self, attempt: int) -> float:
        """
        Calculate exponential backoff delay.
        
        Args:
            attempt: Current attempt number (0-based)
            
        Returns:
            float: Delay in seconds
        """
        base_delay = 1.0
        max_delay = 60.0
        delay = min(base_delay * (2 ** attempt), max_delay)
        return delay
    
    def _handle_api_errors(self, error: Exception) -> List[NodeWithScore]:
        """
        Handle API errors and return appropriate response with enhanced error categorization.
        
        Args:
            error: The exception that occurred
            
        Returns:
            List[NodeWithScore]: Empty list or fallback results
        """
        error_category = self._categorize_error(error)
        
        if isinstance(error, ClientError):
            error_code = error.response.get('Error', {}).get('Code', 'Unknown')
            error_message = error.response.get('Error', {}).get('Message', str(error))
            
            # Handle specific error types with detailed logging
            if error_code == 'ResourceNotFoundException':
                logger.error(f"KnowledgeBase '{self.config.knowledge_base_id}' が見つかりません。"
                           f"KnowledgeBase IDが正しいか、指定されたリージョン '{self.config.region}' で利用可能か確認してください。")
            elif error_code == 'AccessDeniedException':
                logger.error("KnowledgeBaseへのアクセスが拒否されました。"
                           "IAM権限で 'bedrock:Retrieve' アクションが許可されているか確認してください。")
            elif error_code == 'ThrottlingException':
                logger.error("API呼び出しがレート制限されました。リクエスト頻度を下げてください。")
            elif error_code == 'ValidationException':
                logger.error(f"リクエストパラメータが無効です: {error_message}")
            elif error_code == 'ServiceUnavailableException':
                logger.error("Bedrock KnowledgeBaseサービスが一時的に利用できません。")
            elif error_code == 'InternalServerException':
                logger.error("Bedrock内部サーバーエラーが発生しました。")
            else:
                logger.error(f"Bedrock API エラー [{error_code}]: {error_message}")
        
        elif isinstance(error, NoCredentialsError):
            logger.error("AWS認証情報が見つかりません。AWS認証情報を設定してください。")
        
        else:
            logger.error(f"予期しないエラー: {error}")
        
        # Log error category for monitoring
        logger.info(f"エラーカテゴリ: {error_category}")
        
        # Return empty results - fallback will be handled at higher level
        return []
    
    def _categorize_error(self, error: Exception) -> str:
        """
        Categorize errors for better error handling and monitoring.
        
        Args:
            error: The exception that occurred
            
        Returns:
            str: Error category
        """
        if isinstance(error, ClientError):
            error_code = error.response.get('Error', {}).get('Code', 'Unknown')
            
            # Categorize AWS errors
            if error_code in ['ResourceNotFoundException', 'ValidationException']:
                return 'configuration_error'
            elif error_code in ['AccessDeniedException']:
                return 'authentication_error'
            elif error_code in ['ThrottlingException']:
                return 'rate_limit_error'
            elif error_code in ['ServiceUnavailableException', 'InternalServerException']:
                return 'service_error'
            else:
                return 'api_error'
        
        elif isinstance(error, NoCredentialsError):
            return 'authentication_error'
        
        elif isinstance(error, (ConnectionError, TimeoutError)):
            return 'network_error'
        
        else:
            return 'unknown_error'
    
    def get_knowledge_base_info(self) -> Dict[str, Any]:
        """
        Get information about the configured KnowledgeBase.
        
        Returns:
            Dict[str, Any]: KnowledgeBase information
        """
        try:
            # Note: This would require bedrock-agent client, not bedrock-agent-runtime
            # For now, return basic configuration info
            return {
                'knowledge_base_id': self.config.knowledge_base_id,
                'region': self.config.region,
                'similarity_top_k': self.config.similarity_top_k,
                'confidence_threshold': self.config.confidence_threshold,
                'status': 'configured'
            }
        except Exception as e:
            logger.error(f"KnowledgeBase情報の取得に失敗しました: {e}")
            return {
                'knowledge_base_id': self.config.knowledge_base_id,
                'region': self.config.region,
                'status': 'error',
                'error': str(e)
            }


def create_bedrock_retriever(
    knowledge_base_id: str,
    region: str = "us-east-1",
    similarity_top_k: int = 5,
    confidence_threshold: float = 0.0,
    **kwargs
) -> BedrockKnowledgeBaseRetriever:
    """
    Create a Bedrock KnowledgeBase retriever with default configuration.
    
    Args:
        knowledge_base_id: The KnowledgeBase ID
        region: AWS region
        similarity_top_k: Number of results to retrieve
        confidence_threshold: Minimum confidence score
        **kwargs: Additional configuration parameters
        
    Returns:
        BedrockKnowledgeBaseRetriever: Configured retriever instance
    """
    config = KnowledgeBaseConfig(
        knowledge_base_id=knowledge_base_id,
        region=region,
        similarity_top_k=similarity_top_k,
        confidence_threshold=confidence_threshold,
        mode="bedrock",
        **kwargs
    )
    
    return BedrockKnowledgeBaseRetriever(config)


def convert_bedrock_to_llama_nodes(bedrock_results: List[Dict[str, Any]]) -> List[NodeWithScore]:
    """
    Convert Bedrock KnowledgeBase results to llama_index NodeWithScore format.
    
    This utility function ensures proper conversion of Bedrock API responses
    to the format expected by llama_index chat engines.
    
    Args:
        bedrock_results: Raw results from Bedrock KnowledgeBase API
        
    Returns:
        List[NodeWithScore]: Converted nodes with scores
    """
    nodes = []
    
    for result in bedrock_results:
        try:
            # Extract content and metadata
            content = result.get('content', {}).get('text', '')
            score = result.get('score', 0.0)
            
            if not content:
                logger.warning("Bedrock結果に内容がありません。スキップします。")
                continue
            
            # Extract metadata
            metadata = {
                'source': 'bedrock',
                'score': score,
                'bedrock_result_id': result.get('id', ''),
                'retrieval_timestamp': time.time()
            }
            
            # Add location information if available
            if 'location' in result:
                location = result['location']
                if location.get('type') == 'S3':
                    s3_location = location.get('s3Location', {})
                    metadata['s3_uri'] = s3_location.get('uri', '')
                    metadata['file_name'] = s3_location.get('uri', '').split('/')[-1] if s3_location.get('uri') else ''
                    
            # Add any additional metadata from the result
            if 'metadata' in result:
                metadata.update(result['metadata'])
            
            # Create TextNode with proper formatting for chat engines
            text_node = TextNode(
                text=content,
                metadata=metadata,
                id_=result.get('id', f"bedrock_{len(nodes)}")
            )
            
            # Create NodeWithScore
            node_with_score = NodeWithScore(
                node=text_node,
                score=score
            )
            
            nodes.append(node_with_score)
            
        except Exception as e:
            logger.error(f"Bedrock結果の変換中にエラーが発生しました: {e}")
            continue
    
    logger.info(f"Bedrock結果 {len(bedrock_results)} 件を llama_index形式 {len(nodes)} 件に変換しました")
    return nodes


def ensure_chat_engine_compatibility(nodes: List[NodeWithScore]) -> List[NodeWithScore]:
    """
    Ensure nodes are properly formatted for chat engine compatibility.
    
    This function validates and enhances nodes to ensure they work properly
    with llama_index chat engines.
    
    Args:
        nodes: List of NodeWithScore objects
        
    Returns:
        List[NodeWithScore]: Enhanced nodes for chat engine compatibility
    """
    enhanced_nodes = []
    
    for i, node_with_score in enumerate(nodes):
        try:
            node = node_with_score.node
            score = node_with_score.score
            
            # Ensure node has required attributes
            if not hasattr(node, 'text') or not node.text:
                logger.warning(f"ノード {i} にテキストがありません。スキップします。")
                continue
            
            # Ensure metadata exists
            if not hasattr(node, 'metadata') or node.metadata is None:
                node.metadata = {}
            
            # Ensure node has an ID
            if not hasattr(node, 'id_') or not node.id_:
                node.id_ = f"node_{i}_{hash(node.text[:100])}"
            
            # Add chat engine specific metadata
            node.metadata.update({
                'node_index': i,
                'text_length': len(node.text),
                'processed_for_chat': True
            })
            
            # Ensure score is valid
            if not isinstance(score, (int, float)) or score < 0:
                logger.warning(f"ノード {i} の無効なスコア: {score}. デフォルト値0.5を使用します。")
                score = 0.5
            
            enhanced_node = NodeWithScore(
                node=node,
                score=score
            )
            
            enhanced_nodes.append(enhanced_node)
            
        except Exception as e:
            logger.error(f"ノード {i} の拡張中にエラーが発生しました: {e}")
            continue
    
    logger.info(f"チャットエンジン互換性のため {len(nodes)} ノードを {len(enhanced_nodes)} ノードに処理しました")
    return enhanced_nodes