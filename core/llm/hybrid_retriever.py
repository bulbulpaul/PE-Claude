"""
Hybrid Retriever Module

This module provides hybrid search functionality that combines local file-based search
with Amazon Bedrock KnowledgeBase search. It includes result merging, ranking, and
mode management capabilities.

@reference: PE-GPT: a New Paradigm for Power Electronics Design, by Fanfan Lin, Xinze Li, et al.
@code-author: Xinze Li, Fanfan Lin
@github: https://github.com/XinzeLee/PE-GPT
"""

import logging
from typing import List, Dict, Any, Optional, Union
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

from llama_index.core.schema import NodeWithScore, TextNode
from llama_index.core.retrievers import BaseRetriever
from llama_index.core.base.base_query_engine import BaseQueryEngine
from botocore.exceptions import ClientError

from core.knowledge.kb_config import KnowledgeBaseConfig
from core.llm.bedrock_kb_retriever import BedrockKnowledgeBaseRetriever
from core.llm.error_handler import get_error_handler, handle_error, format_error_for_user

logger = logging.getLogger(__name__)


class HybridRetriever(BaseRetriever):
    """
    ローカルとBedrock KnowledgeBaseの結果を統合する検索クラス
    
    This class provides hybrid search functionality that can combine results
    from local file-based search and Amazon Bedrock KnowledgeBase search.
    It supports different search modes and intelligent result merging.
    """
    
    def __init__(
        self,
        local_retriever: Optional[BaseRetriever] = None,
        bedrock_retriever: Optional[BedrockKnowledgeBaseRetriever] = None,
        config: Optional[KnowledgeBaseConfig] = None,
        mode: str = "hybrid"
    ):
        """
        Initialize hybrid retriever.
        
        Args:
            local_retriever: Local file-based retriever (VectorStoreIndex retriever)
            bedrock_retriever: Bedrock KnowledgeBase retriever
            config: KnowledgeBase configuration (used if bedrock_retriever not provided)
            mode: Search mode - "local", "bedrock", or "hybrid"
        """
        super().__init__()
        self.local_retriever = local_retriever
        self.bedrock_retriever = bedrock_retriever
        self.config = config
        self.mode = mode
        
        # Validate configuration
        self._validate_configuration()
        
        # Initialize Bedrock retriever if config provided but retriever not
        if not self.bedrock_retriever and self.config and self.config.is_bedrock_enabled():
            try:
                self.bedrock_retriever = BedrockKnowledgeBaseRetriever(self.config)
                logger.info("Bedrock KnowledgeBase retriever initialized from config")
            except Exception as e:
                logger.warning(f"Bedrock retriever initialization failed: {e}")
                if self.mode == "bedrock":
                    # If bedrock-only mode fails, this is a critical error
                    raise ValueError(f"Bedrock-only mode requested but initialization failed: {e}")
                # For hybrid mode, we can continue with local only
                self.mode = "local"
                logger.info("Falling back to local-only mode")
    
    def _validate_configuration(self):
        """
        Validate retriever configuration.
        
        Raises:
            ValueError: If configuration is invalid
        """
        valid_modes = ["local", "bedrock", "hybrid"]
        if self.mode not in valid_modes:
            raise ValueError(f"Invalid mode: {self.mode}. Must be one of {valid_modes}")
        
        if self.mode == "local" and not self.local_retriever:
            raise ValueError("Local mode requires local_retriever")
        
        if self.mode == "bedrock" and not self.bedrock_retriever and not self.config:
            raise ValueError("Bedrock mode requires bedrock_retriever or config")
        
        if self.mode == "hybrid":
            if not self.local_retriever and not self.bedrock_retriever and not self.config:
                raise ValueError("Hybrid mode requires at least one retriever or config")
    
    def _retrieve(self, query_bundle) -> List[NodeWithScore]:
        """
        Retrieve documents using the configured mode.
        
        Args:
            query_bundle: Query bundle containing the search query
            
        Returns:
            List[NodeWithScore]: Retrieved documents with scores
        """
        query_str = query_bundle.query_str if hasattr(query_bundle, 'query_str') else str(query_bundle)
        return self.retrieve(query_str)
    
    def retrieve(self, query: str) -> List[NodeWithScore]:
        """
        Retrieve documents based on the configured search mode with enhanced error handling.
        
        Args:
            query: Search query string
            
        Returns:
            List[NodeWithScore]: Retrieved and ranked documents
        """
        if not query or not query.strip():
            logger.warning("Empty query provided")
            return []
        
        query = query.strip()
        error_handler = get_error_handler()
        
        try:
            if self.mode == "local":
                return self._retrieve_local_only(query)
            elif self.mode == "bedrock":
                return self._retrieve_bedrock_only(query)
            elif self.mode == "hybrid":
                return self._retrieve_hybrid(query)
            else:
                error_msg = f"Unknown search mode: {self.mode}"
                logger.error(error_msg)
                # Create a ValueError for proper error handling
                error = ValueError(error_msg)
                error_info = error_handler.handle_error(error, "Invalid search mode")
                return []
                
        except Exception as e:
            # Use enhanced error handler
            error_info = error_handler.handle_error(e, f"Hybrid retrieval in {self.mode} mode")
            
            # Log user-friendly error message
            user_message = error_handler.format_user_message(error_info, include_actions=False)
            logger.info(f"検索エラー: {user_message}")
            
            # Attempt fallback if enabled
            return self._handle_retrieval_error(query, e)
    
    def _retrieve_local_only(self, query: str) -> List[NodeWithScore]:
        """
        Retrieve documents from local source only.
        
        Args:
            query: Search query string
            
        Returns:
            List[NodeWithScore]: Local search results
        """
        if not self.local_retriever:
            logger.warning("Local retriever not available")
            return []
        
        try:
            logger.info(f"Performing local-only search for: {query[:50]}...")
            results = self.local_retriever.retrieve(query)
            
            # Add source metadata
            for result in results:
                if hasattr(result.node, 'metadata'):
                    result.node.metadata['source'] = 'local'
                else:
                    result.node.metadata = {'source': 'local'}
            
            logger.info(f"Local search returned {len(results)} results")
            return results
            
        except Exception as e:
            logger.error(f"Local search failed: {e}")
            return []
    
    def _retrieve_bedrock_only(self, query: str) -> List[NodeWithScore]:
        """
        Retrieve documents from Bedrock KnowledgeBase only.
        
        Args:
            query: Search query string
            
        Returns:
            List[NodeWithScore]: Bedrock search results
        """
        if not self.bedrock_retriever:
            logger.warning("Bedrock retriever not available")
            return []
        
        try:
            logger.info(f"Performing Bedrock-only search for: {query[:50]}...")
            results = self.bedrock_retriever.retrieve(query)
            
            # Ensure chat engine compatibility
            from core.llm.bedrock_kb_retriever import ensure_chat_engine_compatibility
            results = ensure_chat_engine_compatibility(results)
            
            logger.info(f"Bedrock search returned {len(results)} results")
            return results
            
        except Exception as e:
            logger.error(f"Bedrock search failed: {e}")
            # For bedrock-only mode, try fallback if enabled
            if self.mode == "bedrock":
                return self._handle_retrieval_error(query, e)
            return []
    
    def _retrieve_hybrid(self, query: str) -> List[NodeWithScore]:
        """
        Retrieve documents from both local and Bedrock sources.
        
        Args:
            query: Search query string
            
        Returns:
            List[NodeWithScore]: Merged and ranked results
        """
        logger.info(f"Performing hybrid search for: {query[:50]}...")
        
        local_results = []
        bedrock_results = []
        
        # Use parallel execution for better performance
        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = {}
            
            # Submit local search if available
            if self.local_retriever:
                futures['local'] = executor.submit(self._retrieve_local_only, query)
            
            # Submit Bedrock search if available
            if self.bedrock_retriever:
                futures['bedrock'] = executor.submit(self._retrieve_bedrock_only, query)
            
            # Collect results
            for source, future in futures.items():
                try:
                    results = future.result(timeout=30)  # 30 second timeout
                    if source == 'local':
                        local_results = results
                    elif source == 'bedrock':
                        bedrock_results = results
                except Exception as e:
                    logger.warning(f"{source} search failed in hybrid mode: {e}")
        
        # Merge and rank results
        merged_results = self._merge_results(local_results, bedrock_results)
        ranked_results = self._rank_by_relevance(merged_results)
        
        # Ensure chat engine compatibility for final results
        from core.llm.bedrock_kb_retriever import ensure_chat_engine_compatibility
        ranked_results = ensure_chat_engine_compatibility(ranked_results)
        
        logger.info(f"Hybrid search completed: {len(local_results)} local + {len(bedrock_results)} bedrock = {len(ranked_results)} final results")
        
        return ranked_results
    
    def _merge_results(
        self, 
        local_results: List[NodeWithScore], 
        bedrock_results: List[NodeWithScore]
    ) -> List[NodeWithScore]:
        """
        Merge results from local and Bedrock sources.
        
        Args:
            local_results: Results from local search
            bedrock_results: Results from Bedrock search
            
        Returns:
            List[NodeWithScore]: Merged results with deduplication
        """
        if not local_results and not bedrock_results:
            return []
        
        if not local_results:
            return bedrock_results
        
        if not bedrock_results:
            return local_results
        
        # Combine all results
        all_results = local_results + bedrock_results
        
        # Simple deduplication based on content similarity
        # This is a basic implementation - could be enhanced with more sophisticated methods
        deduplicated_results = self._deduplicate_results(all_results)
        
        logger.info(f"Merged {len(local_results)} local + {len(bedrock_results)} bedrock results into {len(deduplicated_results)} unique results")
        
        return deduplicated_results
    
    def _deduplicate_results(self, results: List[NodeWithScore]) -> List[NodeWithScore]:
        """
        Remove duplicate results based on content similarity.
        
        Args:
            results: List of results to deduplicate
            
        Returns:
            List[NodeWithScore]: Deduplicated results
        """
        if len(results) <= 1:
            return results
        
        unique_results = []
        seen_content = set()
        
        for result in results:
            # Get text content for comparison
            content = result.node.text if hasattr(result.node, 'text') else str(result.node)
            
            # Simple content-based deduplication
            # Use first 200 characters as a fingerprint
            content_fingerprint = content[:200].strip().lower()
            
            if content_fingerprint not in seen_content:
                seen_content.add(content_fingerprint)
                unique_results.append(result)
            else:
                # If duplicate found, keep the one with higher score
                for i, existing_result in enumerate(unique_results):
                    existing_content = existing_result.node.text if hasattr(existing_result.node, 'text') else str(existing_result.node)
                    existing_fingerprint = existing_content[:200].strip().lower()
                    
                    if existing_fingerprint == content_fingerprint:
                        if result.score > existing_result.score:
                            unique_results[i] = result
                        break
        
        logger.debug(f"Deduplication: {len(results)} -> {len(unique_results)} results")
        return unique_results
    
    def _rank_by_relevance(self, results: List[NodeWithScore]) -> List[NodeWithScore]:
        """
        Rank results by relevance score with source-aware scoring.
        
        Args:
            results: List of results to rank
            
        Returns:
            List[NodeWithScore]: Ranked results
        """
        if not results:
            return results
        
        # Apply source-aware scoring adjustments
        adjusted_results = []
        
        for result in results:
            adjusted_result = result
            source = result.node.metadata.get('source', 'unknown') if hasattr(result.node, 'metadata') else 'unknown'
            
            # Apply source-specific score adjustments
            # This is a simple implementation - could be made configurable
            if source == 'bedrock':
                # Bedrock results might be more authoritative for some use cases
                # Slight boost for Bedrock results
                adjusted_score = min(result.score * 1.05, 1.0)
            elif source == 'local':
                # Local results are domain-specific and might be more relevant
                # Keep original score
                adjusted_score = result.score
            else:
                adjusted_score = result.score
            
            # Create new NodeWithScore with adjusted score
            adjusted_result = NodeWithScore(
                node=result.node,
                score=adjusted_score
            )
            
            adjusted_results.append(adjusted_result)
        
        # Sort by score (descending)
        ranked_results = sorted(adjusted_results, key=lambda x: x.score, reverse=True)
        
        # Apply top-k limit if configured
        if self.config and hasattr(self.config, 'similarity_top_k'):
            max_results = self.config.similarity_top_k
            if len(ranked_results) > max_results:
                ranked_results = ranked_results[:max_results]
                logger.info(f"Limited results to top {max_results} based on configuration")
        
        return ranked_results
    
    def _handle_retrieval_error(self, query: str, error: Exception) -> List[NodeWithScore]:
        """
        Handle retrieval errors with enhanced fallback logic and error categorization.
        
        Args:
            query: Original search query
            error: The error that occurred
            
        Returns:
            List[NodeWithScore]: Fallback results or empty list
        """
        error_category = self._categorize_retrieval_error(error)
        logger.error(f"Retrieval error (category: {error_category}): {error}")
        
        # Check if fallback is enabled
        if not self.config or not self.config.enable_fallback:
            logger.info("Fallback disabled, returning empty results")
            self._log_fallback_decision("disabled", error_category)
            return []
        
        # Determine fallback strategy based on error category and current mode
        fallback_strategy = self._determine_fallback_strategy(error_category)
        logger.info(f"Applying fallback strategy: {fallback_strategy}")
        
        # Try fallback based on strategy
        try:
            if fallback_strategy == "local_fallback" and self.local_retriever:
                logger.info("Falling back to local search")
                results = self._retrieve_local_only(query)
                self._log_fallback_success("local", len(results))
                return results
                
            elif fallback_strategy == "bedrock_fallback" and self.bedrock_retriever:
                logger.info("Falling back to Bedrock search")
                results = self._retrieve_bedrock_only(query)
                self._log_fallback_success("bedrock", len(results))
                return results
                
            elif fallback_strategy == "partial_hybrid":
                # For hybrid mode, try individual retrievers
                if self.local_retriever:
                    logger.info("Attempting local-only fallback for hybrid mode")
                    results = self._retrieve_local_only(query)
                    if results:
                        self._log_fallback_success("local_partial", len(results))
                        return results
                
                if self.bedrock_retriever:
                    logger.info("Attempting Bedrock-only fallback for hybrid mode")
                    results = self._retrieve_bedrock_only(query)
                    if results:
                        self._log_fallback_success("bedrock_partial", len(results))
                        return results
                        
            elif fallback_strategy == "retry_with_delay":
                # For transient errors, suggest retry
                logger.info("Transient error detected. Consider retrying after a delay.")
                
        except Exception as fallback_error:
            fallback_error_category = self._categorize_retrieval_error(fallback_error)
            logger.error(f"Fallback also failed (category: {fallback_error_category}): {fallback_error}")
            self._log_fallback_failure(fallback_strategy, fallback_error_category)
        
        logger.warning("All retrieval methods failed, returning empty results")
        self._log_fallback_decision("exhausted", error_category)
        return []
    
    def _categorize_retrieval_error(self, error: Exception) -> str:
        """
        Categorize retrieval errors for better fallback decision making.
        
        Args:
            error: The exception that occurred
            
        Returns:
            str: Error category
        """
        # Check for AWS ClientError first
        if isinstance(error, ClientError):
            error_code = error.response.get('Error', {}).get('Code', 'Unknown')
            if error_code == 'ThrottlingException':
                return "bedrock_rate_limit"
            elif error_code == 'AccessDeniedException':
                return "bedrock_auth_error"
            elif error_code == 'ResourceNotFoundException':
                return "bedrock_config_error"
            elif error_code in ['ServiceUnavailableException', 'InternalServerException']:
                return "bedrock_service_error"
            else:
                return "bedrock_api_error"
        
        # Check string patterns for other errors
        error_str = str(error).lower()
        
        # Check for specific error patterns
        if "bedrock" in error_str and ("credentials" in error_str or "authentication" in error_str):
            return "bedrock_auth_error"
        elif "bedrock" in error_str and ("throttling" in error_str or "rate" in error_str):
            return "bedrock_rate_limit"
        elif "bedrock" in error_str and ("service" in error_str or "unavailable" in error_str):
            return "bedrock_service_error"
        elif "bedrock" in error_str and ("resource" in error_str or "not found" in error_str):
            return "bedrock_config_error"
        elif "network" in error_str or "connection" in error_str or "timeout" in error_str:
            return "network_error"
        elif "local" in error_str or "file" in error_str or "directory" in error_str:
            return "local_error"
        else:
            return "unknown_error"
    
    def _determine_fallback_strategy(self, error_category: str) -> str:
        """
        Determine the appropriate fallback strategy based on error category and current mode.
        
        Args:
            error_category: The categorized error type
            
        Returns:
            str: Fallback strategy to apply
        """
        if self.mode == "bedrock":
            # For Bedrock-only mode, always try local fallback if available
            if error_category in ["bedrock_auth_error", "bedrock_config_error", "bedrock_service_error"]:
                return "local_fallback"
            elif error_category == "bedrock_rate_limit":
                return "retry_with_delay"
            else:
                return "local_fallback"
                
        elif self.mode == "local":
            # For local-only mode, try Bedrock fallback if available
            if error_category == "local_error":
                return "bedrock_fallback"
            else:
                return "bedrock_fallback"
                
        elif self.mode == "hybrid":
            # For hybrid mode, try partial retrieval
            if error_category.startswith("bedrock_"):
                return "partial_hybrid"  # Try local only
            elif error_category == "local_error":
                return "partial_hybrid"  # Try Bedrock only
            else:
                return "partial_hybrid"  # Try both individually
        
        return "local_fallback"  # Default fallback
    
    def _log_fallback_decision(self, decision: str, error_category: str):
        """
        Log fallback decisions for monitoring and debugging.
        
        Args:
            decision: The fallback decision made
            error_category: The error category that triggered the decision
        """
        logger.info(f"Fallback decision: {decision} (triggered by: {error_category})")
    
    def _log_fallback_success(self, fallback_type: str, result_count: int):
        """
        Log successful fallback operations.
        
        Args:
            fallback_type: The type of fallback that succeeded
            result_count: Number of results returned by fallback
        """
        logger.info(f"Fallback successful: {fallback_type} returned {result_count} results")
    
    def _log_fallback_failure(self, strategy: str, error_category: str):
        """
        Log failed fallback operations.
        
        Args:
            strategy: The fallback strategy that failed
            error_category: The error category of the fallback failure
        """
        logger.warning(f"Fallback strategy '{strategy}' failed with error category: {error_category}")
    
    def get_retriever_info(self) -> Dict[str, Any]:
        """
        Get information about the configured retrievers.
        
        Returns:
            Dict[str, Any]: Retriever configuration and status information
        """
        info = {
            'mode': self.mode,
            'local_available': self.local_retriever is not None,
            'bedrock_available': self.bedrock_retriever is not None,
            'fallback_enabled': self.config.enable_fallback if self.config else False
        }
        
        if self.bedrock_retriever and hasattr(self.bedrock_retriever, 'get_knowledge_base_info'):
            info['bedrock_info'] = self.bedrock_retriever.get_knowledge_base_info()
        
        return info
    
    def set_mode(self, mode: str):
        """
        Change the search mode dynamically.
        
        Args:
            mode: New search mode ("local", "bedrock", or "hybrid")
            
        Raises:
            ValueError: If mode is invalid or required retrievers are not available
        """
        valid_modes = ["local", "bedrock", "hybrid"]
        if mode not in valid_modes:
            raise ValueError(f"Invalid mode: {mode}. Must be one of {valid_modes}")
        
        # Validate that required retrievers are available for the new mode
        if mode == "local" and not self.local_retriever:
            raise ValueError("Cannot set local mode: local retriever not available")
        
        if mode == "bedrock" and not self.bedrock_retriever:
            raise ValueError("Cannot set bedrock mode: Bedrock retriever not available")
        
        old_mode = self.mode
        self.mode = mode
        logger.info(f"Search mode changed from '{old_mode}' to '{mode}'")


