#!/usr/bin/env python3
"""
End-to-end integration test for main application with KnowledgeBase integration
Tests the complete workflow from main.py with enhanced RAG functionality
"""

import os
import sys
import json
import time
import traceback
from typing import Dict, List, Any
import unittest
from unittest.mock import patch, MagicMock

# Add core modules to path
sys.path.append('.')
sys.path.append('core')

# Import application modules
from core.llm.llm import bedrock_init, enhanced_rag_load
from core.knowledge.kb_config import KnowledgeBaseConfig


class MainApplicationIntegrationTest(unittest.TestCase):
    """
    End-to-end integration test for main application with KnowledgeBase support
    """
    
    @classmethod
    def setUpClass(cls):
        """Set up test environment"""
        cls.test_results = {}
        cls.client = None
        
        # Check if knowledge base directories exist
        cls.kb_paths = [
            "core/knowledge/kb/database",
            "core/knowledge/kb/database1", 
            "core/knowledge/kb/introduction"
        ]
        
        cls.existing_paths = []
        for path in cls.kb_paths:
            if os.path.exists(path) and os.path.isdir(path):
                files = [f for f in os.listdir(path) if f.endswith('.txt')]
                if files:
                    cls.existing_paths.append(path)
    
    def setUp(self):
        """Set up each test"""
        # Mock streamlit session state
        self.mock_session_state = MagicMock()
        self.mock_session_state.kb_mode = 'local'
        self.mock_session_state.kb_id = None
        self.mock_session_state.kb_region = 'us-east-1'
        self.mock_session_state.similarity_top_k = 5
        self.mock_session_state.confidence_threshold = 0.0
    
    def test_main_application_local_mode(self):
        """Test main application workflow in local-only mode"""
        print("Testing main application in local-only mode...")
        
        if not self.existing_paths:
            self.skipTest("No knowledge base directories available")
        
        try:
            # Initialize Bedrock client
            client = bedrock_init()
            self.assertIsNotNone(client, "Bedrock client initialization failed")
            
            # Test enhanced_rag_load for each knowledge base (local mode)
            chat_engines = []
            
            for i, kb_path in enumerate(self.existing_paths[:3]):  # Test up to 3 paths
                print(f"  Testing knowledge base {i}: {kb_path}")
                
                # Load system prompt
                try:
                    with open('core/knowledge/prompts/prompt.txt', 'r') as file:
                        system_prompt = file.read()
                except FileNotFoundError:
                    system_prompt = "You are a helpful assistant specializing in power electronics."
                
                # Create enhanced RAG index (local mode)
                index = enhanced_rag_load(
                    database_folder=kb_path,
                    knowledge_base_config=None,  # Local mode
                    temperature=0.1,
                    chunk_size=512,
                    system_prompt=system_prompt,
                    use_bedrock=True
                )
                
                self.assertIsNotNone(index, f"Enhanced RAG index creation failed for {kb_path}")
                
                # Create chat engine
                if i == 0:  # database
                    chat_engine = index.as_chat_engine(chat_mode="context", similarity_top_k=7)
                elif i == 1:  # database1
                    chat_engine = index.as_chat_engine(similarity_top_k=7)
                else:  # introduction
                    chat_engine = index.as_chat_engine(chat_mode="context", similarity_top_k=7)
                
                self.assertIsNotNone(chat_engine, f"Chat engine creation failed for {kb_path}")
                chat_engines.append(chat_engine)
            
            # Test that we have at least one working chat engine
            self.assertGreater(len(chat_engines), 0, "No chat engines were created successfully")
            
            print(f"  Successfully created {len(chat_engines)} chat engines")
            
        except Exception as e:
            self.fail(f"Main application local mode test failed: {str(e)}")
    
    def test_main_application_hybrid_mode_fallback(self):
        """Test main application workflow in hybrid mode with fallback"""
        print("Testing main application in hybrid mode with fallback...")
        
        if not self.existing_paths:
            self.skipTest("No knowledge base directories available")
        
        try:
            # Create mock KnowledgeBase config (should trigger fallback)
            mock_kb_config = KnowledgeBaseConfig(
                knowledge_base_id="MOCK123456",
                region="us-east-1",
                mode="hybrid",
                enable_fallback=True,
                similarity_top_k=5
            )
            
            # Test enhanced_rag_load with fallback
            kb_path = self.existing_paths[0]
            print(f"  Testing hybrid mode with fallback for: {kb_path}")
            
            # Load system prompt
            try:
                with open('core/knowledge/prompts/prompt.txt', 'r') as file:
                    system_prompt = file.read()
            except FileNotFoundError:
                system_prompt = "You are a helpful assistant specializing in power electronics."
            
            # This should fall back to local mode due to invalid KnowledgeBase ID
            index = enhanced_rag_load(
                database_folder=kb_path,
                knowledge_base_config=mock_kb_config,
                temperature=0.1,
                chunk_size=512,
                system_prompt=system_prompt,
                use_bedrock=True
            )
            
            self.assertIsNotNone(index, "Enhanced RAG index creation with fallback failed")
            
            # Create chat engine
            chat_engine = index.as_chat_engine(chat_mode="context", similarity_top_k=7)
            self.assertIsNotNone(chat_engine, "Chat engine creation with fallback failed")
            
            print("  Successfully created chat engine with fallback")
            
        except Exception as e:
            self.fail(f"Main application hybrid mode fallback test failed: {str(e)}")
    
    def test_main_application_bedrock_only_error_handling(self):
        """Test main application error handling for Bedrock-only mode"""
        print("Testing main application error handling for Bedrock-only mode...")
        
        try:
            # Create mock KnowledgeBase config (Bedrock-only, should fail)
            mock_kb_config = KnowledgeBaseConfig(
                knowledge_base_id="MOCK123456",
                region="us-east-1",
                mode="bedrock",
                enable_fallback=False,
                similarity_top_k=5
            )
            
            print("  Testing Bedrock-only mode with invalid config...")
            
            # This should raise an error since we don't have a real KnowledgeBase
            with self.assertRaises(Exception) as context:
                enhanced_rag_load(
                    database_folder=None,
                    knowledge_base_config=mock_kb_config,
                    temperature=0.1,
                    chunk_size=512,
                    use_bedrock=True
                )
            
            # Verify that the error is related to KnowledgeBase initialization
            error_message = str(context.exception)
            self.assertTrue(
                any(keyword in error_message for keyword in ["認証", "初期化", "AWS", "KnowledgeBase"]),
                f"Expected KnowledgeBase-related error, got: {error_message}"
            )
            
            print("  Successfully handled Bedrock-only mode error")
            
        except Exception as e:
            self.fail(f"Main application Bedrock-only error handling test failed: {str(e)}")
    
    def test_main_application_no_sources_error(self):
        """Test main application error handling when no sources are provided"""
        print("Testing main application error handling for no sources...")
        
        try:
            # Test with no database folder and no KnowledgeBase config
            with self.assertRaises(ValueError) as context:
                enhanced_rag_load(
                    database_folder=None,
                    knowledge_base_config=None
                )
            
            # Verify error message
            error_message = str(context.exception)
            self.assertIn("少なくとも", error_message, f"Expected 'no sources' error message, got: {error_message}")
            
            print("  Successfully handled no sources error")
            
        except Exception as e:
            self.fail(f"Main application no sources error handling test failed: {str(e)}")
    
    @patch('streamlit.session_state')
    def test_main_application_session_state_integration(self, mock_st_session_state):
        """Test main application integration with session state"""
        print("Testing main application session state integration...")
        
        if not self.existing_paths:
            self.skipTest("No knowledge base directories available")
        
        try:
            # Mock session state with KnowledgeBase settings
            mock_st_session_state.kb_mode = 'hybrid'
            mock_st_session_state.kb_id = 'MOCK123456'
            mock_st_session_state.kb_region = 'us-east-1'
            mock_st_session_state.similarity_top_k = 5
            mock_st_session_state.confidence_threshold = 0.0
            
            # Simulate main.py logic for KnowledgeBase config initialization
            kb_config = None
            if hasattr(mock_st_session_state, 'kb_mode') and mock_st_session_state.kb_mode in ['bedrock', 'hybrid']:
                if hasattr(mock_st_session_state, 'kb_id') and mock_st_session_state.kb_id:
                    kb_config = KnowledgeBaseConfig(
                        knowledge_base_id=mock_st_session_state.kb_id,
                        region=getattr(mock_st_session_state, 'kb_region', 'us-east-1'),
                        similarity_top_k=getattr(mock_st_session_state, 'similarity_top_k', 5),
                        confidence_threshold=getattr(mock_st_session_state, 'confidence_threshold', 0.0),
                        mode=mock_st_session_state.kb_mode
                    )
            
            self.assertIsNotNone(kb_config, "KnowledgeBase config should be created from session state")
            self.assertEqual(kb_config.knowledge_base_id, 'MOCK123456')
            self.assertEqual(kb_config.mode, 'hybrid')
            
            # Test enhanced_rag_load with session state config (should fallback to local)
            kb_path = self.existing_paths[0]
            
            try:
                with open('core/knowledge/prompts/prompt.txt', 'r') as file:
                    system_prompt = file.read()
            except FileNotFoundError:
                system_prompt = "You are a helpful assistant specializing in power electronics."
            
            index = enhanced_rag_load(
                database_folder=kb_path,
                knowledge_base_config=kb_config,
                temperature=0.1,
                chunk_size=512,
                system_prompt=system_prompt,
                use_bedrock=True
            )
            
            self.assertIsNotNone(index, "Enhanced RAG index creation with session state config failed")
            
            print("  Successfully integrated with session state")
            
        except Exception as e:
            self.fail(f"Main application session state integration test failed: {str(e)}")
    
    def test_main_application_backward_compatibility(self):
        """Test that main application maintains backward compatibility"""
        print("Testing main application backward compatibility...")
        
        if not self.existing_paths:
            self.skipTest("No knowledge base directories available")
        
        try:
            # Test that enhanced_rag_load works exactly like rag_load when no kb_config is provided
            from core.llm.llm import rag_load
            
            kb_path = self.existing_paths[0]
            
            try:
                with open('core/knowledge/prompts/prompt.txt', 'r') as file:
                    system_prompt = file.read()
            except FileNotFoundError:
                system_prompt = "You are a helpful assistant specializing in power electronics."
            
            # Create index with enhanced_rag_load (no kb_config)
            enhanced_index = enhanced_rag_load(
                database_folder=kb_path,
                knowledge_base_config=None,
                temperature=0.1,
                chunk_size=512,
                system_prompt=system_prompt,
                use_bedrock=True
            )
            
            # Create index with original rag_load
            original_index = rag_load(
                database_folder=kb_path,
                temperature=0.1,
                chunk_size=512,
                system_prompt=system_prompt,
                use_bedrock=True
            )
            
            # Both should be created successfully
            self.assertIsNotNone(enhanced_index, "Enhanced RAG index creation failed")
            self.assertIsNotNone(original_index, "Original RAG index creation failed")
            
            # Both should support the same interface
            enhanced_chat_engine = enhanced_index.as_chat_engine(similarity_top_k=5)
            original_chat_engine = original_index.as_chat_engine(similarity_top_k=5)
            
            self.assertIsNotNone(enhanced_chat_engine, "Enhanced chat engine creation failed")
            self.assertIsNotNone(original_chat_engine, "Original chat engine creation failed")
            
            print("  Successfully maintained backward compatibility")
            
        except Exception as e:
            self.fail(f"Main application backward compatibility test failed: {str(e)}")
    
    def test_main_application_multiple_modes(self):
        """Test main application with different modes"""
        print("Testing main application with different modes...")
        
        if not self.existing_paths:
            self.skipTest("No knowledge base directories available")
        
        try:
            modes_to_test = [
                ('local', None),
                ('hybrid', KnowledgeBaseConfig(
                    knowledge_base_id="MOCK123456",
                    region="us-east-1",
                    mode="hybrid",
                    enable_fallback=True
                ))
            ]
            
            for mode_name, kb_config in modes_to_test:
                print(f"  Testing mode: {mode_name}")
                
                kb_path = self.existing_paths[0]
                
                try:
                    with open('core/knowledge/prompts/prompt.txt', 'r') as file:
                        system_prompt = file.read()
                except FileNotFoundError:
                    system_prompt = "You are a helpful assistant specializing in power electronics."
                
                # Create index for this mode
                index = enhanced_rag_load(
                    database_folder=kb_path,
                    knowledge_base_config=kb_config,
                    temperature=0.1,
                    chunk_size=512,
                    system_prompt=system_prompt,
                    use_bedrock=True
                )
                
                self.assertIsNotNone(index, f"Index creation failed for mode: {mode_name}")
                
                # Create chat engine
                chat_engine = index.as_chat_engine(similarity_top_k=5)
                self.assertIsNotNone(chat_engine, f"Chat engine creation failed for mode: {mode_name}")
                
                print(f"    Mode {mode_name}: ✅ Success")
            
            print("  Successfully tested multiple modes")
            
        except Exception as e:
            self.fail(f"Main application multiple modes test failed: {str(e)}")


