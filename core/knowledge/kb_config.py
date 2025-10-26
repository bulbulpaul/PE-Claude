"""
KnowledgeBase Configuration Module

This module provides configuration management for Amazon Bedrock KnowledgeBase integration.
It includes validation, error handling, and configuration data structures.

@reference: PE-GPT: a New Paradigm for Power Electronics Design, by Fanfan Lin, Xinze Li, et al.
@code-author: Xinze Li, Fanfan Lin
@github: https://github.com/XinzeLee/PE-GPT
"""

import os
import re
from dataclasses import dataclass
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)


@dataclass
class KnowledgeBaseConfig:
    """
    Configuration class for Amazon Bedrock KnowledgeBase integration.
    
    This class manages all configuration parameters needed for KnowledgeBase
    operations including validation and error handling.
    """
    
    knowledge_base_id: str
    region: str = "us-east-1"
    similarity_top_k: int = 5
    confidence_threshold: float = 0.0
    mode: str = "hybrid"  # "local", "bedrock", "hybrid"
    enable_fallback: bool = True
    retry_attempts: int = 3
    
    def __post_init__(self):
        """
        Post-initialization validation for configuration parameters.
        
        Validates:
        - KnowledgeBase ID format
        - Region format (single region only)
        - Parameter ranges and types
        
        Raises:
            ValueError: If any configuration parameter is invalid
        """
        self._validate_knowledge_base_id()
        self._validate_region()
        self._validate_similarity_top_k()
        self._validate_confidence_threshold()
        self._validate_mode()
        self._validate_retry_attempts()
    
    def _validate_knowledge_base_id(self):
        """Validate KnowledgeBase ID format."""
        if not self.knowledge_base_id:
            raise ValueError("KnowledgeBase IDは必須です")
        
        if not isinstance(self.knowledge_base_id, str):
            raise ValueError("KnowledgeBase IDは文字列である必要があります")
        
        # Basic format validation for AWS KnowledgeBase ID
        if not re.match(r'^[A-Z0-9]{10}$', self.knowledge_base_id):
            logger.warning(f"KnowledgeBase ID '{self.knowledge_base_id}' の形式が一般的でない可能性があります")
    
    def _validate_region(self):
        """Validate AWS region format (single region only)."""
        if not self.region:
            raise ValueError("リージョンは必須です")
        
        if not isinstance(self.region, str):
            raise ValueError("リージョンは単一の文字列で指定してください")
        
        # Validate AWS region format
        if not re.match(r'^[a-z]{2}-[a-z]+-\d+$', self.region):
            raise ValueError(f"リージョン形式が正しくありません: {self.region} (例: us-east-1)")
    
    def _validate_similarity_top_k(self):
        """Validate similarity_top_k parameter."""
        if not isinstance(self.similarity_top_k, int):
            raise ValueError("similarity_top_kは整数である必要があります")
        
        if self.similarity_top_k < 1 or self.similarity_top_k > 100:
            raise ValueError("similarity_top_kは1から100の間である必要があります")
    
    def _validate_confidence_threshold(self):
        """Validate confidence threshold parameter."""
        if not isinstance(self.confidence_threshold, (int, float)):
            raise ValueError("confidence_thresholdは数値である必要があります")
        
        if self.confidence_threshold < 0.0 or self.confidence_threshold > 1.0:
            raise ValueError("confidence_thresholdは0.0から1.0の間である必要があります")
    
    def _validate_mode(self):
        """Validate mode parameter."""
        valid_modes = ["local", "bedrock", "hybrid"]
        if self.mode not in valid_modes:
            raise ValueError(f"modeは{valid_modes}のいずれかである必要があります")
    
    def _validate_retry_attempts(self):
        """Validate retry attempts parameter."""
        if not isinstance(self.retry_attempts, int):
            raise ValueError("retry_attemptsは整数である必要があります")
        
        if self.retry_attempts < 0 or self.retry_attempts > 10:
            raise ValueError("retry_attemptsは0から10の間である必要があります")
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert configuration to dictionary format.
        
        Returns:
            Dict[str, Any]: Configuration as dictionary
        """
        return {
            'knowledge_base_id': self.knowledge_base_id,
            'region': self.region,
            'similarity_top_k': self.similarity_top_k,
            'confidence_threshold': self.confidence_threshold,
            'mode': self.mode,
            'enable_fallback': self.enable_fallback,
            'retry_attempts': self.retry_attempts
        }
    
    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> 'KnowledgeBaseConfig':
        """
        Create configuration from dictionary.
        
        Args:
            config_dict: Configuration dictionary
            
        Returns:
            KnowledgeBaseConfig: Configuration instance
        """
        return cls(**config_dict)
    
    def is_bedrock_enabled(self) -> bool:
        """
        Check if Bedrock KnowledgeBase is enabled in current mode.
        
        Returns:
            bool: True if Bedrock is enabled
        """
        return self.mode in ["bedrock", "hybrid"]
    
    def is_local_enabled(self) -> bool:
        """
        Check if local search is enabled in current mode.
        
        Returns:
            bool: True if local search is enabled
        """
        return self.mode in ["local", "hybrid"]
    
    def get_aws_config(self) -> Dict[str, str]:
        """
        Get AWS-specific configuration parameters.
        
        Returns:
            Dict[str, str]: AWS configuration parameters
        """
        return {
            'region_name': self.region
        }


def create_default_config(knowledge_base_id: str, region: Optional[str] = None) -> KnowledgeBaseConfig:
    """
    Create a default configuration with minimal required parameters.
    
    Args:
        knowledge_base_id: The KnowledgeBase ID
        region: AWS region (defaults to us-east-1)
        
    Returns:
        KnowledgeBaseConfig: Default configuration instance
    """
    return KnowledgeBaseConfig(
        knowledge_base_id=knowledge_base_id,
        region=region or "us-east-1"
    )


def validate_config_dict(config_dict: Dict[str, Any]) -> bool:
    """
    Validate configuration dictionary without creating instance.
    
    Args:
        config_dict: Configuration dictionary to validate
        
    Returns:
        bool: True if configuration is valid
        
    Raises:
        ValueError: If configuration is invalid
    """
    try:
        KnowledgeBaseConfig.from_dict(config_dict)
        return True
    except (ValueError, TypeError) as e:
        logger.error(f"設定検証エラー: {e}")
        raise


def load_config_from_env() -> Optional[KnowledgeBaseConfig]:
    """
    Load KnowledgeBase configuration from environment variables.
    
    Environment variables:
        BEDROCK_KB_ID: KnowledgeBase ID (required)
        BEDROCK_KB_REGION: AWS region (default: us-east-1)
        BEDROCK_KB_MODE: Mode (default: hybrid)
        BEDROCK_KB_TOP_K: Top K results (default: 5)
        BEDROCK_KB_CONFIDENCE_THRESHOLD: Confidence threshold (default: 0.0)
        BEDROCK_KB_ENABLE_FALLBACK: Enable fallback (default: true)
        BEDROCK_KB_RETRY_ATTEMPTS: Retry attempts (default: 3)
    
    Returns:
        Optional[KnowledgeBaseConfig]: Configuration instance or None if KB_ID not set
    """
    kb_id = os.getenv('BEDROCK_KB_ID')
    if not kb_id:
        logger.info("BEDROCK_KB_ID環境変数が設定されていません。Bedrock KnowledgeBase機能は無効です。")
        return None
    
    try:
        # Get all environment variables with defaults
        region = os.getenv('BEDROCK_KB_REGION', 'us-east-1')
        mode = os.getenv('BEDROCK_KB_MODE', 'hybrid')
        top_k_str = os.getenv('BEDROCK_KB_TOP_K', '5')
        threshold_str = os.getenv('BEDROCK_KB_CONFIDENCE_THRESHOLD', '0.0')
        fallback_str = os.getenv('BEDROCK_KB_ENABLE_FALLBACK', 'true')
        retry_str = os.getenv('BEDROCK_KB_RETRY_ATTEMPTS', '3')
        
        # Debug logging
        logger.info(f"環境変数読み込み: KB_ID={kb_id[:10]}..., region={region}, mode={mode}")
        logger.info(f"パラメータ: top_k={top_k_str}, threshold={threshold_str}, fallback={fallback_str}, retry={retry_str}")
        
        # Parse numeric values with error handling
        try:
            top_k = int(top_k_str)
        except ValueError as e:
            logger.warning(f"BEDROCK_KB_TOP_K値が無効です: {top_k_str}. デフォルト値5を使用します")
            top_k = 5
        
        try:
            threshold = float(threshold_str)
        except ValueError as e:
            logger.warning(f"BEDROCK_KB_CONFIDENCE_THRESHOLD値が無効です: {threshold_str}. デフォルト値0.0を使用します")
            threshold = 0.0
        
        try:
            retry_attempts = int(retry_str)
        except ValueError as e:
            logger.warning(f"BEDROCK_KB_RETRY_ATTEMPTS値が無効です: {retry_str}. デフォルト値3を使用します")
            retry_attempts = 3
        
        # Parse boolean value
        enable_fallback = fallback_str.lower() in ('true', '1', 'yes', 'on')
        
        config = KnowledgeBaseConfig(
            knowledge_base_id=kb_id,
            region=region,
            mode=mode,
            similarity_top_k=top_k,
            confidence_threshold=threshold,
            enable_fallback=enable_fallback,
            retry_attempts=retry_attempts
        )
        
        logger.info(f"✅ 環境変数からKnowledgeBase設定を読み込みました: mode={config.mode}, region={config.region}")
        return config
        
    except (ValueError, TypeError) as e:
        logger.error(f"環境変数からの設定読み込みエラー: {e}")
        raise ValueError(f"KnowledgeBase設定の環境変数が正しくありません: {e}")


def get_default_config() -> Optional[KnowledgeBaseConfig]:
    """
    Get default configuration, prioritizing environment variables.
    
    Returns:
        Optional[KnowledgeBaseConfig]: Configuration instance or None if not available
    """
    return load_config_from_env()