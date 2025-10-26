#!/usr/bin/env python3
"""
Unit tests for KnowledgeBase components
Tests KnowledgeBaseConfig and BedrockKnowledgeBaseRetriever classes
"""

import os
import sys
import unittest
from unittest.mock import Mock, patch, MagicMock
import json
from typing import Dict, List, Any

# Add core modules to path
sys.path.append('.')
sys.path.append('core')

# Import the modules to test
from core.knowledge.kb_config import (
    KnowledgeBaseConfig,
    create_default_config,
    validate_config_dict
)
from core.llm.bedrock_kb_retriever import (
    BedrockKnowledgeBaseRetriever,
    create_bedrock_retriever
)


class TestKnowledgeBaseConfig(unittest.TestCase):
    """Test cases for KnowledgeBaseConfig class"""
    
    def test_valid_config_creation(self):
        """Test creating a valid configuration"""
        config = KnowledgeBaseConfig(
            knowledge_base_id="ABCDEFGHIJ",
            region="us-east-1"
        )
        
        self.assertEqual(config.knowledge_base_id, "ABCDEFGHIJ")
        self.assertEqual(config.region, "us-east-1")
        self.assertEqual(config.similarity_top_k, 5)
        self.assertEqual(config.confidence_threshold, 0.0)
        self.assertEqual(config.mode, "hybrid")
        self.assertTrue(config.enable_fallback)
        self.assertEqual(config.retry_attempts, 3)
    
    def test_invalid_knowledge_base_id(self):
        """Test validation of KnowledgeBase ID"""
        # Empty ID
        with self.assertRaises(ValueError) as context:
            KnowledgeBaseConfig(knowledge_base_id="")
        self.assertIn("KnowledgeBase IDは必須です", str(context.exception))
        
        # Non-string ID
        with self.assertRaises(ValueError) as context:
            KnowledgeBaseConfig(knowledge_base_id=123)
        self.assertIn("文字列である必要があります", str(context.exception))
    
    def test_invalid_region(self):
        """Test validation of AWS region"""
        # Empty region
        with self.assertRaises(ValueError) as context:
            KnowledgeBaseConfig(
                knowledge_base_id="ABCDEFGHIJ",
                region=""
            )
        self.assertIn("リージョンは必須です", str(context.exception))
        
        # Invalid region format
        with self.assertRaises(ValueError) as context:
            KnowledgeBaseConfig(
                knowledge_base_id="ABCDEFGHIJ",
                region="invalid-region"
            )
        self.assertIn("リージョン形式が正しくありません", str(context.exception))
        
        # Non-string region
        with self.assertRaises(ValueError) as context:
            KnowledgeBaseConfig(
                knowledge_base_id="ABCDEFGHIJ",
                region=123
            )
        self.assertIn("単一の文字列で指定してください", str(context.exception))
    
    def test_invalid_similarity_top_k(self):
        """Test validation of similarity_top_k parameter"""
        # Non-integer value
        with self.assertRaises(ValueError) as context:
            KnowledgeBaseConfig(
                knowledge_base_id="ABCDEFGHIJ",
                similarity_top_k="5"
            )
        self.assertIn("整数である必要があります", str(context.exception))
        
        # Out of range values
        with self.assertRaises(ValueError) as context:
            KnowledgeBaseConfig(
                knowledge_base_id="ABCDEFGHIJ",
                similarity_top_k=0
            )
        self.assertIn("1から100の間である必要があります", str(context.exception))
        
        with self.assertRaises(ValueError) as context:
            KnowledgeBaseConfig(
                knowledge_base_id="ABCDEFGHIJ",
                similarity_top_k=101
            )
        self.assertIn("1から100の間である必要があります", str(context.exception))
    
    def test_invalid_confidence_threshold(self):
        """Test validation of confidence_threshold parameter"""
        # Non-numeric value
        with self.assertRaises(ValueError) as context:
            KnowledgeBaseConfig(
                knowledge_base_id="ABCDEFGHIJ",
                confidence_threshold="0.5"
            )
        self.assertIn("数値である必要があります", str(context.exception))
        
        # Out of range values
        with self.assertRaises(ValueError) as context:
            KnowledgeBaseConfig(
                knowledge_base_id="ABCDEFGHIJ",
                confidence_threshold=-0.1
            )
        self.assertIn("0.0から1.0の間である必要があります", str(context.exception))
        
        with self.assertRaises(ValueError) as context:
            KnowledgeBaseConfig(
                knowledge_base_id="ABCDEFGHIJ",
                confidence_threshold=1.1
            )
        self.assertIn("0.0から1.0の間である必要があります", str(context.exception))
    
    def test_invalid_mode(self):
        """Test validation of mode parameter"""
        with self.assertRaises(ValueError) as context:
            KnowledgeBaseConfig(
                knowledge_base_id="ABCDEFGHIJ",
                mode="invalid"
            )
        self.assertIn("のいずれかである必要があります", str(context.exception))
    
    def test_invalid_retry_attempts(self):
        """Test validation of retry_attempts parameter"""
        # Non-integer value
        with self.assertRaises(ValueError) as context:
            KnowledgeBaseConfig(
                knowledge_base_id="ABCDEFGHIJ",
                retry_attempts="3"
            )
        self.assertIn("整数である必要があります", str(context.exception))
        
        # Out of range values
        with self.assertRaises(ValueError) as context:
            KnowledgeBaseConfig(
                knowledge_base_id="ABCDEFGHIJ",
                retry_attempts=-1
            )
        self.assertIn("0から10の間である必要があります", str(context.exception))
        
        with self.assertRaises(ValueError) as context:
            KnowledgeBaseConfig(
                knowledge_base_id="ABCDEFGHIJ",
                retry_attempts=11
            )
        self.assertIn("0から10の間である必要があります", str(context.exception))
    
    def test_to_dict(self):
        """Test converting configuration to dictionary"""
        config = KnowledgeBaseConfig(
            knowledge_base_id="ABCDEFGHIJ",
            region="us-west-2",
            similarity_top_k=10,
            confidence_threshold=0.5,
            mode="bedrock",
            enable_fallback=False,
            retry_attempts=5
        )
        
        config_dict = config.to_dict()
        
        expected_dict = {
            'knowledge_base_id': "ABCDEFGHIJ",
            'region': "us-west-2",
            'similarity_top_k': 10,
            'confidence_threshold': 0.5,
            'mode': "bedrock",
            'enable_fallback': False,
            'retry_attempts': 5
        }
        
        self.assertEqual(config_dict, expected_dict)
    
    def test_from_dict(self):
        """Test creating configuration from dictionary"""
        config_dict = {
            'knowledge_base_id': "ABCDEFGHIJ",
            'region': "us-west-2",
            'similarity_top_k': 10,
            'confidence_threshold': 0.5,
            'mode': "bedrock",
            'enable_fallback': False,
            'retry_attempts': 5
        }
        
        config = KnowledgeBaseConfig.from_dict(config_dict)
        
        self.assertEqual(config.knowledge_base_id, "ABCDEFGHIJ")
        self.assertEqual(config.region, "us-west-2")
        self.assertEqual(config.similarity_top_k, 10)
        self.assertEqual(config.confidence_threshold, 0.5)
        self.assertEqual(config.mode, "bedrock")
        self.assertFalse(config.enable_fallback)
        self.assertEqual(config.retry_attempts, 5)
    
    def test_mode_checks(self):
        """Test mode checking methods"""
        # Test bedrock mode
        config_bedrock = KnowledgeBaseConfig(
            knowledge_base_id="ABCDEFGHIJ",
            mode="bedrock"
        )
        self.assertTrue(config_bedrock.is_bedrock_enabled())
        self.assertFalse(config_bedrock.is_local_enabled())
        
        # Test local mode
        config_local = KnowledgeBaseConfig(
            knowledge_base_id="ABCDEFGHIJ",
            mode="local"
        )
        self.assertFalse(config_local.is_bedrock_enabled())
        self.assertTrue(config_local.is_local_enabled())
        
        # Test hybrid mode
        config_hybrid = KnowledgeBaseConfig(
            knowledge_base_id="ABCDEFGHIJ",
            mode="hybrid"
        )
        self.assertTrue(config_hybrid.is_bedrock_enabled())
        self.assertTrue(config_hybrid.is_local_enabled())
    
    def test_get_aws_config(self):
        """Test AWS configuration extraction"""
        config = KnowledgeBaseConfig(
            knowledge_base_id="ABCDEFGHIJ",
            region="eu-west-1"
        )
        
        aws_config = config.get_aws_config()
        expected_aws_config = {'region_name': 'eu-west-1'}
        
        self.assertEqual(aws_config, expected_aws_config)
    
    def test_create_default_config(self):
        """Test creating default configuration"""
        config = create_default_config("ABCDEFGHIJ")
        
        self.assertEqual(config.knowledge_base_id, "ABCDEFGHIJ")
        self.assertEqual(config.region, "us-east-1")
        
        # Test with custom region
        config_custom = create_default_config("ABCDEFGHIJ", "eu-west-1")
        self.assertEqual(config_custom.region, "eu-west-1")
    
    def test_validate_config_dict(self):
        """Test configuration dictionary validation"""
        # Valid configuration
        valid_config = {
            'knowledge_base_id': "ABCDEFGHIJ",
            'region': "us-east-1"
        }
        self.assertTrue(validate_config_dict(valid_config))
        
        # Invalid configuration
        invalid_config = {
            'knowledge_base_id': "",
            'region': "us-east-1"
        }
        with self.assertRaises(ValueError):
            validate_config_dict(invalid_config)