def run_main_integration_tests():
    """Run the main application integration tests"""
    print("🧪 Starting Main Application Integration Tests")
    print("=" * 60)
    
    # Check if running in correct directory
    if not os.path.exists("main.py") or not os.path.exists("core/llm/llm.py"):
        print("❌ Error: Please run this script from the PE-GPT root directory")
        return False
    
    # Create test suite
    suite = unittest.TestLoader().loadTestsFromTestCase(MainApplicationIntegrationTest)
    
    # Run tests with detailed output
    runner = unittest.TextTestRunner(verbosity=2, stream=sys.stdout)
    result = runner.run(suite)
    
    # Generate summary
    print("=" * 60)
    print("🏁 Main Application Integration Test Summary")
    print("=" * 60)
    
    total_tests = result.testsRun
    failed_tests = len(result.failures) + len(result.errors)
    passed_tests = total_tests - failed_tests
    
    print(f"Total Tests: {total_tests}")
    print(f"Passed: {passed_tests} ✅")
    print(f"Failed: {failed_tests} ❌")
    print(f"Success Rate: {(passed_tests/total_tests*100):.1f}%" if total_tests > 0 else "0%")
    
    # Show failures and errors
    if result.failures:
        print("\n❌ Failures:")
        for test, traceback in result.failures:
            print(f"  - {test}: {traceback}")
    
    if result.errors:
        print("\n💥 Errors:")
        for test, traceback in result.errors:
            print(f"  - {test}: {traceback}")
    
    # Overall assessment
    overall_success = failed_tests == 0
    print(f"\n🎯 Overall Assessment: {'✅ ALL TESTS PASSED' if overall_success else '❌ SOME TESTS FAILED'}")
    
    # Save results
    results = {
        "overall_success": overall_success,
        "total_tests": total_tests,
        "passed_tests": passed_tests,
        "failed_tests": failed_tests,
        "success_rate": (passed_tests/total_tests*100) if total_tests > 0 else 0,
        "failures": [str(test) for test, _ in result.failures],
        "errors": [str(test) for test, _ in result.errors]
    }
    
    try:
        with open("tests/main_integration_test_results.json", 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        print(f"\n💾 Test results saved to: tests/main_integration_test_results.json")
    except Exception as e:
        print(f"\n⚠️ Could not save results to file: {e}")
    
    return overall_success


if __name__ == "__main__":
    success = run_main_integration_tests()
    sys.exit(0 if success else 1)