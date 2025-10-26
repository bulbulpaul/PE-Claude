#!/usr/bin/env python3
"""
Error Handling and Fallback Tests for PE-GPT Bedrock KnowledgeBase Integration

This module tests the enhanced error handling, fallback functionality, and error scenarios
to ensure robust operation under various failure conditions.

@reference: PE-GPT: a New Paradigm for Power Electronics Design, by Fanfan Lin, Xinze Li, et al.
@code-author: Xinze Li, Fanfan Lin
@github: https://github.com/XinzeLee/PE-GPT
"""

import os
import sys
import unittest
import tempfile
from unittest.mock import Mock, patch, MagicMock
from typing import List, Dict, Any
import json

# Add core modules to path
sys.path.append('.')
sys.path.append('core')

# Import modules to test
from core.llm.error_handler import (
    EnhancedErrorHandler,
    ErrorCategory,
    ErrorSeverity,
    ErrorInfo,
    get_error_handler,
    handle_error,
    format_error_for_user
)
from core.knowledge.kb_config import KnowledgeBaseConfig
from core.llm.bedrock_kb_retriever import BedrockKnowledgeBaseRetriever
from core.llm.hybrid_retriever import HybridRetriever

# Mock AWS exceptions
from botocore.exceptions import ClientError, NoCredentialsError


