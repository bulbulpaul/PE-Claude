#!/usr/bin/env python3
"""
Unit tests for Hybrid Retriever components
Tests HybridRetriever and SearchModeManager classes
"""

import os
import sys
import unittest
from unittest.mock import Mock, patch, MagicMock
from concurrent.futures import ThreadPoolExecutor
from typing import List, Dict, Any

# Add core modules to path
sys.path.append('.')
sys.path.append('core')

# Import the modules to test
from core.llm.hybrid_retriever import (
    HybridRetriever,
    SearchModeManager,
    create_hybrid_retriever,
    create_mode_manager
)
from core.knowledge.kb_config import KnowledgeBaseConfig
from core.llm.bedrock_kb_retriever import BedrockKnowledgeBaseRetriever

# Mock llama_index components
from llama_index.core.schema import NodeWithScore, TextNode
from llama_index.core.retrievers import BaseRetriever


class MockLocalRetriever(BaseRetriever):
    """Mock local retriever for testing"""
    
    def __init__(self, mock_results=None):
        super().__init__()
        self.mock_results = mock_results or []
    
    def _retrieve(self, query_bundle):
        query_str = query_bundle.query_str if hasattr(query_bundle, 'query_str') else str(query_bundle)
        return self.retrieve(query_str)
    
    def retrieve(self, query: str) -> List[NodeWithScore]:
        # Return mock results with local source metadata
        results = []
        for i, content in enumerate(self.mock_results):
            node = TextNode(
                text=content,
                metadata={'source': 'local', 'doc_id': f'local_{i}'}
            )
            results.append(NodeWithScore(node=node, score=0.8 - i * 0.1))
        return results


class TestSearchModeManager(unittest.TestCase):
    """Test cases for SearchModeManager class"""
    
    def test_initialization_default_mode(self):
        """Test initialization with default mode"""
        manager = SearchModeManager()
        self.assertEqual(manager.get_mode(), "hybrid")
        self.assertEqual(manager.get_mode_history(), ["hybrid"])
    
    def test_initialization_custom_mode(self):
        """Test initialization with custom mode"""
        manager = SearchModeManager("local")
        self.assertEqual(manager.get_mode(), "local")
        self.assertEqual(manager.get_mode_history(), ["local"])
    
    def test_invalid_mode_initialization(self):
        """Test initialization with invalid mode"""
        with self.assertRaises(ValueError) as context:
            SearchModeManager("invalid")
        self.assertIn("Invalid mode: invalid", str(context.exception))
    
    def test_mode_validation(self):
        """Test mode validation method"""
        # Valid modes
        self.assertTrue(SearchModeManager.validate_mode("local"))
        self.assertTrue(SearchModeManager.validate_mode("bedrock"))
        self.assertTrue(SearchModeManager.validate_mode("hybrid"))
        
        # Invalid mode
        with self.assertRaises(ValueError):
            SearchModeManager.validate_mode("invalid")
    
    def test_set_mode(self):
        """Test setting mode"""
        manager = SearchModeManager("local")
        
        # Change to bedrock mode
        previous = manager.set_mode("bedrock")
        self.assertEqual(previous, "local")
        self.assertEqual(manager.get_mode(), "bedrock")
        self.assertEqual(manager.get_mode_history(), ["local", "bedrock"])
        
        # Change to hybrid mode
        previous = manager.set_mode("hybrid")
        self.assertEqual(previous, "bedrock")
        self.assertEqual(manager.get_mode(), "hybrid")
        self.assertEqual(manager.get_mode_history(), ["local", "bedrock", "hybrid"])
    
    def test_set_invalid_mode(self):
        """Test setting invalid mode"""
        manager = SearchModeManager()
        
        with self.assertRaises(ValueError):
            manager.set_mode("invalid")
        
        # Mode should remain unchanged
        self.assertEqual(manager.get_mode(), "hybrid")
    
    def test_mode_enablement_checks(self):
        """Test mode enablement check methods"""
        # Local mode
        manager = SearchModeManager("local")
        self.assertTrue(manager.is_local_enabled())
        self.assertFalse(manager.is_bedrock_enabled())
        
        # Bedrock mode
        manager.set_mode("bedrock")
        self.assertFalse(manager.is_local_enabled())
        self.assertTrue(manager.is_bedrock_enabled())
        
        # Hybrid mode
        manager.set_mode("hybrid")
        self.assertTrue(manager.is_local_enabled())
        self.assertTrue(manager.is_bedrock_enabled())
    
    def test_mode_descriptions(self):
        """Test mode description method"""
        manager = SearchModeManager()
        
        # Test descriptions for all modes
        local_desc = manager.get_mode_description("local")
        self.assertIn("ローカルファイルのみ", local_desc)
        
        bedrock_desc = manager.get_mode_description("bedrock")
        self.assertIn("Bedrock KnowledgeBase", bedrock_desc)
        
        hybrid_desc = manager.get_mode_description("hybrid")
        self.assertIn("両方を検索", hybrid_desc)
        
        # Test current mode description
        manager.set_mode("local")
        current_desc = manager.get_mode_description()
        self.assertEqual(current_desc, local_desc)
    
    def test_recommended_mode(self):
        """Test recommended mode logic"""
        manager = SearchModeManager()
        
        # Both available, prefer comprehensive
        rec_mode = manager.get_recommended_mode(True, True, False)
        self.assertEqual(rec_mode, "hybrid")
        
        # Both available, prefer speed
        rec_mode = manager.get_recommended_mode(True, True, True)
        self.assertEqual(rec_mode, "local")
        
        # Only local available
        rec_mode = manager.get_recommended_mode(True, False, False)
        self.assertEqual(rec_mode, "local")
        
        # Only bedrock available
        rec_mode = manager.get_recommended_mode(False, True, False)
        self.assertEqual(rec_mode, "bedrock")
        
        # Neither available
        with self.assertRaises(ValueError):
            manager.get_recommended_mode(False, False, False)
    
    def test_to_dict(self):
        """Test converting manager state to dictionary"""
        manager = SearchModeManager("local")
        manager.set_mode("bedrock")
        
        state_dict = manager.to_dict()
        
        expected_dict = {
            "current_mode": "bedrock",
            "mode_history": ["local", "bedrock"],
            "valid_modes": ["local", "bedrock", "hybrid"],
            "local_enabled": False,
            "bedrock_enabled": True
        }
        
        self.assertEqual(state_dict, expected_dict)