class SearchModeManager:
    """
    Utility class for managing search modes and their configurations.
    
    This class provides centralized management of search modes, validation,
    and dynamic mode switching capabilities.
    """
    
    VALID_MODES = ["local", "bedrock", "hybrid"]
    DEFAULT_MODE = "hybrid"
    
    def __init__(self, initial_mode: str = None):
        """
        Initialize search mode manager.
        
        Args:
            initial_mode: Initial search mode (defaults to hybrid)
        """
        self.current_mode = initial_mode or self.DEFAULT_MODE
        self.mode_history = [self.current_mode]
        self.validate_mode(self.current_mode)
    
    @classmethod
    def validate_mode(cls, mode: str) -> bool:
        """
        Validate if a mode is supported.
        
        Args:
            mode: Mode to validate
            
        Returns:
            bool: True if mode is valid
            
        Raises:
            ValueError: If mode is invalid
        """
        if mode not in cls.VALID_MODES:
            raise ValueError(f"Invalid mode: {mode}. Valid modes are: {cls.VALID_MODES}")
        return True
    
    def set_mode(self, mode: str) -> str:
        """
        Set the current search mode.
        
        Args:
            mode: New search mode
            
        Returns:
            str: Previous mode
            
        Raises:
            ValueError: If mode is invalid
        """
        self.validate_mode(mode)
        previous_mode = self.current_mode
        self.current_mode = mode
        self.mode_history.append(mode)
        
        logger.info(f"Search mode changed: {previous_mode} -> {mode}")
        return previous_mode
    
    def get_mode(self) -> str:
        """
        Get the current search mode.
        
        Returns:
            str: Current search mode
        """
        return self.current_mode
    
    def get_mode_history(self) -> List[str]:
        """
        Get the history of mode changes.
        
        Returns:
            List[str]: Mode change history
        """
        return self.mode_history.copy()
    
    def is_local_enabled(self) -> bool:
        """
        Check if local search is enabled in current mode.
        
        Returns:
            bool: True if local search is enabled
        """
        return self.current_mode in ["local", "hybrid"]
    
    def is_bedrock_enabled(self) -> bool:
        """
        Check if Bedrock search is enabled in current mode.
        
        Returns:
            bool: True if Bedrock search is enabled
        """
        return self.current_mode in ["bedrock", "hybrid"]
    
    def get_mode_description(self, mode: str = None) -> str:
        """
        Get a human-readable description of a search mode.
        
        Args:
            mode: Mode to describe (defaults to current mode)
            
        Returns:
            str: Mode description
        """
        target_mode = mode or self.current_mode
        
        descriptions = {
            "local": "ローカルファイルのみを検索対象とします。高速で、ローカルに保存された専門的な文書に最適です。",
            "bedrock": "Amazon Bedrock KnowledgeBaseのみを検索対象とします。クラウド上の大規模な知識ベースにアクセスできます。",
            "hybrid": "ローカルファイルとBedrock KnowledgeBaseの両方を検索し、結果を統合します。最も包括的な検索結果を提供します。"
        }
        
        return descriptions.get(target_mode, f"Unknown mode: {target_mode}")
    
    def get_recommended_mode(
        self, 
        has_local: bool, 
        has_bedrock: bool, 
        prefer_speed: bool = False
    ) -> str:
        """
        Get recommended search mode based on available resources and preferences.
        
        Args:
            has_local: Whether local retriever is available
            has_bedrock: Whether Bedrock retriever is available
            prefer_speed: Whether to prefer faster modes
            
        Returns:
            str: Recommended search mode
        """
        if not has_local and not has_bedrock:
            raise ValueError("No retrievers available")
        
        if not has_local:
            return "bedrock"
        
        if not has_bedrock:
            return "local"
        
        # Both available
        if prefer_speed:
            return "local"  # Local is typically faster
        else:
            return "hybrid"  # Hybrid provides most comprehensive results
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert mode manager state to dictionary.
        
        Returns:
            Dict[str, Any]: Mode manager state
        """
        return {
            "current_mode": self.current_mode,
            "mode_history": self.mode_history,
            "valid_modes": self.VALID_MODES,
            "local_enabled": self.is_local_enabled(),
            "bedrock_enabled": self.is_bedrock_enabled()
        }


def create_hybrid_retriever(
    local_retriever: Optional[BaseRetriever] = None,
    knowledge_base_config: Optional[KnowledgeBaseConfig] = None,
    mode: str = "hybrid"
) -> HybridRetriever:
    """
    Create a hybrid retriever with the specified configuration.
    
    Args:
        local_retriever: Local file-based retriever
        knowledge_base_config: Bedrock KnowledgeBase configuration
        mode: Search mode ("local", "bedrock", or "hybrid")
        
    Returns:
        HybridRetriever: Configured hybrid retriever instance
    """
    return HybridRetriever(
        local_retriever=local_retriever,
        config=knowledge_base_config,
        mode=mode
)


def create_mode_manager(initial_mode: str = None) -> SearchModeManager:
    """
    Create a search mode manager with the specified initial mode.
    
    Args:
        initial_mode: Initial search mode (defaults to hybrid)
        
    Returns:
        SearchModeManager: Configured mode manager instance
    """
    return SearchModeManager(initial_mode)