class TestEnhancedErrorHandler(unittest.TestCase):
    """Test cases for EnhancedErrorHandler class"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.error_handler = EnhancedErrorHandler("test_handler")
    
    def test_aws_client_error_handling(self):
        """Test handling of AWS ClientError exceptions"""
        # Test ResourceNotFoundException
        error_response = {
            'Error': {
                'Code': 'ResourceNotFoundException',
                'Message': 'KnowledgeBase not found'
            }
        }
        client_error = ClientError(error_response, 'retrieve')
        
        error_info = self.error_handler.handle_error(client_error, "Test context")
        
        self.assertEqual(error_info.category, ErrorCategory.CONFIGURATION_ERROR)
        self.assertEqual(error_info.severity, ErrorSeverity.HIGH)
        self.assertFalse(error_info.is_retryable)
        self.assertIn("KnowledgeBase", error_info.user_message)
        self.assertIn("KnowledgeBase ID", error_info.suggested_actions[0])
    
    def test_access_denied_error_handling(self):
        """Test handling of AccessDeniedException"""
        error_response = {
            'Error': {
                'Code': 'AccessDeniedException',
                'Message': 'Access denied'
            }
        }
        client_error = ClientError(error_response, 'retrieve')
        
        error_info = self.error_handler.handle_error(client_error)
        
        self.assertEqual(error_info.category, ErrorCategory.AUTHENTICATION_ERROR)
        self.assertEqual(error_info.severity, ErrorSeverity.HIGH)
        self.assertFalse(error_info.is_retryable)
        self.assertIn("アクセス権限", error_info.user_message)
        self.assertIn("IAM", error_info.suggested_actions[0])
    
    def test_throttling_error_handling(self):
        """Test handling of ThrottlingException"""
        error_response = {
            'Error': {
                'Code': 'ThrottlingException',
                'Message': 'Rate exceeded'
            }
        }
        client_error = ClientError(error_response, 'retrieve')
        
        error_info = self.error_handler.handle_error(client_error)
        
        self.assertEqual(error_info.category, ErrorCategory.RATE_LIMIT_ERROR)
        self.assertEqual(error_info.severity, ErrorSeverity.MEDIUM)
        self.assertTrue(error_info.is_retryable)
        self.assertIsNotNone(error_info.retry_delay)
        self.assertIn("レート制限", error_info.user_message)
    
    def test_service_unavailable_error_handling(self):
        """Test handling of ServiceUnavailableException"""
        error_response = {
            'Error': {
                'Code': 'ServiceUnavailableException',
                'Message': 'Service temporarily unavailable'
            }
        }
        client_error = ClientError(error_response, 'retrieve')
        
        error_info = self.error_handler.handle_error(client_error)
        
        self.assertEqual(error_info.category, ErrorCategory.SERVICE_ERROR)
        self.assertEqual(error_info.severity, ErrorSeverity.HIGH)
        self.assertTrue(error_info.is_retryable)
        self.assertGreater(error_info.retry_delay, 0)
        self.assertIn("一時的に利用できません", error_info.user_message)
    
    def test_credentials_error_handling(self):
        """Test handling of NoCredentialsError"""
        credentials_error = NoCredentialsError()
        
        error_info = self.error_handler.handle_error(credentials_error)
        
        self.assertEqual(error_info.category, ErrorCategory.AUTHENTICATION_ERROR)
        self.assertEqual(error_info.severity, ErrorSeverity.CRITICAL)
        self.assertFalse(error_info.is_retryable)
        self.assertIn("認証情報", error_info.user_message)
        self.assertIn("AWS_ACCESS_KEY_ID", error_info.suggested_actions[0])
    
    def test_validation_error_handling(self):
        """Test handling of ValueError (validation errors)"""
        validation_error = ValueError("Invalid KnowledgeBase ID format")
        
        error_info = self.error_handler.handle_error(validation_error)
        
        self.assertEqual(error_info.category, ErrorCategory.CONFIGURATION_ERROR)
        self.assertEqual(error_info.severity, ErrorSeverity.MEDIUM)
        self.assertFalse(error_info.is_retryable)
        self.assertIn("設定パラメータ", error_info.user_message)
    
    def test_network_error_handling(self):
        """Test handling of network errors"""
        network_error = ConnectionError("Connection failed")
        
        error_info = self.error_handler.handle_error(network_error)
        
        self.assertEqual(error_info.category, ErrorCategory.NETWORK_ERROR)
        self.assertEqual(error_info.severity, ErrorSeverity.MEDIUM)
        self.assertTrue(error_info.is_retryable)
        self.assertIn("ネットワーク", error_info.user_message)
    
    def test_file_not_found_error_handling(self):
        """Test handling of FileNotFoundError"""
        file_error = FileNotFoundError("File not found: /path/to/file")
        
        error_info = self.error_handler.handle_error(file_error)
        
        self.assertEqual(error_info.category, ErrorCategory.LOCAL_ERROR)
        self.assertEqual(error_info.severity, ErrorSeverity.MEDIUM)
        self.assertFalse(error_info.is_retryable)
        self.assertIn("ローカルファイル", error_info.user_message)
    
    def test_unknown_error_handling(self):
        """Test handling of unknown errors"""
        unknown_error = RuntimeError("Unknown runtime error")
        
        error_info = self.error_handler.handle_error(unknown_error)
        
        self.assertEqual(error_info.category, ErrorCategory.UNKNOWN_ERROR)
        self.assertEqual(error_info.severity, ErrorSeverity.MEDIUM)
        self.assertTrue(error_info.is_retryable)
        self.assertIn("予期しない", error_info.user_message)
    
    def test_retry_logic(self):
        """Test retry decision logic"""
        # Retryable error
        retryable_error_info = ErrorInfo(
            category=ErrorCategory.RATE_LIMIT_ERROR,
            severity=ErrorSeverity.MEDIUM,
            message="Rate limit",
            user_message="Rate limited",
            suggested_actions=["Wait"],
            is_retryable=True,
            retry_delay=1.0
        )
        
        # Should retry on first attempt
        should_retry, delay = self.error_handler.should_retry(retryable_error_info, 0, 3)
        self.assertTrue(should_retry)
        self.assertEqual(delay, 1.0)
        
        # Should retry on second attempt with exponential backoff
        should_retry, delay = self.error_handler.should_retry(retryable_error_info, 1, 3)
        self.assertTrue(should_retry)
        self.assertEqual(delay, 2.0)
        
        # Should not retry after max attempts
        should_retry, delay = self.error_handler.should_retry(retryable_error_info, 3, 3)
        self.assertFalse(should_retry)
        self.assertEqual(delay, 0.0)
        
        # Non-retryable error
        non_retryable_error_info = ErrorInfo(
            category=ErrorCategory.CONFIGURATION_ERROR,
            severity=ErrorSeverity.HIGH,
            message="Config error",
            user_message="Configuration error",
            suggested_actions=["Fix config"],
            is_retryable=False
        )
        
        should_retry, delay = self.error_handler.should_retry(non_retryable_error_info, 0, 3)
        self.assertFalse(should_retry)
        self.assertEqual(delay, 0.0)
    
    def test_error_statistics(self):
        """Test error statistics tracking"""
        # Generate some errors
        errors = [
            ClientError({'Error': {'Code': 'ThrottlingException', 'Message': 'Rate exceeded'}}, 'retrieve'),
            NoCredentialsError(),
            ValueError("Invalid config"),
            ClientError({'Error': {'Code': 'ThrottlingException', 'Message': 'Rate exceeded'}}, 'retrieve')
        ]
        
        for error in errors:
            self.error_handler.handle_error(error)
        
        stats = self.error_handler.get_error_statistics()
        
        self.assertEqual(stats['total_errors'], 4)
        self.assertEqual(stats['error_counts']['rate_limit_error'], 2)
        self.assertEqual(stats['error_counts']['authentication_error'], 1)
        self.assertEqual(stats['error_counts']['configuration_error'], 1)
    
    def test_user_message_formatting(self):
        """Test user message formatting"""
        error_info = ErrorInfo(
            category=ErrorCategory.CONFIGURATION_ERROR,
            severity=ErrorSeverity.HIGH,
            message="Test error",
            user_message="テストエラーが発生しました",
            suggested_actions=["アクション1", "アクション2"],
            is_retryable=False,
            error_code="TEST001"
        )
        
        # With actions
        message_with_actions = self.error_handler.format_user_message(error_info, include_actions=True)
        self.assertIn("❌ テストエラーが発生しました", message_with_actions)
        self.assertIn("(エラーコード: TEST001)", message_with_actions)
        self.assertIn("🔧 対処方法:", message_with_actions)
        self.assertIn("1. アクション1", message_with_actions)
        self.assertIn("2. アクション2", message_with_actions)
        
        # Without actions
        message_without_actions = self.error_handler.format_user_message(error_info, include_actions=False)
        self.assertIn("❌ テストエラーが発生しました", message_without_actions)
        self.assertIn("(エラーコード: TEST001)", message_without_actions)
        self.assertNotIn("🔧 対処方法:", message_without_actions)


class TestBedrockRetrieverErrorHandling(unittest.TestCase):
    """Test error handling in BedrockKnowledgeBaseRetriever"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.config = KnowledgeBaseConfig(
            knowledge_base_id="TEST123456",
            region="us-east-1",
            mode="bedrock",
            retry_attempts=2
        )
    
    @patch('core.llm.bedrock_kb_retriever.boto3.client')
    def test_retriever_with_resource_not_found(self, mock_boto_client):
        """Test retriever behavior with ResourceNotFoundException"""
        # Mock client that raises ResourceNotFoundException
        mock_client = Mock()
        error_response = {
            'Error': {
                'Code': 'ResourceNotFoundException',
                'Message': 'KnowledgeBase not found'
            }
        }
        mock_client.retrieve.side_effect = ClientError(error_response, 'retrieve')
        mock_boto_client.return_value = mock_client
        
        retriever = BedrockKnowledgeBaseRetriever(self.config)
        results = retriever.retrieve("test query")
        
        # Should return empty results
        self.assertEqual(results, [])
        
        # Should have attempted the call
        mock_client.retrieve.assert_called()
    
    @patch('core.llm.bedrock_kb_retriever.boto3.client')
    @patch('core.llm.bedrock_kb_retriever.time.sleep')
    def test_retriever_with_throttling_and_retry(self, mock_sleep, mock_boto_client):
        """Test retriever retry behavior with ThrottlingException"""
        mock_client = Mock()
        error_response = {
            'Error': {
                'Code': 'ThrottlingException',
                'Message': 'Rate exceeded'
            }
        }
        
        # First two calls fail, third succeeds
        mock_client.retrieve.side_effect = [
            ClientError(error_response, 'retrieve'),
            ClientError(error_response, 'retrieve'),
            {'retrievalResults': []}
        ]
        mock_boto_client.return_value = mock_client
        
        retriever = BedrockKnowledgeBaseRetriever(self.config)
        results = retriever.retrieve("test query")
        
        # Should have made 3 attempts
        self.assertEqual(mock_client.retrieve.call_count, 3)
        
        # Should have slept between retries
        self.assertEqual(mock_sleep.call_count, 2)
        
        # Should return empty results from successful third call
        self.assertEqual(results, [])
    
    @patch('core.llm.bedrock_kb_retriever.boto3.client')
    def test_retriever_with_access_denied(self, mock_boto_client):
        """Test retriever behavior with AccessDeniedException"""
        mock_client = Mock()
        error_response = {
            'Error': {
                'Code': 'AccessDeniedException',
                'Message': 'Access denied'
            }
        }
        mock_client.retrieve.side_effect = ClientError(error_response, 'retrieve')
        mock_boto_client.return_value = mock_client
        
        retriever = BedrockKnowledgeBaseRetriever(self.config)
        results = retriever.retrieve("test query")
        
        # Should return empty results (no retry for access denied)
        self.assertEqual(results, [])
        
        # Should have attempted only once (not retryable)
        self.assertEqual(mock_client.retrieve.call_count, 1)
    
    def test_retriever_with_invalid_config(self):
        """Test retriever initialization with invalid configuration"""
        invalid_config = KnowledgeBaseConfig(
            knowledge_base_id="TEST123456",
            region="us-east-1",
            mode="local"  # Bedrock not enabled
        )
        
        with self.assertRaises(ValueError) as context:
            BedrockKnowledgeBaseRetriever(invalid_config)
        
        self.assertIn("Bedrockモードが有効になっていません", str(context.exception))