class TestHybridRetriever(unittest.TestCase):
    """Test cases for HybridRetriever class"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.config = KnowledgeBaseConfig(
            knowledge_base_id="ABCDEFGHIJ",
            region="us-east-1",
            mode="hybrid"
        )
        
        self.local_retriever = MockLocalRetriever(["Local document 1", "Local document 2"])
        
        # Mock Bedrock retriever
        self.bedrock_retriever = Mock(spec=BedrockKnowledgeBaseRetriever)
        self.bedrock_retriever.retrieve.return_value = [
            NodeWithScore(
                node=TextNode(text="Bedrock document 1", metadata={'source': 'bedrock'}),
                score=0.9
            ),
            NodeWithScore(
                node=TextNode(text="Bedrock document 2", metadata={'source': 'bedrock'}),
                score=0.7
            )
        ]
    
    def test_initialization_with_retrievers(self):
        """Test initialization with both retrievers"""
        retriever = HybridRetriever(
            local_retriever=self.local_retriever,
            bedrock_retriever=self.bedrock_retriever,
            mode="hybrid"
        )
        
        self.assertEqual(retriever.local_retriever, self.local_retriever)
        self.assertEqual(retriever.bedrock_retriever, self.bedrock_retriever)
        self.assertEqual(retriever.mode, "hybrid")
    
    def test_initialization_with_config(self):
        """Test initialization with config only"""
        with patch('core.llm.hybrid_retriever.BedrockKnowledgeBaseRetriever') as mock_bedrock_class:
            mock_bedrock_instance = Mock()
            mock_bedrock_class.return_value = mock_bedrock_instance
            
            retriever = HybridRetriever(
                local_retriever=self.local_retriever,
                config=self.config,
                mode="hybrid"
            )
            
            # Should create Bedrock retriever from config
            mock_bedrock_class.assert_called_once_with(self.config)
            self.assertEqual(retriever.bedrock_retriever, mock_bedrock_instance)
    
    def test_invalid_configuration(self):
        """Test invalid configuration handling"""
        # Invalid mode
        with self.assertRaises(ValueError):
            HybridRetriever(mode="invalid")
        
        # Local mode without local retriever
        with self.assertRaises(ValueError):
            HybridRetriever(mode="local")
        
        # Bedrock mode without bedrock retriever or config
        with self.assertRaises(ValueError):
            HybridRetriever(mode="bedrock")
    
    def test_local_only_retrieval(self):
        """Test local-only retrieval mode"""
        retriever = HybridRetriever(
            local_retriever=self.local_retriever,
            mode="local"
        )
        
        results = retriever.retrieve("test query")
        
        # Should return only local results
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0].node.text, "Local document 1")
        self.assertEqual(results[0].node.metadata['source'], 'local')
        self.assertEqual(results[1].node.text, "Local document 2")
    
    def test_bedrock_only_retrieval(self):
        """Test Bedrock-only retrieval mode"""
        retriever = HybridRetriever(
            bedrock_retriever=self.bedrock_retriever,
            mode="bedrock"
        )
        
        results = retriever.retrieve("test query")
        
        # Should call bedrock retriever
        self.bedrock_retriever.retrieve.assert_called_once_with("test query")
        
        # Should return bedrock results
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0].node.text, "Bedrock document 1")
        self.assertEqual(results[0].node.metadata['source'], 'bedrock')
    
    def test_hybrid_retrieval(self):
        """Test hybrid retrieval mode"""
        retriever = HybridRetriever(
            local_retriever=self.local_retriever,
            bedrock_retriever=self.bedrock_retriever,
            mode="hybrid"
        )
        
        results = retriever.retrieve("test query")
        
        # Should call bedrock retriever
        self.bedrock_retriever.retrieve.assert_called_once_with("test query")
        
        # Should return merged results (4 total: 2 local + 2 bedrock)
        self.assertEqual(len(results), 4)
        
        # Results should be sorted by score (descending)
        scores = [result.score for result in results]
        self.assertEqual(scores, sorted(scores, reverse=True))
        
        # Should have both local and bedrock sources
        sources = [result.node.metadata['source'] for result in results]
        self.assertIn('local', sources)
        self.assertIn('bedrock', sources)
    
    def test_empty_query_handling(self):
        """Test handling of empty queries"""
        retriever = HybridRetriever(
            local_retriever=self.local_retriever,
            bedrock_retriever=self.bedrock_retriever,
            mode="hybrid"
        )
        
        # Empty string
        results = retriever.retrieve("")
        self.assertEqual(results, [])
        
        # Whitespace only
        results = retriever.retrieve("   ")
        self.assertEqual(results, [])
        
        # None (converted to string)
        results = retriever.retrieve(None)
        self.assertEqual(results, [])
    
    def test_result_deduplication(self):
        """Test result deduplication logic"""
        # Create local retriever with duplicate content
        local_retriever = MockLocalRetriever(["Duplicate content", "Unique local content"])
        
        # Mock bedrock retriever with similar content
        bedrock_retriever = Mock(spec=BedrockKnowledgeBaseRetriever)
        bedrock_retriever.retrieve.return_value = [
            NodeWithScore(
                node=TextNode(text="Duplicate content", metadata={'source': 'bedrock'}),
                score=0.95  # Higher score than local
            ),
            NodeWithScore(
                node=TextNode(text="Unique bedrock content", metadata={'source': 'bedrock'}),
                score=0.85
            )
        ]
        
        retriever = HybridRetriever(
            local_retriever=local_retriever,
            bedrock_retriever=bedrock_retriever,
            mode="hybrid"
        )
        
        results = retriever.retrieve("test query")
        
        # Should deduplicate and keep higher scoring version
        self.assertEqual(len(results), 3)  # 2 unique + 1 deduplicated
        
        # Find the duplicate content result
        duplicate_result = next(r for r in results if "Duplicate content" in r.node.text)
        # Should keep the bedrock version (higher score)
        self.assertEqual(duplicate_result.node.metadata['source'], 'bedrock')
        # Score should be adjusted (0.95 * 1.05 = 0.9975, capped at 1.0)
        self.assertAlmostEqual(duplicate_result.score, 0.9975, places=3)
    
    def test_error_handling_with_fallback(self):
        """Test error handling with fallback enabled"""
        # Mock bedrock retriever that fails
        failing_bedrock = Mock(spec=BedrockKnowledgeBaseRetriever)
        failing_bedrock.retrieve.side_effect = Exception("Bedrock API error")
        
        config_with_fallback = KnowledgeBaseConfig(
            knowledge_base_id="ABCDEFGHIJ",
            region="us-east-1",
            mode="bedrock",
            enable_fallback=True
        )
        
        retriever = HybridRetriever(
            local_retriever=self.local_retriever,
            bedrock_retriever=failing_bedrock,
            config=config_with_fallback,
            mode="bedrock"
        )
        
        results = retriever.retrieve("test query")
        
        # Should fallback to local results
        # The actual implementation calls _retrieve_local_only internally during fallback
        self.assertEqual(len(results), 2)  # MockLocalRetriever returns 2 results
        self.assertEqual(results[0].node.metadata['source'], 'local')
    
    def test_error_handling_without_fallback(self):
        """Test error handling without fallback"""
        # Mock bedrock retriever that fails
        failing_bedrock = Mock(spec=BedrockKnowledgeBaseRetriever)
        failing_bedrock.retrieve.side_effect = Exception("Bedrock API error")
        
        config_no_fallback = KnowledgeBaseConfig(
            knowledge_base_id="ABCDEFGHIJ",
            region="us-east-1",
            mode="bedrock",
            enable_fallback=False
        )
        
        retriever = HybridRetriever(
            bedrock_retriever=failing_bedrock,
            config=config_no_fallback,
            mode="bedrock"
        )
        
        results = retriever.retrieve("test query")
        
        # Should return empty results (no fallback)
        self.assertEqual(results, [])
    
    def test_dynamic_mode_switching(self):
        """Test dynamic mode switching"""
        retriever = HybridRetriever(
            local_retriever=self.local_retriever,
            bedrock_retriever=self.bedrock_retriever,
            mode="hybrid"
        )
        
        # Switch to local mode
        retriever.set_mode("local")
        self.assertEqual(retriever.mode, "local")
        
        results = retriever.retrieve("test query")
        # Should only return local results
        self.assertEqual(len(results), 2)
        self.assertTrue(all(r.node.metadata['source'] == 'local' for r in results))
        
        # Switch to bedrock mode
        retriever.set_mode("bedrock")
        self.assertEqual(retriever.mode, "bedrock")
        
        # Reset mock call count
        self.bedrock_retriever.retrieve.reset_mock()
        
        results = retriever.retrieve("test query")
        # Should call bedrock retriever
        self.bedrock_retriever.retrieve.assert_called_once()
    
    def test_invalid_mode_switching(self):
        """Test invalid mode switching"""
        retriever = HybridRetriever(
            local_retriever=self.local_retriever,
            mode="local"
        )
        
        # Try to switch to bedrock mode without bedrock retriever
        with self.assertRaises(ValueError):
            retriever.set_mode("bedrock")
        
        # Mode should remain unchanged
        self.assertEqual(retriever.mode, "local")
    
    def test_get_retriever_info(self):
        """Test getting retriever information"""
        retriever = HybridRetriever(
            local_retriever=self.local_retriever,
            bedrock_retriever=self.bedrock_retriever,
            config=self.config,
            mode="hybrid"
        )
        
        # Mock bedrock retriever info method
        self.bedrock_retriever.get_knowledge_base_info.return_value = {
            'knowledge_base_id': 'ABCDEFGHIJ',
            'status': 'configured'
        }
        
        info = retriever.get_retriever_info()
        
        expected_info = {
            'mode': 'hybrid',
            'local_available': True,
            'bedrock_available': True,
            'fallback_enabled': True,
            'bedrock_info': {
                'knowledge_base_id': 'ABCDEFGHIJ',
                'status': 'configured'
            }
        }
        
        self.assertEqual(info, expected_info)
    
    def test_score_adjustment(self):
        """Test source-aware score adjustment"""
        retriever = HybridRetriever(
            local_retriever=self.local_retriever,
            bedrock_retriever=self.bedrock_retriever,
            mode="hybrid"
        )
        
        results = retriever.retrieve("test query")
        
        # Find bedrock results (should have slight score boost)
        bedrock_results = [r for r in results if r.node.metadata['source'] == 'bedrock']
        local_results = [r for r in results if r.node.metadata['source'] == 'local']
        
        # Bedrock results should have been boosted (but capped at 1.0)
        self.assertTrue(len(bedrock_results) > 0)
        self.assertTrue(len(local_results) > 0)
        
        # Results should be properly sorted by adjusted scores
        scores = [result.score for result in results]
        self.assertEqual(scores, sorted(scores, reverse=True))


class TestHybridRetrieverIntegration(unittest.TestCase):
    """Integration tests for hybrid retriever components"""
    
    def test_create_hybrid_retriever_function(self):
        """Test the create_hybrid_retriever convenience function"""
        local_retriever = MockLocalRetriever(["Test content"])
        config = KnowledgeBaseConfig(
            knowledge_base_id="ABCDEFGHIJ",
            region="us-east-1",
            mode="hybrid"
        )
        
        retriever = create_hybrid_retriever(
            local_retriever=local_retriever,
            knowledge_base_config=config,
            mode="hybrid"
        )
        
        self.assertIsInstance(retriever, HybridRetriever)
        self.assertEqual(retriever.local_retriever, local_retriever)
        self.assertEqual(retriever.config, config)
        self.assertEqual(retriever.mode, "hybrid")
    
    def test_create_mode_manager_function(self):
        """Test the create_mode_manager convenience function"""
        manager = create_mode_manager("local")
        
        self.assertIsInstance(manager, SearchModeManager)
        self.assertEqual(manager.get_mode(), "local")
    
    def test_mode_manager_retriever_integration(self):
        """Test integration between mode manager and retriever"""
        manager = SearchModeManager("hybrid")
        
        retriever = HybridRetriever(
            local_retriever=MockLocalRetriever(["Test"]),
            bedrock_retriever=Mock(spec=BedrockKnowledgeBaseRetriever),
            mode=manager.get_mode()
        )
        
        # Change mode in manager
        manager.set_mode("local")
        
        # Update retriever mode
        retriever.set_mode(manager.get_mode())
        
        self.assertEqual(retriever.mode, "local")
        self.assertEqual(manager.get_mode(), "local")
    
    @patch('core.llm.hybrid_retriever.ThreadPoolExecutor')
    def test_parallel_execution_in_hybrid_mode(self, mock_executor_class):
        """Test parallel execution of local and bedrock searches"""
        # Mock ThreadPoolExecutor
        mock_executor = Mock()
        mock_executor_class.return_value.__enter__.return_value = mock_executor
        
        # Mock futures
        local_future = Mock()
        local_future.result.return_value = [
            NodeWithScore(
                node=TextNode(text="Local result", metadata={'source': 'local'}),
                score=0.8
            )
        ]
        
        bedrock_future = Mock()
        bedrock_future.result.return_value = [
            NodeWithScore(
                node=TextNode(text="Bedrock result", metadata={'source': 'bedrock'}),
                score=0.9
            )
        ]
        
        mock_executor.submit.side_effect = [local_future, bedrock_future]
        
        retriever = HybridRetriever(
            local_retriever=MockLocalRetriever(["Local content"]),
            bedrock_retriever=Mock(spec=BedrockKnowledgeBaseRetriever),
            mode="hybrid"
        )
        
        results = retriever.retrieve("test query")
        
        # Should have submitted two tasks (local and bedrock)
        self.assertEqual(mock_executor.submit.call_count, 2)
        
        # Should return merged results
        self.assertEqual(len(results), 2)


def run_tests():
    """Run all Hybrid Retriever tests"""
    print("🧪 Running Hybrid Retriever Component Tests")
    print("=" * 50)
    
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add test classes
    suite.addTests(loader.loadTestsFromTestCase(TestSearchModeManager))
    suite.addTests(loader.loadTestsFromTestCase(TestHybridRetriever))
    suite.addTests(loader.loadTestsFromTestCase(TestHybridRetrieverIntegration))
    
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