class TestBedrockKnowledgeBaseRetriever(unittest.TestCase):
    """Test cases for BedrockKnowledgeBaseRetriever class"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.valid_config = KnowledgeBaseConfig(
            knowledge_base_id="ABCDEFGHIJ",
            region="us-east-1",
            mode="bedrock"
        )
        
        self.invalid_config = KnowledgeBaseConfig(
            knowledge_base_id="ABCDEFGHIJ",
            region="us-east-1",
            mode="local"  # Bedrock not enabled
        )
    
    def test_config_validation(self):
        """Test configuration validation during initialization"""
        # Valid configuration should work
        try:
            retriever = BedrockKnowledgeBaseRetriever(self.valid_config)
            # Should not raise exception
        except ValueError:
            self.fail("Valid configuration should not raise ValueError")
        
        # Invalid configuration should raise error
        with self.assertRaises(ValueError) as context:
            BedrockKnowledgeBaseRetriever(self.invalid_config)
        self.assertIn("Bedrockモードが有効になっていません", str(context.exception))
    
    @patch('core.llm.bedrock_kb_retriever.boto3.client')
    def test_client_initialization(self, mock_boto_client):
        """Test Bedrock client initialization"""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client
        
        retriever = BedrockKnowledgeBaseRetriever(self.valid_config)
        
        # Access client property to trigger initialization
        client = retriever.client
        
        # Verify boto3.client was called with correct parameters
        mock_boto_client.assert_called_once_with(
            service_name='bedrock-agent-runtime',
            region_name='us-east-1'
        )
        
        self.assertEqual(client, mock_client)
    
    @patch('core.llm.bedrock_kb_retriever.boto3.client')
    def test_client_initialization_with_credentials(self, mock_boto_client):
        """Test client initialization with custom credentials"""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client
        
        retriever = BedrockKnowledgeBaseRetriever(
            self.valid_config,
            aws_access_key_id="test_key",
            aws_secret_access_key="test_secret"
        )
        
        # Access client property to trigger initialization
        client = retriever.client
        
        # Verify boto3.client was called with credentials
        mock_boto_client.assert_called_once_with(
            service_name='bedrock-agent-runtime',
            region_name='us-east-1',
            aws_access_key_id="test_key",
            aws_secret_access_key="test_secret"
        )
    
    @patch('core.llm.bedrock_kb_retriever.boto3.client')
    def test_retrieve_empty_query(self, mock_boto_client):
        """Test handling of empty queries"""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client
        
        retriever = BedrockKnowledgeBaseRetriever(self.valid_config)
        
        # Test empty string
        result = retriever.retrieve("")
        self.assertEqual(result, [])
        
        # Test whitespace only
        result = retriever.retrieve("   ")
        self.assertEqual(result, [])
        
        # Test None (converted to string)
        result = retriever.retrieve(None)
        self.assertEqual(result, [])
    
    @patch('core.llm.bedrock_kb_retriever.boto3.client')
    def test_successful_retrieval(self, mock_boto_client):
        """Test successful document retrieval"""
        # Mock Bedrock response
        mock_response = {
            'retrievalResults': [
                {
                    'content': {'text': 'Test document content 1'},
                    'score': 0.8,
                    'location': {
                        'type': 'S3',
                        's3Location': {'uri': 's3://bucket/doc1.txt'}
                    }
                },
                {
                    'content': {'text': 'Test document content 2'},
                    'score': 0.6,
                    'location': {
                        'type': 'S3',
                        's3Location': {'uri': 's3://bucket/doc2.txt'}
                    }
                }
            ]
        }
        
        mock_client = Mock()
        mock_client.retrieve.return_value = mock_response
        mock_boto_client.return_value = mock_client
        
        retriever = BedrockKnowledgeBaseRetriever(self.valid_config)
        
        # Perform retrieval
        results = retriever.retrieve("test query")
        
        # Verify API call
        mock_client.retrieve.assert_called_once_with(
            knowledgeBaseId="ABCDEFGHIJ",
            retrievalQuery={'text': 'test query'},
            retrievalConfiguration={
                'vectorSearchConfiguration': {
                    'numberOfResults': 5
                }
            }
        )
        
        # Verify results
        self.assertEqual(len(results), 2)
        
        # Check first result
        first_result = results[0]
        self.assertEqual(first_result.score, 0.8)
        self.assertEqual(first_result.node.text, 'Test document content 1')
        self.assertEqual(first_result.node.metadata['source'], 'bedrock')
        self.assertEqual(first_result.node.metadata['s3_uri'], 's3://bucket/doc1.txt')
        self.assertEqual(first_result.node.metadata['file_name'], 'doc1.txt')
        
        # Check second result
        second_result = results[1]
        self.assertEqual(second_result.score, 0.6)
        self.assertEqual(second_result.node.text, 'Test document content 2')
    
    @patch('core.llm.bedrock_kb_retriever.boto3.client')
    def test_confidence_threshold_filtering(self, mock_boto_client):
        """Test filtering results by confidence threshold"""
        # Create config with confidence threshold
        config_with_threshold = KnowledgeBaseConfig(
            knowledge_base_id="ABCDEFGHIJ",
            region="us-east-1",
            mode="bedrock",
            confidence_threshold=0.7
        )
        
        # Mock response with mixed scores
        mock_response = {
            'retrievalResults': [
                {
                    'content': {'text': 'High confidence content'},
                    'score': 0.8  # Above threshold
                },
                {
                    'content': {'text': 'Low confidence content'},
                    'score': 0.5  # Below threshold
                }
            ]
        }
        
        mock_client = Mock()
        mock_client.retrieve.return_value = mock_response
        mock_boto_client.return_value = mock_client
        
        retriever = BedrockKnowledgeBaseRetriever(config_with_threshold)
        results = retriever.retrieve("test query")
        
        # Should only return high confidence result
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].node.text, 'High confidence content')
        self.assertEqual(results[0].score, 0.8)
    
    @patch('core.llm.bedrock_kb_retriever.boto3.client')
    @patch('core.llm.bedrock_kb_retriever.time.sleep')
    def test_retry_logic(self, mock_sleep, mock_boto_client):
        """Test retry logic on API failures"""
        from botocore.exceptions import ClientError
        
        # Create error response
        error_response = {
            'Error': {
                'Code': 'ThrottlingException',
                'Message': 'Rate exceeded'
            }
        }
        
        mock_client = Mock()
        # First two calls fail, third succeeds
        mock_client.retrieve.side_effect = [
            ClientError(error_response, 'retrieve'),
            ClientError(error_response, 'retrieve'),
            {'retrievalResults': []}
        ]
        mock_boto_client.return_value = mock_client
        
        retriever = BedrockKnowledgeBaseRetriever(self.valid_config)
        results = retriever.retrieve("test query")
        
        # Should have made 3 attempts
        self.assertEqual(mock_client.retrieve.call_count, 3)
        
        # Should have slept twice (between retries)
        self.assertEqual(mock_sleep.call_count, 2)
        
        # Should return empty results from successful third call
        self.assertEqual(results, [])
    
    @patch('core.llm.bedrock_kb_retriever.boto3.client')
    def test_api_error_handling(self, mock_boto_client):
        """Test handling of various API errors"""
        from botocore.exceptions import ClientError
        
        # Test ResourceNotFoundException
        error_response = {
            'Error': {
                'Code': 'ResourceNotFoundException',
                'Message': 'KnowledgeBase not found'
            }
        }
        
        mock_client = Mock()
        mock_client.retrieve.side_effect = ClientError(error_response, 'retrieve')
        mock_boto_client.return_value = mock_client
        
        retriever = BedrockKnowledgeBaseRetriever(self.valid_config)
        results = retriever.retrieve("test query")
        
        # Should return empty results on error
        self.assertEqual(results, [])
    
    def test_get_knowledge_base_info(self):
        """Test getting KnowledgeBase information"""
        retriever = BedrockKnowledgeBaseRetriever(self.valid_config)
        info = retriever.get_knowledge_base_info()
        
        expected_info = {
            'knowledge_base_id': "ABCDEFGHIJ",
            'region': "us-east-1",
            'similarity_top_k': 5,
            'confidence_threshold': 0.0,
            'status': 'configured'
        }
        
        self.assertEqual(info, expected_info)
    
    def test_create_bedrock_retriever_function(self):
        """Test the create_bedrock_retriever convenience function"""
        retriever = create_bedrock_retriever(
            knowledge_base_id="ABCDEFGHIJ",
            region="eu-west-1",
            similarity_top_k=10,
            confidence_threshold=0.5
        )
        
        self.assertIsInstance(retriever, BedrockKnowledgeBaseRetriever)
        self.assertEqual(retriever.config.knowledge_base_id, "ABCDEFGHIJ")
        self.assertEqual(retriever.config.region, "eu-west-1")
        self.assertEqual(retriever.config.similarity_top_k, 10)
        self.assertEqual(retriever.config.confidence_threshold, 0.5)
        self.assertEqual(retriever.config.mode, "bedrock")


class TestKnowledgeBaseIntegration(unittest.TestCase):
    """Integration tests for KnowledgeBase components"""
    
    def test_config_retriever_integration(self):
        """Test integration between config and retriever"""
        config = KnowledgeBaseConfig(
            knowledge_base_id="ABCDEFGHIJ",
            region="us-east-1",
            similarity_top_k=10,
            confidence_threshold=0.3,
            mode="bedrock",
            retry_attempts=2
        )
        
        # Should be able to create retriever with config
        try:
            retriever = BedrockKnowledgeBaseRetriever(config)
            self.assertEqual(retriever.config, config)
        except ValueError:
            self.fail("Should be able to create retriever with valid config")
    
    def test_config_serialization_roundtrip(self):
        """Test configuration serialization and deserialization"""
        original_config = KnowledgeBaseConfig(
            knowledge_base_id="ABCDEFGHIJ",
            region="ap-southeast-1",
            similarity_top_k=15,
            confidence_threshold=0.4,
            mode="hybrid",
            enable_fallback=False,
            retry_attempts=1
        )
        
        # Convert to dict and back
        config_dict = original_config.to_dict()
        restored_config = KnowledgeBaseConfig.from_dict(config_dict)
        
        # Should be identical
        self.assertEqual(original_config.knowledge_base_id, restored_config.knowledge_base_id)
        self.assertEqual(original_config.region, restored_config.region)
        self.assertEqual(original_config.similarity_top_k, restored_config.similarity_top_k)
        self.assertEqual(original_config.confidence_threshold, restored_config.confidence_threshold)
        self.assertEqual(original_config.mode, restored_config.mode)
        self.assertEqual(original_config.enable_fallback, restored_config.enable_fallback)
        self.assertEqual(original_config.retry_attempts, restored_config.retry_attempts)


def run_tests():
    """Run all KnowledgeBase tests"""
    print("🧪 Running KnowledgeBase Component Tests")
    print("=" * 50)
    
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add test classes
    suite.addTests(loader.loadTestsFromTestCase(TestKnowledgeBaseConfig))
    suite.addTests(loader.loadTestsFromTestCase(TestBedrockKnowledgeBaseRetriever))
    suite.addTests(loader.loadTestsFromTestCase(TestKnowledgeBaseIntegration))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Print summary
    print("\n" + "=" * 50)
    print("🏁 Test Summary")
    print("=" * 50)
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    
    if result.failures:
        print("\n❌ Failures:")
        for test, traceback in result.failures:
            print(f"  - {test}: {traceback}")
    
    if result.errors:
        print("\n⚠️ Errors:")
        for test, traceback in result.errors:
            print(f"  - {test}: {traceback}")
    
    success = len(result.failures) == 0 and len(result.errors) == 0
    print(f"\n🎯 Overall: {'✅ ALL TESTS PASSED' if success else '❌ SOME TESTS FAILED'}")
    
    return success


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)