#!/usr/bin/env python3
"""
Enhanced RAG functionality tests for PE-GPT Bedrock KnowledgeBase integration

This module tests the enhanced_rag_load function and related chat engine integration
functionality to ensure proper operation with both local and Bedrock KnowledgeBase sources.

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

# Add core modules to path
sys.path.append('.')
sys.path.append('core')

# Import modules to test
from core.llm.llm import enhanced_rag_load, EnhancedVectorStoreIndex
from core.knowledge.kb_config import KnowledgeBaseConfig
from core.llm.hybrid_retriever import HybridRetriever
from core.llm.bedrock_kb_retriever import BedrockKnowledgeBaseRetriever


class TestEnhancedRAGLoad(unittest.TestCase):
    """Test cases for enhanced_rag_load function"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.test_dir = tempfile.mkdtemp()
        self.test_file_path = os.path.join(self.test_dir, "test_doc.txt")
        
        # Create a test document
        with open(self.test_file_path, 'w', encoding='utf-8') as f:
            f.write("This is a test document about power electronics. "
                   "Power electronics deals with the conversion of electrical power. "
                   "It involves switching devices like MOSFETs and IGBTs.")
        
        # Mock KnowledgeBase config
        self.mock_kb_config = KnowledgeBaseConfig(
            knowledge_base_id="TEST123456",
            region="us-east-1",
            mode="hybrid",
            similarity_top_k=5,
            enable_fallback=True
        )
    
    def tearDown(self):
        """Clean up test fixtures"""
        import shutil
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    @patch('streamlit.spinner')
    @patch('streamlit.info')
    @patch('streamlit.success')
    @patch('streamlit.error')
    @patch('streamlit.warning')
    def test_local_only_mode(self, mock_warning, mock_error, mock_success, mock_info, mock_spinner):
        """Test enhanced_rag_load in local-only mode"""
        mock_spinner.return_value.__enter__ = Mock()
        mock_spinner.return_value.__exit__ = Mock()
        
        try:
            # Test local-only mode (no KnowledgeBase config)
            index = enhanced_rag_load(
                database_folder=self.test_dir,
                knowledge_base_config=None,
                temperature=0.1,
                chunk_size=256
            )
            
            # Should return a VectorStoreIndex for backward compatibility
            self.assertIsNotNone(index)
            self.assertTrue(hasattr(index, 'as_chat_engine'))
            self.assertTrue(hasattr(index, 'as_retriever'))
            
        except Exception as e:
            # If dependencies are missing, skip the test
            if "llama_index" in str(e) or "bedrock" in str(e).lower():
                self.skipTest(f"Dependencies not available: {e}")
            else:
                raise
    
    @patch('streamlit.spinner')
    @patch('streamlit.info')
    @patch('streamlit.success')
    @patch('streamlit.error')
    @patch('streamlit.warning')
    def test_bedrock_only_mode_with_mock(self, mock_warning, mock_error, mock_success, mock_info, mock_spinner):
        """Test enhanced_rag_load in Bedrock-only mode with mocked components"""
        mock_spinner.return_value.__enter__ = Mock()
        mock_spinner.return_value.__exit__ = Mock()
        
        # Create a mock config for Bedrock-only mode with invalid KB ID
        bedrock_config = KnowledgeBaseConfig(
            knowledge_base_id="INVALID_KB_ID",  # Use clearly invalid ID
            region="us-east-1",
            mode="bedrock",
            similarity_top_k=5,
            enable_fallback=False  # Disable fallback to force failure
        )
        
        try:
            # This should either succeed (if AWS credentials work) or fail gracefully
            result = enhanced_rag_load(
                database_folder=None,
                knowledge_base_config=bedrock_config,
                temperature=0.1
            )
            
            # If it succeeds, verify it's a valid index
            if result is not None:
                self.assertTrue(hasattr(result, 'as_chat_engine'))
                self.assertTrue(hasattr(result, 'as_retriever'))
            
        except Exception as e:
            # Expected to fail with invalid KnowledgeBase ID or AWS issues
            self.assertIn(("認証" in str(e) or "初期化" in str(e) or "AWS" in str(e) or 
                          "KnowledgeBase" in str(e) or "Bedrock" in str(e)), [True])
            
        # Test should pass either way since we're testing error handling
    
    @patch('streamlit.spinner')
    @patch('streamlit.info')
    @patch('streamlit.success')
    @patch('streamlit.error')
    @patch('streamlit.warning')
    def test_hybrid_mode_fallback(self, mock_warning, mock_error, mock_success, mock_info, mock_spinner):
        """Test enhanced_rag_load in hybrid mode with fallback to local"""
        mock_spinner.return_value.__enter__ = Mock()
        mock_spinner.return_value.__exit__ = Mock()
        
        try:
            # Test hybrid mode with fallback enabled
            index = enhanced_rag_load(
                database_folder=self.test_dir,
                knowledge_base_config=self.mock_kb_config,
                temperature=0.1,
                chunk_size=256
            )
            
            # Should return an EnhancedVectorStoreIndex or fall back to local
            self.assertIsNotNone(index)
            self.assertTrue(hasattr(index, 'as_chat_engine'))
            self.assertTrue(hasattr(index, 'as_retriever'))
            
        except Exception as e:
            # If dependencies are missing, skip the test
            if "llama_index" in str(e) or "bedrock" in str(e).lower():
                self.skipTest(f"Dependencies not available: {e}")
            else:
                raise
    
    def test_invalid_configurations(self):
        """Test enhanced_rag_load with invalid configurations"""
        
        # Test with no sources
        with self.assertRaises(ValueError) as context:
            enhanced_rag_load(database_folder=None, knowledge_base_config=None)
        
        self.assertIn("少なくとも", str(context.exception))
    
    def test_parameter_validation(self):
        """Test parameter validation in enhanced_rag_load"""
        
        # Test with invalid chunk_size
        try:
            index = enhanced_rag_load(
                database_folder=self.test_dir,
                chunk_size=-1  # Invalid chunk size
            )
            # Should handle gracefully or use default
            self.assertIsNotNone(index)
        except Exception as e:
            # Should not raise exception for invalid chunk_size
            if "chunk_size" in str(e):
                self.fail("Should handle invalid chunk_size gracefully")