class TestHybridRetrieverFallback(unittest.TestCase):
    """Test fallback functionality in HybridRetriever"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.config = KnowledgeBaseConfig(
            knowledge_base_id="TEST123456",
            region="us-east-1",
            mode="hybrid",
            enable_fallback=True
        )
        
        # Mock local retriever
        self.mock_local_retriever = Mock()
        self.mock_local_retriever.retrieve.return_value = [
            Mock(node=Mock(text="Local result", metadata={'source': 'local'}), score=0.8)
        ]
        
        # Mock bedrock retriever
        self.mock_bedrock_retriever = Mock()
        self.mock_bedrock_retriever.retrieve.return_value = [
            Mock(node=Mock(text="Bedrock result", metadata={'source': 'bedrock'}), score=0.9)
        ]
    
    def test_bedrock_mode_fallback_to_local(self):
        """Test fallback from Bedrock to local when Bedrock fails"""
        # Make bedrock retriever fail
        self.mock_bedrock_retriever.retrieve.side_effect = Exception("Bedrock API error")
        
        retriever = HybridRetriever(
            local_retriever=self.mock_local_retriever,
            bedrock_retriever=self.mock_bedrock_retriever,
            config=self.config,
            mode="bedrock"
        )
        
        results = retriever.retrieve("test query")
        
        # Should fallback to local results
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].node.metadata['source'], 'local')
    
    def test_hybrid_mode_partial_fallback(self):
        """Test partial fallback in hybrid mode when one source fails"""
        # Make bedrock retriever fail
        self.mock_bedrock_retriever.retrieve.side_effect = Exception("Bedrock API error")
        
        retriever = HybridRetriever(
            local_retriever=self.mock_local_retriever,
            bedrock_retriever=self.mock_bedrock_retriever,
            config=self.config,
            mode="hybrid"
        )
        
        results = retriever.retrieve("test query")
        
        # Should return local results only
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].node.metadata['source'], 'local')
    
    def test_fallback_disabled(self):
        """Test behavior when fallback is disabled"""
        config_no_fallback = KnowledgeBaseConfig(
            knowledge_base_id="TEST123456",
            region="us-east-1",
            mode="bedrock",
            enable_fallback=False
        )
        
        # Make bedrock retriever fail
        self.mock_bedrock_retriever.retrieve.side_effect = Exception("Bedrock API error")
        
        retriever = HybridRetriever(
            local_retriever=self.mock_local_retriever,
            bedrock_retriever=self.mock_bedrock_retriever,
            config=config_no_fallback,
            mode="bedrock"
        )
        
        results = retriever.retrieve("test query")
        
        # Should return empty results (no fallback)
        self.assertEqual(results, [])
    
    def test_fallback_when_both_sources_fail(self):
        """Test behavior when both sources fail"""
        # Make both retrievers fail
        self.mock_local_retriever.retrieve.side_effect = Exception("Local error")
        self.mock_bedrock_retriever.retrieve.side_effect = Exception("Bedrock error")
        
        retriever = HybridRetriever(
            local_retriever=self.mock_local_retriever,
            bedrock_retriever=self.mock_bedrock_retriever,
            config=self.config,
            mode="hybrid"
        )
        
        results = retriever.retrieve("test query")
        
        # Should return empty results
        self.assertEqual(results, [])
    
    def test_error_categorization_and_fallback_strategy(self):
        """Test error categorization and appropriate fallback strategy"""
        # Test with different error types
        error_scenarios = [
            (ClientError({'Error': {'Code': 'AccessDeniedException', 'Message': 'Access denied'}}, 'retrieve'), "local_fallback"),
            (ClientError({'Error': {'Code': 'ThrottlingException', 'Message': 'Rate exceeded'}}, 'retrieve'), "retry_with_delay"),
            (ConnectionError("Network error"), "local_fallback"),
            (ValueError("Config error"), "local_fallback")
        ]
        
        for error, expected_strategy in error_scenarios:
            with self.subTest(error=error):
                retriever = HybridRetriever(
                    local_retriever=self.mock_local_retriever,
                    bedrock_retriever=self.mock_bedrock_retriever,
                    config=self.config,
                    mode="bedrock"
                )
                
                # Test error categorization
                error_category = retriever._categorize_retrieval_error(error)
                self.assertIsNotNone(error_category)
                
                # Test fallback strategy determination
                strategy = retriever._determine_fallback_strategy(error_category)
                self.assertEqual(strategy, expected_strategy)


class TestErrorHandlingIntegration(unittest.TestCase):
    """Integration tests for error handling across components"""
    
    def test_global_error_handler_singleton(self):
        """Test that global error handler is a singleton"""
        handler1 = get_error_handler()
        handler2 = get_error_handler()
        
        self.assertIs(handler1, handler2)
    
    def test_convenience_functions(self):
        """Test convenience functions for error handling"""
        test_error = ValueError("Test validation error")
        
        # Test handle_error function
        error_info = handle_error(test_error, "Test context")
        self.assertIsInstance(error_info, ErrorInfo)
        self.assertEqual(error_info.category, ErrorCategory.CONFIGURATION_ERROR)
        
        # Test format_error_for_user function
        user_message = format_error_for_user(test_error, "Test context", include_actions=True)
        self.assertIn("❌", user_message)
        self.assertIn("設定パラメータ", user_message)
        self.assertIn("🔧 対処方法:", user_message)
    
    def test_error_logging_levels(self):
        """Test that errors are logged at appropriate levels"""
        with patch('logging.Logger.critical') as mock_critical, \
             patch('logging.Logger.error') as mock_error, \
             patch('logging.Logger.warning') as mock_warning, \
             patch('logging.Logger.info') as mock_info:
            
            handler = EnhancedErrorHandler("test_logger")
            
            # Critical error
            critical_error = NoCredentialsError()
            handler.handle_error(critical_error)
            mock_critical.assert_called()
            
            # High severity error
            high_error = ClientError({'Error': {'Code': 'AccessDeniedException', 'Message': 'Access denied'}}, 'retrieve')
            handler.handle_error(high_error)
            mock_error.assert_called()
            
            # Medium severity error
            medium_error = ValueError("Config error")
            handler.handle_error(medium_error)
            mock_warning.assert_called()


def run_error_handling_tests():
    """Run all error handling tests"""
    print("🧪 Running Error Handling and Fallback Tests")
    print("=" * 60)
    
    # Create test suite
    test_suite = unittest.TestSuite()
    
    # Add test cases
    test_suite.addTest(unittest.makeSuite(TestEnhancedErrorHandler))
    test_suite.addTest(unittest.makeSuite(TestBedrockRetrieverErrorHandling))
    test_suite.addTest(unittest.makeSuite(TestHybridRetrieverFallback))
    test_suite.addTest(unittest.makeSuite(TestErrorHandlingIntegration))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    
    # Print summary
    print("\n" + "=" * 60)
    print("🏁 Error Handling Test Summary")
    print("=" * 60)
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Skipped: {len(result.skipped) if hasattr(result, 'skipped') else 0}")
    
    if result.failures:
        print("\n❌ FAILURES:")
        for test, traceback in result.failures:
            print(f"  - {test}")
            print(f"    {traceback.split('AssertionError:')[-1].strip() if 'AssertionError:' in traceback else 'See details above'}")
    
    if result.errors:
        print("\n❌ ERRORS:")
        for test, traceback in result.errors:
            print(f"  - {test}")
            print(f"    {traceback.split('Exception:')[-1].strip() if 'Exception:' in traceback else 'See details above'}")
    
    success = len(result.failures) == 0 and len(result.errors) == 0
    
    # Print test coverage summary
    print(f"\n📊 Test Coverage Summary:")
    print(f"  ✅ Error categorization and analysis")
    print(f"  ✅ AWS error handling (ResourceNotFound, AccessDenied, Throttling, etc.)")
    print(f"  ✅ Network and authentication error handling")
    print(f"  ✅ Retry logic and exponential backoff")
    print(f"  ✅ Fallback mechanisms (Bedrock → Local, Hybrid partial)")
    print(f"  ✅ Error statistics and monitoring")
    print(f"  ✅ User-friendly error message formatting")
    print(f"  ✅ Integration with existing components")
    
    print(f"\n🎯 Overall Result: {'✅ ALL TESTS PASSED' if success else '❌ SOME TESTS FAILED'}")
    
    return success


if __name__ == "__main__":
    success = run_error_handling_tests()
    sys.exit(0 if success else 1)