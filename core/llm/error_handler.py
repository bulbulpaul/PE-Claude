"""
Enhanced Error Handling Module for Bedrock KnowledgeBase Integration

This module provides comprehensive error handling, logging, and user-friendly error messages
for the PE-GPT Bedrock KnowledgeBase integration.

@reference: PE-GPT: a New Paradigm for Power Electronics Design, by Fanfan Lin, Xinze Li, et al.
@code-author: Xinze Li, Fanfan Lin
@github: https://github.com/XinzeLee/PE-GPT
"""

import logging
import time
from typing import Dict, Any, Optional, List, Tuple
from enum import Enum
from dataclasses import dataclass
from botocore.exceptions import ClientError, NoCredentialsError, BotoCoreError


class ErrorCategory(Enum):
    """Error categories for better error handling and monitoring."""
    CONFIGURATION_ERROR = "configuration_error"
    AUTHENTICATION_ERROR = "authentication_error"
    RATE_LIMIT_ERROR = "rate_limit_error"
    SERVICE_ERROR = "service_error"
    NETWORK_ERROR = "network_error"
    API_ERROR = "api_error"
    LOCAL_ERROR = "local_error"
    UNKNOWN_ERROR = "unknown_error"


class ErrorSeverity(Enum):
    """Error severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class ErrorInfo:
    """Structured error information."""
    category: ErrorCategory
    severity: ErrorSeverity
    message: str
    user_message: str
    suggested_actions: List[str]
    is_retryable: bool
    retry_delay: Optional[float] = None
    error_code: Optional[str] = None
    original_error: Optional[Exception] = None


class EnhancedErrorHandler:
    """
    Enhanced error handler for Bedrock KnowledgeBase integration.
    
    Provides comprehensive error categorization, user-friendly messages,
    and actionable guidance for error resolution.
    """
    
    def __init__(self, logger_name: str = "bedrock_kb_integration"):
        """
        Initialize enhanced error handler.
        
        Args:
            logger_name: Name for the logger instance
        """
        self.logger = logging.getLogger(logger_name)
        self.error_counts = {}
        self.last_error_time = {}
        
        # Configure logger if not already configured
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)
    
    def handle_error(self, error: Exception, context: str = "") -> ErrorInfo:
        """
        Handle and categorize an error with comprehensive information.
        
        Args:
            error: The exception that occurred
            context: Additional context about where the error occurred
            
        Returns:
            ErrorInfo: Structured error information
        """
        error_info = self._analyze_error(error)
        
        # Log the error with context
        self._log_error(error_info, context)
        
        # Update error statistics
        self._update_error_stats(error_info)
        
        return error_info
    
    def _analyze_error(self, error: Exception) -> ErrorInfo:
        """
        Analyze and categorize an error.
        
        Args:
            error: The exception to analyze
            
        Returns:
            ErrorInfo: Structured error information
        """
        if isinstance(error, ClientError):
            return self._analyze_aws_error(error)
        elif isinstance(error, NoCredentialsError):
            return self._analyze_credentials_error(error)
        elif isinstance(error, (ConnectionError, TimeoutError)):
            return self._analyze_network_error(error)
        elif isinstance(error, ValueError):
            return self._analyze_validation_error(error)
        elif isinstance(error, FileNotFoundError):
            return self._analyze_file_error(error)
        else:
            return self._analyze_unknown_error(error)
    
    def _analyze_aws_error(self, error: ClientError) -> ErrorInfo:
        """Analyze AWS ClientError exceptions."""
        error_code = error.response.get('Error', {}).get('Code', 'Unknown')
        error_message = error.response.get('Error', {}).get('Message', str(error))
        
        error_mappings = {
            'ResourceNotFoundException': ErrorInfo(
                category=ErrorCategory.CONFIGURATION_ERROR,
                severity=ErrorSeverity.HIGH,
                message=f"KnowledgeBase not found: {error_message}",
                user_message="指定されたKnowledgeBaseが見つかりません。",
                suggested_actions=[
                    "KnowledgeBase IDが正しいか確認してください",
                    "指定されたリージョンでKnowledgeBaseが利用可能か確認してください",
                    "BedrockコンソールでKnowledgeBaseの存在を確認してください"
                ],
                is_retryable=False,
                error_code=error_code,
                original_error=error
            ),
            'AccessDeniedException': ErrorInfo(
                category=ErrorCategory.AUTHENTICATION_ERROR,
                severity=ErrorSeverity.HIGH,
                message=f"Access denied: {error_message}",
                user_message="KnowledgeBaseへのアクセス権限がありません。",
                suggested_actions=[
                    "IAMポリシーで 'bedrock:Retrieve' アクションが許可されているか確認してください",
                    "IAMロールまたはユーザーにBedrockKnowledgeBaseへのアクセス権限を付与してください",
                    "AWS認証情報が正しく設定されているか確認してください"
                ],
                is_retryable=False,
                error_code=error_code,
                original_error=error
            ),
            'ThrottlingException': ErrorInfo(
                category=ErrorCategory.RATE_LIMIT_ERROR,
                severity=ErrorSeverity.MEDIUM,
                message=f"Rate limit exceeded: {error_message}",
                user_message="API呼び出しがレート制限されました。",
                suggested_actions=[
                    "リクエスト頻度を下げてください",
                    "指数バックオフを使用して再試行してください",
                    "同時リクエスト数を制限してください"
                ],
                is_retryable=True,
                retry_delay=2.0,
                error_code=error_code,
                original_error=error
            ),
            'ValidationException': ErrorInfo(
                category=ErrorCategory.CONFIGURATION_ERROR,
                severity=ErrorSeverity.MEDIUM,
                message=f"Validation error: {error_message}",
                user_message="リクエストパラメータが無効です。",
                suggested_actions=[
                    "クエリ文字列が空でないか確認してください",
                    "similarity_top_kパラメータが有効な範囲内か確認してください",
                    "KnowledgeBase設定パラメータを確認してください"
                ],
                is_retryable=False,
                error_code=error_code,
                original_error=error
            ),
            'ServiceUnavailableException': ErrorInfo(
                category=ErrorCategory.SERVICE_ERROR,
                severity=ErrorSeverity.HIGH,
                message=f"Service unavailable: {error_message}",
                user_message="Bedrock KnowledgeBaseサービスが一時的に利用できません。",
                suggested_actions=[
                    "しばらく時間を置いてから再試行してください",
                    "AWS Status Pageでサービス状況を確認してください",
                    "別のリージョンでの利用を検討してください"
                ],
                is_retryable=True,
                retry_delay=5.0,
                error_code=error_code,
                original_error=error
            ),
            'InternalServerException': ErrorInfo(
                category=ErrorCategory.SERVICE_ERROR,
                severity=ErrorSeverity.HIGH,
                message=f"Internal server error: {error_message}",
                user_message="Bedrock内部サーバーエラーが発生しました。",
                suggested_actions=[
                    "しばらく時間を置いてから再試行してください",
                    "問題が続く場合はAWSサポートにお問い合わせください",
                    "エラーの詳細をログで確認してください"
                ],
                is_retryable=True,
                retry_delay=10.0,
                error_code=error_code,
                original_error=error
            )
        }
        
        return error_mappings.get(error_code, ErrorInfo(
            category=ErrorCategory.API_ERROR,
            severity=ErrorSeverity.MEDIUM,
            message=f"AWS API error [{error_code}]: {error_message}",
            user_message=f"AWS APIエラーが発生しました: {error_code}",
            suggested_actions=[
                "エラーコードの詳細をAWSドキュメントで確認してください",
                "設定パラメータを確認してください",
                "問題が続く場合はAWSサポートにお問い合わせください"
            ],
            is_retryable=True,
            retry_delay=1.0,
            error_code=error_code,
            original_error=error
        ))
    
    def _analyze_credentials_error(self, error: NoCredentialsError) -> ErrorInfo:
        """Analyze AWS credentials errors."""
        return ErrorInfo(
            category=ErrorCategory.AUTHENTICATION_ERROR,
            severity=ErrorSeverity.CRITICAL,
            message="AWS credentials not found",
            user_message="AWS認証情報が見つかりません。",
            suggested_actions=[
                "環境変数でAWS_ACCESS_KEY_IDとAWS_SECRET_ACCESS_KEYを設定してください",
                "AWS CLIで 'aws configure' を実行して認証情報を設定してください",
                "IAMロールを使用している場合は、適切にアタッチされているか確認してください",
                "AWS認証情報ファイル (~/.aws/credentials) が存在するか確認してください"
            ],
            is_retryable=False,
            original_error=error
        )
    
    def _analyze_network_error(self, error: Exception) -> ErrorInfo:
        """Analyze network-related errors."""
        return ErrorInfo(
            category=ErrorCategory.NETWORK_ERROR,
            severity=ErrorSeverity.MEDIUM,
            message=f"Network error: {str(error)}",
            user_message="ネットワーク接続エラーが発生しました。",
            suggested_actions=[
                "インターネット接続を確認してください",
                "ファイアウォール設定を確認してください",
                "プロキシ設定が正しいか確認してください",
                "しばらく時間を置いてから再試行してください"
            ],
            is_retryable=True,
            retry_delay=3.0,
            original_error=error
        )
    
    def _analyze_validation_error(self, error: ValueError) -> ErrorInfo:
        """Analyze validation errors."""
        error_message = str(error)
        
        return ErrorInfo(
            category=ErrorCategory.CONFIGURATION_ERROR,
            severity=ErrorSeverity.MEDIUM,
            message=f"Validation error: {error_message}",
            user_message="設定パラメータが無効です。",
            suggested_actions=[
                "KnowledgeBase IDが正しい形式か確認してください",
                "リージョン名が正しいか確認してください",
                "数値パラメータが有効な範囲内か確認してください",
                "必須パラメータが設定されているか確認してください"
            ],
            is_retryable=False,
            original_error=error
        )
    
    def _analyze_file_error(self, error: FileNotFoundError) -> ErrorInfo:
        """Analyze file-related errors."""
        return ErrorInfo(
            category=ErrorCategory.LOCAL_ERROR,
            severity=ErrorSeverity.MEDIUM,
            message=f"File not found: {str(error)}",
            user_message="ローカルファイルが見つかりません。",
            suggested_actions=[
                "指定されたファイルパスが正しいか確認してください",
                "ファイルが存在するか確認してください",
                "ファイルアクセス権限を確認してください",
                "相対パスではなく絶対パスを使用してみてください"
            ],
            is_retryable=False,
            original_error=error
        )
    
    def _analyze_unknown_error(self, error: Exception) -> ErrorInfo:
        """Analyze unknown errors."""
        return ErrorInfo(
            category=ErrorCategory.UNKNOWN_ERROR,
            severity=ErrorSeverity.MEDIUM,
            message=f"Unknown error: {str(error)}",
            user_message="予期しないエラーが発生しました。",
            suggested_actions=[
                "エラーメッセージの詳細を確認してください",
                "設定パラメータを確認してください",
                "ログファイルで詳細情報を確認してください",
                "問題が続く場合はサポートにお問い合わせください"
            ],
            is_retryable=True,
            retry_delay=1.0,
            original_error=error
        )
    
    def _log_error(self, error_info: ErrorInfo, context: str):
        """
        Log error information with appropriate level.
        
        Args:
            error_info: Structured error information
            context: Additional context about the error
        """
        log_message = f"[{error_info.category.value}] {error_info.message}"
        if context:
            log_message += f" (Context: {context})"
        
        if error_info.severity == ErrorSeverity.CRITICAL:
            self.logger.critical(log_message)
        elif error_info.severity == ErrorSeverity.HIGH:
            self.logger.error(log_message)
        elif error_info.severity == ErrorSeverity.MEDIUM:
            self.logger.warning(log_message)
        else:
            self.logger.info(log_message)
        
        # Log suggested actions for high severity errors
        if error_info.severity in [ErrorSeverity.HIGH, ErrorSeverity.CRITICAL]:
            self.logger.info(f"Suggested actions: {'; '.join(error_info.suggested_actions)}")
    
    def _update_error_stats(self, error_info: ErrorInfo):
        """
        Update error statistics for monitoring.
        
        Args:
            error_info: Structured error information
        """
        category = error_info.category.value
        
        # Update error counts
        if category not in self.error_counts:
            self.error_counts[category] = 0
        self.error_counts[category] += 1
        
        # Update last error time
        self.last_error_time[category] = time.time()
        
        # Log statistics periodically
        total_errors = sum(self.error_counts.values())
        if total_errors % 10 == 0:  # Log every 10 errors
            self.logger.info(f"Error statistics: {dict(self.error_counts)}")
    
    def get_error_statistics(self) -> Dict[str, Any]:
        """
        Get error statistics for monitoring.
        
        Returns:
            Dict[str, Any]: Error statistics
        """
        return {
            'error_counts': dict(self.error_counts),
            'last_error_times': dict(self.last_error_time),
            'total_errors': sum(self.error_counts.values())
        }
    
    def should_retry(self, error_info: ErrorInfo, attempt: int, max_attempts: int) -> Tuple[bool, float]:
        """
        Determine if an error should be retried and calculate delay.
        
        Args:
            error_info: Structured error information
            attempt: Current attempt number (0-based)
            max_attempts: Maximum number of attempts
            
        Returns:
            Tuple[bool, float]: (should_retry, delay_seconds)
        """
        if not error_info.is_retryable or attempt >= max_attempts:
            return False, 0.0
        
        # Calculate exponential backoff delay
        base_delay = error_info.retry_delay or 1.0
        delay = min(base_delay * (2 ** attempt), 60.0)  # Cap at 60 seconds
        
        return True, delay
    
    def format_user_message(self, error_info: ErrorInfo, include_actions: bool = True) -> str:
        """
        Format a user-friendly error message.
        
        Args:
            error_info: Structured error information
            include_actions: Whether to include suggested actions
            
        Returns:
            str: Formatted user message
        """
        message = f"❌ {error_info.user_message}"
        
        if error_info.error_code:
            message += f" (エラーコード: {error_info.error_code})"
        
        if include_actions and error_info.suggested_actions:
            message += "\n\n🔧 対処方法:\n"
            for i, action in enumerate(error_info.suggested_actions, 1):
                message += f"{i}. {action}\n"
        
        return message.strip()


# Global error handler instance
_global_error_handler = None


def get_error_handler() -> EnhancedErrorHandler:
    """
    Get the global error handler instance.
    
    Returns:
        EnhancedErrorHandler: Global error handler instance
    """
    global _global_error_handler
    if _global_error_handler is None:
        _global_error_handler = EnhancedErrorHandler()
    return _global_error_handler


def handle_error(error: Exception, context: str = "") -> ErrorInfo:
    """
    Convenience function to handle errors using the global error handler.
    
    Args:
        error: The exception that occurred
        context: Additional context about the error
        
    Returns:
        ErrorInfo: Structured error information
    """
    return get_error_handler().handle_error(error, context)


def format_error_for_user(error: Exception, context: str = "", include_actions: bool = True) -> str:
    """
    Convenience function to format an error for user display.
    
    Args:
        error: The exception that occurred
        context: Additional context about the error
        include_actions: Whether to include suggested actions
        
    Returns:
        str: Formatted user-friendly error message
    """
    error_info = handle_error(error, context)
    return get_error_handler().format_user_message(error_info, include_actions)