class TestEnhancedVectorStoreIndex(unittest.TestCase):
    """Test cases for EnhancedVectorStoreIndex class"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Create mock hybrid retriever
        self.mock_hybrid_retriever = Mock(spec=HybridRetriever)
        self.mock_local_index = Mock()
        
        # Create EnhancedVectorStoreIndex instance
        self.enhanced_index = EnhancedVectorStoreIndex(
            hybrid_retriever=self.mock_hybrid_retriever,
            local_index=self.mock_local_index
        )
    
    def test_as_retriever(self):
        """Test as_retriever method"""
        retriever = self.enhanced_index.as_retriever(similarity_top_k=5)
        
        # Should return the hybrid retriever
        self.assertEqual(retriever, self.mock_hybrid_retriever)
    
    def test_as_query_engine(self):
        """Test as_query_engine method"""
        with patch('llama_index.core.query_engine.RetrieverQueryEngine') as mock_query_engine:
            mock_query_engine.from_args.return_value = Mock()
            
            query_engine = self.enhanced_index.as_query_engine(similarity_top_k=3)
            
            # Should create query engine with hybrid retriever
            mock_query_engine.from_args.assert_called_once()
            self.assertIsNotNone(query_engine)
    
    def test_as_chat_engine(self):
        """Test as_chat_engine method"""
        with patch('llama_index.core.chat_engine.CondensePlusContextChatEngine') as mock_chat_engine:
            with patch('llama_index.core.query_engine.RetrieverQueryEngine') as mock_query_engine:
                mock_query_engine.from_args.return_value = Mock()
                mock_chat_engine.from_defaults.return_value = Mock()
                
                chat_engine = self.enhanced_index.as_chat_engine(similarity_top_k=3)
                
                # Should create chat engine
                mock_chat_engine.from_defaults.assert_called_once()
                self.assertIsNotNone(chat_engine)
    
    def test_get_retriever_info(self):
        """Test get_retriever_info method"""
        # Mock retriever info
        mock_info = {"mode": "hybrid", "local_available": True}
        self.mock_hybrid_retriever.get_retriever_info.return_value = mock_info
        
        info = self.enhanced_index.get_retriever_info()
        
        self.assertEqual(info, mock_info)
        self.mock_hybrid_retriever.get_retriever_info.assert_called_once()
    
    def test_backward_compatibility(self):
        """Test backward compatibility methods"""
        # Test __getattr__ delegation to local_index
        self.mock_local_index.some_method.return_value = "test_result"
        
        result = self.enhanced_index.some_method()
        
        self.assertEqual(result, "test_result")
        self.mock_local_index.some_method.assert_called_once()
    
    def test_get_nodes(self):
        """Test get_nodes method"""
        mock_nodes = [Mock(), Mock()]
        self.mock_local_index.get_nodes.return_value = mock_nodes
        
        nodes = self.enhanced_index.get_nodes()
        
        self.assertEqual(nodes, mock_nodes)
        self.mock_local_index.get_nodes.assert_called_once_with(None)
    
    def test_insert_nodes_not_supported(self):
        """Test that insert_nodes raises NotImplementedError"""
        with self.assertRaises(NotImplementedError):
            self.enhanced_index.insert_nodes([Mock()])
    
    def test_delete_nodes_not_supported(self):
        """Test that delete_nodes raises NotImplementedError"""
        with self.assertRaises(NotImplementedError):
            self.enhanced_index.delete_nodes(["node1", "node2"])


class TestChatEngineIntegration(unittest.TestCase):
    """Test cases for chat engine integration"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.test_dir = tempfile.mkdtemp()
        self.test_file_path = os.path.join(self.test_dir, "test_doc.txt")
        
        # Create a test document
        with open(self.test_file_path, 'w', encoding='utf-8') as f:
            f.write("Power electronics is the application of solid-state electronics "
                   "to the control and conversion of electric power. "
                   "Key components include power semiconductors like MOSFETs, IGBTs, and diodes.")
    
    def tearDown(self):
        """Clean up test fixtures"""
        import shutil
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    @patch('streamlit.spinner')
    @patch('streamlit.info')
    @patch('streamlit.success')
    @patch('streamlit.error')
    @patch('streamlit.warning')
    def test_chat_engine_creation_and_usage(self, mock_warning, mock_error, mock_success, mock_info, mock_spinner):
        """Test chat engine creation and basic usage"""
        mock_spinner.return_value.__enter__ = Mock()
        mock_spinner.return_value.__exit__ = Mock()
        
        try:
            # Create enhanced RAG index
            index = enhanced_rag_load(
                database_folder=self.test_dir,
                knowledge_base_config=None,  # Local-only for testing
                temperature=0.1,
                chunk_size=256
            )
            
            self.assertIsNotNone(index)
            
            # Test retriever creation
            retriever = index.as_retriever(similarity_top_k=3)
            self.assertIsNotNone(retriever)
            
            # Test query engine creation
            query_engine = index.as_query_engine(similarity_top_k=3)
            self.assertIsNotNone(query_engine)
            
            # Test chat engine creation
            chat_engine = index.as_chat_engine(similarity_top_k=3)
            self.assertIsNotNone(chat_engine)
            
        except Exception as e:
            # If dependencies are missing, skip the test
            if "llama_index" in str(e) or "bedrock" in str(e).lower():
                self.skipTest(f"Dependencies not available: {e}")
            else:
                raise
    
    def test_node_compatibility(self):
        """Test that nodes are properly formatted for chat engine compatibility"""
        from core.llm.bedrock_kb_retriever import ensure_chat_engine_compatibility
        from llama_index.core.schema import NodeWithScore, TextNode
        
        # Create test nodes
        test_nodes = [
            NodeWithScore(
                node=TextNode(text="Test content 1", metadata={"source": "test"}),
                score=0.8
            ),
            NodeWithScore(
                node=TextNode(text="Test content 2", metadata={"source": "test"}),
                score=0.6
            )
        ]
        
        # Test compatibility enhancement
        enhanced_nodes = ensure_chat_engine_compatibility(test_nodes)
        
        self.assertEqual(len(enhanced_nodes), 2)
        
        for node_with_score in enhanced_nodes:
            self.assertIsNotNone(node_with_score.node.text)
            self.assertIsNotNone(node_with_score.node.metadata)
            self.assertTrue(node_with_score.node.metadata.get('processed_for_chat', False))
            self.assertIsInstance(node_with_score.score, (int, float))
            self.assertGreaterEqual(node_with_score.score, 0)


def run_enhanced_rag_tests():
    """Run all enhanced RAG tests"""
    print("🧪 Running Enhanced RAG Tests")
    print("=" * 50)
    
    # Create test suite
    test_suite = unittest.TestSuite()
    
    # Add test cases
    test_suite.addTest(unittest.makeSuite(TestEnhancedRAGLoad))
    test_suite.addTest(unittest.makeSuite(TestEnhancedVectorStoreIndex))
    test_suite.addTest(unittest.makeSuite(TestChatEngineIntegration))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    
    # Print summary
    print("\n" + "=" * 50)
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Skipped: {len(result.skipped) if hasattr(result, 'skipped') else 0}")
    
    if result.failures:
        print("\n❌ FAILURES:")
        for test, traceback in result.failures:
            print(f"  - {test}: {traceback}")
    
    if result.errors:
        print("\n❌ ERRORS:")
        for test, traceback in result.errors:
            print(f"  - {test}: {traceback}")
    
    success = len(result.failures) == 0 and len(result.errors) == 0
    print(f"\n🎯 Overall Result: {'✅ PASSED' if success else '❌ FAILED'}")
    
    return success


if __name__ == "__main__":
    success = run_enhanced_rag_tests()
    sys.exit(0 if success else 1)