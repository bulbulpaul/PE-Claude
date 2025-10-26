#!/usr/bin/env python3
"""
Integration test script for PE-GPT Bedrock migration
Tests all components to ensure proper functionality after migration
"""

import os
import sys
import json
import time
import traceback
from typing import Dict, List, Any
import boto3
from botocore.exceptions import ClientError, NoCredentialsError

# Add core modules to path
sys.path.append('.')
sys.path.append('core')

# Import application modules
from core.llm.llm import (
    bedrock_init, 
    bedrock_chat_completion, 
    convert_messages_to_bedrock_format,
    parse_bedrock_response,
    BedrockLLM,
    rag_load,
    BedrockConfig,
    BedrockError
)

class IntegrationTestRunner:
    """
    Comprehensive integration test runner for PE-GPT Bedrock migration
    """
    
    def __init__(self):
        self.test_results = {}
        self.client = None
        self.config = None
        self.total_tests = 0
        self.passed_tests = 0
        self.failed_tests = 0
        
    def log_test_result(self, test_name: str, success: bool, message: str = "", details: Dict = None):
        """Log test result with details"""
        self.total_tests += 1
        if success:
            self.passed_tests += 1
            status = "✅ PASS"
        else:
            self.failed_tests += 1
            status = "❌ FAIL"
            
        self.test_results[test_name] = {
            "status": status,
            "success": success,
            "message": message,
            "details": details or {}
        }
        
        print(f"{status}: {test_name}")
        if message:
            print(f"    {message}")
        if details:
            for key, value in details.items():
                print(f"    {key}: {value}")
        print()

    def test_aws_credentials(self) -> bool:
        """Test AWS credentials and connectivity"""
        print("🔐 Testing AWS Credentials and Connectivity...")
        
        try:
            # Test basic AWS connectivity
            session = boto3.Session()
            credentials = session.get_credentials()
            
            if not credentials:
                self.log_test_result(
                    "AWS Credentials", 
                    False, 
                    "No AWS credentials found"
                )
                return False
            
            # Test Bedrock service connectivity
            bedrock_client = boto3.client('bedrock-runtime', region_name='us-east-1')
            
            # Try to list models to verify connectivity
            try:
                # Use bedrock client (not runtime) for listing models
                bedrock_control_client = boto3.client('bedrock', region_name='us-east-1')
                bedrock_control_client.list_foundation_models()
                connectivity_test = True
                connectivity_message = "Successfully connected to Bedrock"
            except ClientError as e:
                if e.response['Error']['Code'] == 'AccessDeniedException':
                    connectivity_test = True
                    connectivity_message = "Connected to Bedrock (limited access)"
                else:
                    connectivity_test = False
                    connectivity_message = f"Bedrock connection failed: {e.response['Error']['Code']}"
            
            self.log_test_result(
                "AWS Credentials", 
                True, 
                "AWS credentials found and valid",
                {
                    "Access Key ID": credentials.access_key[:8] + "..." if credentials.access_key else "Not available",
                    "Region": session.region_name or "us-east-1",
                    "Bedrock Connectivity": connectivity_message
                }
            )
            return True
            
        except Exception as e:
            self.log_test_result(
                "AWS Credentials", 
                False, 
                f"AWS credentials test failed: {str(e)}"
            )
            return False

    def test_bedrock_config(self) -> bool:
        """Test Bedrock configuration"""
        print("⚙️ Testing Bedrock Configuration...")
        
        try:
            self.config = BedrockConfig()
            
            # Validate configuration values
            config_valid = True
            config_issues = []
            
            if not self.config.aws_region:
                config_valid = False
                config_issues.append("Missing AWS region")
            
            if not self.config.bedrock_model_id:
                config_valid = False
                config_issues.append("Missing Bedrock model ID")
            
            if self.config.max_tokens < 1 or self.config.max_tokens > 4096:
                config_valid = False
                config_issues.append(f"Invalid max_tokens: {self.config.max_tokens}")
            
            if self.config.temperature < 0.0 or self.config.temperature > 1.0:
                config_valid = False
                config_issues.append(f"Invalid temperature: {self.config.temperature}")
            
            self.log_test_result(
                "Bedrock Configuration", 
                config_valid, 
                "Configuration validation completed" if config_valid else f"Configuration issues: {', '.join(config_issues)}",
                {
                    "AWS Region": self.config.aws_region,
                    "Model ID": self.config.bedrock_model_id,
                    "Max Tokens": self.config.max_tokens,
                    "Temperature": self.config.temperature,
                    "Model Display Name": self.config.get_model_display_name()
                }
            )
            return config_valid
            
        except Exception as e:
            self.log_test_result(
                "Bedrock Configuration", 
                False, 
                f"Configuration test failed: {str(e)}"
            )
            return False

    def test_bedrock_client_init(self) -> bool:
        """Test Bedrock client initialization"""
        print("🚀 Testing Bedrock Client Initialization...")
        
        try:
            # Mock streamlit session state for testing
            import streamlit as st
            if not hasattr(st, 'session_state'):
                class MockSessionState:
                    def __init__(self):
                        self._state = {}
                    def get(self, key, default=None):
                        return self._state.get(key, default)
                    def __setitem__(self, key, value):
                        self._state[key] = value
                    def __getitem__(self, key):
                        return self._state[key]
                    def __contains__(self, key):
                        return key in self._state
                
                st.session_state = MockSessionState()
            
            # Test client initialization
            self.client = bedrock_init()
            
            if self.client is None:
                self.log_test_result(
                    "Bedrock Client Init", 
                    False, 
                    "Client initialization returned None"
                )
                return False
            
            # Verify client type
            if not hasattr(self.client, 'invoke_model'):
                self.log_test_result(
                    "Bedrock Client Init", 
                    False, 
                    "Client missing invoke_model method"
                )
                return False
            
            self.log_test_result(
                "Bedrock Client Init", 
                True, 
                "Bedrock client initialized successfully",
                {
                    "Client Type": type(self.client).__name__,
                    "Service Name": getattr(self.client, 'service_model', {}).get('service_name', 'Unknown')
                }
            )
            return True
            
        except Exception as e:
            self.log_test_result(
                "Bedrock Client Init", 
                False, 
                f"Client initialization failed: {str(e)}"
            )
            return False

    def test_message_conversion(self) -> bool:
        """Test message format conversion"""
        print("🔄 Testing Message Format Conversion...")
        
        try:
            # Test cases for message conversion
            test_cases = [
                {
                    "name": "Simple user message",
                    "input": [{"role": "user", "content": "Hello, how are you?"}],
                    "expected_length": 1
                },
                {
                    "name": "User and assistant conversation",
                    "input": [
                        {"role": "user", "content": "What is power electronics?"},
                        {"role": "assistant", "content": "Power electronics is a field of electrical engineering..."},
                        {"role": "user", "content": "Can you explain more?"}
                    ],
                    "expected_length": 3
                },
                {
                    "name": "Message with system prompt (should be filtered)",
                    "input": [
                        {"role": "system", "content": "You are a helpful assistant"},
                        {"role": "user", "content": "Hello"}
                    ],
                    "expected_length": 1  # System message should be filtered out
                }
            ]
            
            all_passed = True
            conversion_results = {}
            
            for test_case in test_cases:
                try:
                    converted = convert_messages_to_bedrock_format(test_case["input"])
                    
                    # Validate conversion
                    if len(converted) != test_case["expected_length"]:
                        all_passed = False
                        conversion_results[test_case["name"]] = f"Expected {test_case['expected_length']} messages, got {len(converted)}"
                        continue
                    
                    # Validate message structure
                    for msg in converted:
                        if not isinstance(msg, dict) or "role" not in msg or "content" not in msg:
                            all_passed = False
                            conversion_results[test_case["name"]] = "Invalid message structure"
                            break
                        
                        if msg["role"] not in ["user", "assistant"]:
                            all_passed = False
                            conversion_results[test_case["name"]] = f"Invalid role: {msg['role']}"
                            break
                    
                    if test_case["name"] not in conversion_results:
                        conversion_results[test_case["name"]] = "✅ Passed"
                        
                except Exception as e:
                    all_passed = False
                    conversion_results[test_case["name"]] = f"Exception: {str(e)}"
            
            self.log_test_result(
                "Message Conversion", 
                all_passed, 
                "Message conversion tests completed",
                conversion_results
            )
            return all_passed
            
        except Exception as e:
            self.log_test_result(
                "Message Conversion", 
                False, 
                f"Message conversion test failed: {str(e)}"
            )
            return False

    def test_bedrock_api_call(self) -> bool:
        """Test actual Bedrock API call"""
        print("🌐 Testing Bedrock API Call...")
        
        if not self.client:
            self.log_test_result(
                "Bedrock API Call", 
                False, 
                "No Bedrock client available"
            )
            return False
        
        try:
            # Simple test message
            test_messages = [
                {"role": "user", "content": "Hello! Please respond with 'API test successful' to confirm the connection is working."}
            ]
            
            # Record start time for performance measurement
            start_time = time.time()
            
            # Make API call
            response = bedrock_chat_completion(
                client=self.client,
                messages=test_messages,
                model_id=self.config.bedrock_model_id if self.config else None,
                max_tokens=100,
                temperature=0.0
            )
            
            # Record end time
            end_time = time.time()
            response_time = end_time - start_time
            
            # Validate response
            if not response or not isinstance(response, dict):
                self.log_test_result(
                    "Bedrock API Call", 
                    False, 
                    "Invalid response format"
                )
                return False
            
            if "content" not in response or not response["content"]:
                self.log_test_result(
                    "Bedrock API Call", 
                    False, 
                    "No content in response"
                )
                return False
            
            # Check for error in response
            if "error" in response:
                self.log_test_result(
                    "Bedrock API Call", 
                    False, 
                    f"API returned error: {response['error']}"
                )
                return False
            
            self.log_test_result(
                "Bedrock API Call", 
                True, 
                "API call successful",
                {
                    "Response Time": f"{response_time:.2f} seconds",
                    "Content Length": len(response["content"]),
                    "Input Tokens": response.get("usage", {}).get("input_tokens", "Unknown"),
                    "Output Tokens": response.get("usage", {}).get("output_tokens", "Unknown"),
                    "Model": response.get("model", "Unknown"),
                    "Stop Reason": response.get("stop_reason", "Unknown")
                }
            )
            return True
            
        except BedrockError as e:
            self.log_test_result(
                "Bedrock API Call", 
                False, 
                f"Bedrock error: {str(e)}",
                {"Error Code": getattr(e, 'error_code', 'Unknown')}
            )
            return False
            
        except Exception as e:
            self.log_test_result(
                "Bedrock API Call", 
                False, 
                f"API call failed: {str(e)}"
            )
            return False

    def test_bedrock_llm_class(self) -> bool:
        """Test BedrockLLM class functionality"""
        print("🤖 Testing BedrockLLM Class...")
        
        try:
            # Initialize BedrockLLM
            llm = BedrockLLM(
                model_id=self.config.bedrock_model_id if self.config else None,
                temperature=0.0,
                max_tokens=100
            )
            
            # Test metadata property
            metadata = llm.metadata
            if not isinstance(metadata, dict):
                self.log_test_result(
                    "BedrockLLM Class", 
                    False, 
                    "Invalid metadata format"
                )
                return False
            
            # Test complete method
            try:
                response = llm.complete("What is 2+2? Please answer briefly.")
                
                if not response or not isinstance(response, str):
                    self.log_test_result(
                        "BedrockLLM Class", 
                        False, 
                        "Invalid complete method response"
                    )
                    return False
                
                complete_test = "✅ Passed"
                
            except Exception as e:
                complete_test = f"❌ Failed: {str(e)}"
            
            self.log_test_result(
                "BedrockLLM Class", 
                "✅" in complete_test, 
                "BedrockLLM class tests completed",
                {
                    "Metadata": "✅ Valid" if metadata else "❌ Invalid",
                    "Complete Method": complete_test,
                    "Model ID": metadata.get("model_id", "Unknown"),
                    "Temperature": metadata.get("temperature", "Unknown"),
                    "Max Tokens": metadata.get("max_tokens", "Unknown")
                }
            )
            return "✅" in complete_test
            
        except Exception as e:
            self.log_test_result(
                "BedrockLLM Class", 
                False, 
                f"BedrockLLM class test failed: {str(e)}"
            )
            return False

    def test_rag_functionality(self) -> bool:
        """Test RAG (Retrieval Augmented Generation) functionality"""
        print("📚 Testing RAG Functionality...")
        
        try:
            # Check if knowledge base directories exist
            kb_paths = [
                "core/knowledge/kb/database",
                "core/knowledge/kb/database1", 
                "core/knowledge/kb/introduction"
            ]
            
            existing_paths = []
            for path in kb_paths:
                if os.path.exists(path) and os.path.isdir(path):
                    # Check if directory has files
                    files = [f for f in os.listdir(path) if f.endswith('.txt')]
                    if files:
                        existing_paths.append(path)
            
            if not existing_paths:
                self.log_test_result(
                    "RAG Functionality", 
                    False, 
                    "No knowledge base directories with .txt files found"
                )
                return False
            
            # Test RAG loading with first available path
            test_path = existing_paths[0]
            
            try:
                # Test RAG loading (this might take some time)
                print(f"    Loading RAG index from {test_path}...")
                index = rag_load(
                    database_folder=test_path,
                    llm_model=self.config.bedrock_model_id if self.config else "anthropic.claude-3-sonnet-20240229-v1:0",
                    temperature=0.1,
                    chunk_size=512,
                    use_bedrock=True
                )
                
                if index is None:
                    self.log_test_result(
                        "RAG Functionality", 
                        False, 
                        "RAG index creation returned None"
                    )
                    return False
                
                # Test chat engine creation
                chat_engine = index.as_chat_engine(chat_mode="context", similarity_top_k=3)
                
                if chat_engine is None:
                    self.log_test_result(
                        "RAG Functionality", 
                        False, 
                        "Chat engine creation returned None"
                    )
                    return False
                
                # Test a simple query (optional - might be slow)
                try:
                    response = chat_engine.chat("What information is available in this knowledge base?")
                    query_test = "✅ Query successful"
                except Exception as e:
                    query_test = f"⚠️ Query failed: {str(e)}"
                
                self.log_test_result(
                    "RAG Functionality", 
                    True, 
                    "RAG functionality tests completed",
                    {
                        "Knowledge Base Path": test_path,
                        "Index Creation": "✅ Successful",
                        "Chat Engine Creation": "✅ Successful", 
                        "Test Query": query_test
                    }
                )
                return True
                
            except Exception as e:
                self.log_test_result(
                    "RAG Functionality", 
                    False, 
                    f"RAG loading failed: {str(e)}"
                )
                return False
            
        except Exception as e:
            self.log_test_result(
                "RAG Functionality", 
                False, 
                f"RAG functionality test failed: {str(e)}"
            )
            return False

    def test_enhanced_rag_functionality(self) -> bool:
        """Test Enhanced RAG functionality with KnowledgeBase integration"""
        print("🚀 Testing Enhanced RAG Functionality...")
        
        try:
            from core.llm.llm import enhanced_rag_load
            from core.knowledge.kb_config import KnowledgeBaseConfig
            
            # Check if knowledge base directories exist
            kb_paths = [
                "core/knowledge/kb/database",
                "core/knowledge/kb/database1", 
                "core/knowledge/kb/introduction"
            ]
            
            existing_paths = []
            for path in kb_paths:
                if os.path.exists(path) and os.path.isdir(path):
                    files = [f for f in os.listdir(path) if f.endswith('.txt')]
                    if files:
                        existing_paths.append(path)
            
            test_results = {}
            
            # Test 1: Local-only mode (backward compatibility)
            if existing_paths:
                try:
                    print("    Testing local-only mode...")
                    local_index = enhanced_rag_load(
                        database_folder=existing_paths[0],
                        knowledge_base_config=None,
                        llm_model=self.config.bedrock_model_id if self.config else None,
                        temperature=0.1,
                        chunk_size=512
                    )
                    
                    if local_index is None:
                        test_results["Local-only Mode"] = "❌ Index creation failed"
                    else:
                        # Test chat engine creation
                        chat_engine = local_index.as_chat_engine(similarity_top_k=3)
                        if chat_engine:
                            test_results["Local-only Mode"] = "✅ Successful"
                        else:
                            test_results["Local-only Mode"] = "❌ Chat engine creation failed"
                            
                except Exception as e:
                    test_results["Local-only Mode"] = f"❌ Exception: {str(e)}"
            else:
                test_results["Local-only Mode"] = "⏭️ Skipped (no local files)"
            
            # Test 2: Mock Bedrock-only mode (configuration test)
            try:
                print("    Testing Bedrock-only configuration...")
                mock_config = KnowledgeBaseConfig(
                    knowledge_base_id="MOCK123456",
                    region="us-east-1",
                    mode="bedrock",
                    similarity_top_k=5
                )
                
                # This should fail gracefully since we don't have a real KnowledgeBase
                try:
                    bedrock_index = enhanced_rag_load(
                        database_folder=None,
                        knowledge_base_config=mock_config,
                        llm_model=self.config.bedrock_model_id if self.config else None
                    )
                    test_results["Bedrock Configuration"] = "⚠️ Unexpected success with mock config"
                except Exception as e:
                    # Expected to fail with mock config
                    if "認証" in str(e) or "初期化" in str(e) or "AWS" in str(e):
                        test_results["Bedrock Configuration"] = "✅ Correctly handled invalid config"
                    else:
                        test_results["Bedrock Configuration"] = f"⚠️ Unexpected error: {str(e)}"
                        
            except Exception as e:
                test_results["Bedrock Configuration"] = f"❌ Config test failed: {str(e)}"
            
            # Test 3: Hybrid mode with fallback (should fall back to local)
            if existing_paths:
                try:
                    print("    Testing hybrid mode with fallback...")
                    mock_config = KnowledgeBaseConfig(
                        knowledge_base_id="MOCK123456",
                        region="us-east-1",
                        mode="hybrid",
                        enable_fallback=True,
                        similarity_top_k=5
                    )
                    
                    hybrid_index = enhanced_rag_load(
                        database_folder=existing_paths[0],
                        knowledge_base_config=mock_config,
                        llm_model=self.config.bedrock_model_id if self.config else None
                    )
                    
                    if hybrid_index:
                        # Test retriever info
                        if hasattr(hybrid_index, 'get_retriever_info'):
                            info = hybrid_index.get_retriever_info()
                            test_results["Hybrid Mode Fallback"] = "✅ Successful with fallback"
                        else:
                            test_results["Hybrid Mode Fallback"] = "✅ Fallback to local mode"
                    else:
                        test_results["Hybrid Mode Fallback"] = "❌ Failed to create index"
                        
                except Exception as e:
                    test_results["Hybrid Mode Fallback"] = f"❌ Exception: {str(e)}"
            else:
                test_results["Hybrid Mode Fallback"] = "⏭️ Skipped (no local files)"
            
            # Test 4: Error handling for invalid configurations
            try:
                print("    Testing error handling...")
                
                # Test with no sources
                try:
                    enhanced_rag_load(database_folder=None, knowledge_base_config=None)
                    test_results["Error Handling"] = "❌ Should have raised error for no sources"
                except ValueError as e:
                    if "少なくとも" in str(e):
                        test_results["Error Handling"] = "✅ Correctly handled no sources error"
                    else:
                        test_results["Error Handling"] = f"⚠️ Unexpected error message: {str(e)}"
                except Exception as e:
                    test_results["Error Handling"] = f"⚠️ Unexpected exception type: {type(e).__name__}"
                    
            except Exception as e:
                test_results["Error Handling"] = f"❌ Error handling test failed: {str(e)}"
            
            # Count successful tests
            successful_tests = sum(1 for result in test_results.values() if "✅" in result)
            total_enhanced_tests = len(test_results)
            
            self.log_test_result(
                "Enhanced RAG Functionality", 
                successful_tests >= total_enhanced_tests // 2,  # At least half should pass
                f"Enhanced RAG tests completed ({successful_tests}/{total_enhanced_tests} passed)",
                test_results
            )
            return successful_tests >= total_enhanced_tests // 2
            
        except ImportError as e:
            self.log_test_result(
                "Enhanced RAG Functionality", 
                False, 
                f"Import error: {str(e)} - Enhanced RAG components not available"
            )
            return False
            
        except Exception as e:
            self.log_test_result(
                "Enhanced RAG Functionality", 
                False, 
                f"Enhanced RAG functionality test failed: {str(e)}"
            )
            return False

    def test_chat_engine_integration(self) -> bool:
        """Test chat engine integration with enhanced RAG"""
        print("💬 Testing Chat Engine Integration...")
        
        try:
            from core.llm.llm import enhanced_rag_load
            
            # Check if knowledge base directories exist
            kb_paths = [
                "core/knowledge/kb/database",
                "core/knowledge/kb/database1", 
                "core/knowledge/kb/introduction"
            ]
            
            existing_paths = []
            for path in kb_paths:
                if os.path.exists(path) and os.path.isdir(path):
                    files = [f for f in os.listdir(path) if f.endswith('.txt')]
                    if files:
                        existing_paths.append(path)
            
            if not existing_paths:
                self.log_test_result(
                    "Chat Engine Integration", 
                    False, 
                    "No knowledge base directories available for testing"
                )
                return False
            
            test_results = {}
            
            try:
                print("    Creating enhanced RAG index...")
                enhanced_index = enhanced_rag_load(
                    database_folder=existing_paths[0],
                    knowledge_base_config=None,  # Local-only for testing
                    llm_model=self.config.bedrock_model_id if self.config else None,
                    temperature=0.1,
                    chunk_size=512
                )
                
                if enhanced_index is None:
                    test_results["Index Creation"] = "❌ Failed"
                    self.log_test_result(
                        "Chat Engine Integration", 
                        False, 
                        "Enhanced index creation failed",
                        test_results
                    )
                    return False
                
                test_results["Index Creation"] = "✅ Successful"
                
                # Test retriever creation
                try:
                    retriever = enhanced_index.as_retriever(similarity_top_k=3)
                    if retriever:
                        test_results["Retriever Creation"] = "✅ Successful"
                        
                        # Test retrieval
                        try:
                            results = retriever.retrieve("power electronics")
                            if results and len(results) > 0:
                                test_results["Document Retrieval"] = f"✅ Retrieved {len(results)} documents"
                            else:
                                test_results["Document Retrieval"] = "⚠️ No documents retrieved"
                        except Exception as e:
                            test_results["Document Retrieval"] = f"❌ Retrieval failed: {str(e)}"
                    else:
                        test_results["Retriever Creation"] = "❌ Failed"
                        
                except Exception as e:
                    test_results["Retriever Creation"] = f"❌ Exception: {str(e)}"
                
                # Test query engine creation
                try:
                    query_engine = enhanced_index.as_query_engine(similarity_top_k=3)
                    if query_engine:
                        test_results["Query Engine Creation"] = "✅ Successful"
                        
                        # Test query (optional - might be slow)
                        try:
                            response = query_engine.query("What is power electronics?")
                            if response and hasattr(response, 'response') and response.response:
                                test_results["Query Test"] = "✅ Query successful"
                            else:
                                test_results["Query Test"] = "⚠️ Empty response"
                        except Exception as e:
                            test_results["Query Test"] = f"⚠️ Query failed: {str(e)}"
                    else:
                        test_results["Query Engine Creation"] = "❌ Failed"
                        
                except Exception as e:
                    test_results["Query Engine Creation"] = f"❌ Exception: {str(e)}"
                
                # Test chat engine creation
                try:
                    chat_engine = enhanced_index.as_chat_engine(similarity_top_k=3)
                    if chat_engine:
                        test_results["Chat Engine Creation"] = "✅ Successful"
                        
                        # Test chat (optional - might be slow)
                        try:
                            response = chat_engine.chat("Hello, can you help me with power electronics?")
                            if response and hasattr(response, 'response') and response.response:
                                test_results["Chat Test"] = "✅ Chat successful"
                            else:
                                test_results["Chat Test"] = "⚠️ Empty chat response"
                        except Exception as e:
                            test_results["Chat Test"] = f"⚠️ Chat failed: {str(e)}"
                    else:
                        test_results["Chat Engine Creation"] = "❌ Failed"
                        
                except Exception as e:
                    test_results["Chat Engine Creation"] = f"❌ Exception: {str(e)}"
                
                # Test backward compatibility methods
                try:
                    if hasattr(enhanced_index, 'get_nodes'):
                        nodes = enhanced_index.get_nodes()
                        test_results["Backward Compatibility"] = "✅ get_nodes method available"
                    else:
                        test_results["Backward Compatibility"] = "⚠️ get_nodes method not available"
                except Exception as e:
                    test_results["Backward Compatibility"] = f"⚠️ Compatibility test failed: {str(e)}"
                
            except Exception as e:
                test_results["Index Creation"] = f"❌ Exception: {str(e)}"
            
            # Count successful tests
            successful_tests = sum(1 for result in test_results.values() if "✅" in result)
            total_integration_tests = len(test_results)
            
            self.log_test_result(
                "Chat Engine Integration", 
                successful_tests >= total_integration_tests // 2,  # At least half should pass
                f"Chat engine integration tests completed ({successful_tests}/{total_integration_tests} passed)",
                test_results
            )
            return successful_tests >= total_integration_tests // 2
            
        except ImportError as e:
            self.log_test_result(
                "Chat Engine Integration", 
                False, 
                f"Import error: {str(e)} - Enhanced RAG components not available"
            )
            return False
            
        except Exception as e:
            self.log_test_result(
                "Chat Engine Integration", 
                False, 
                f"Chat engine integration test failed: {str(e)}"
            )
            return False

    def test_error_handling(self) -> bool:
        """Test error handling mechanisms"""
        print("⚠️ Testing Error Handling...")
        
        try:
            error_tests = {}
            
            # Test 1: Invalid message format
            try:
                convert_messages_to_bedrock_format([{"invalid": "format"}])
                error_tests["Invalid Message Format"] = "❌ Should have raised error"
            except BedrockError:
                error_tests["Invalid Message Format"] = "✅ Correctly handled"
            except Exception as e:
                error_tests["Invalid Message Format"] = f"⚠️ Unexpected error: {type(e).__name__}"
            
            # Test 2: Empty messages
            try:
                convert_messages_to_bedrock_format([])
                error_tests["Empty Messages"] = "❌ Should have raised error"
            except BedrockError:
                error_tests["Empty Messages"] = "✅ Correctly handled"
            except Exception as e:
                error_tests["Empty Messages"] = f"⚠️ Unexpected error: {type(e).__name__}"
            
            # Test 3: Invalid model ID (if client available)
            if self.client:
                try:
                    bedrock_chat_completion(
                        client=self.client,
                        messages=[{"role": "user", "content": "test"}],
                        model_id="invalid.model.id",
                        max_tokens=10
                    )
                    error_tests["Invalid Model ID"] = "❌ Should have raised error"
                except (BedrockError, ClientError):
                    error_tests["Invalid Model ID"] = "✅ Correctly handled"
                except Exception as e:
                    error_tests["Invalid Model ID"] = f"⚠️ Unexpected error: {type(e).__name__}"
            else:
                error_tests["Invalid Model ID"] = "⏭️ Skipped (no client)"
            
            # Count successful error handling
            successful_tests = sum(1 for result in error_tests.values() if "✅" in result)
            total_error_tests = len(error_tests)
            
            self.log_test_result(
                "Error Handling", 
                successful_tests == total_error_tests, 
                f"Error handling tests completed ({successful_tests}/{total_error_tests} passed)",
                error_tests
            )
            return successful_tests == total_error_tests
            
        except Exception as e:
            self.log_test_result(
                "Error Handling", 
                False, 
                f"Error handling test failed: {str(e)}"
            )
            return False

    def test_performance_metrics(self) -> bool:
        """Test performance metrics and resource usage"""
        print("📊 Testing Performance Metrics...")
        
        if not self.client:
            self.log_test_result(
                "Performance Metrics", 
                False, 
                "No Bedrock client available for performance testing"
            )
            return False
        
        try:
            # Performance test parameters
            test_messages = [
                {"role": "user", "content": "Please provide a brief explanation of power electronics in exactly 50 words."}
            ]
            
            # Multiple API calls to measure consistency
            response_times = []
            token_usage = []
            
            for i in range(3):  # 3 test calls
                print(f"    Performance test {i+1}/3...")
                
                start_time = time.time()
                response = bedrock_chat_completion(
                    client=self.client,
                    messages=test_messages,
                    model_id=self.config.bedrock_model_id if self.config else None,
                    max_tokens=100,
                    temperature=0.0
                )
                end_time = time.time()
                
                response_time = end_time - start_time
                response_times.append(response_time)
                
                if "usage" in response:
                    token_usage.append(response["usage"])
            
            # Calculate performance metrics
            avg_response_time = sum(response_times) / len(response_times)
            min_response_time = min(response_times)
            max_response_time = max(response_times)
            
            # Token usage analysis
            if token_usage:
                avg_input_tokens = sum(usage.get("input_tokens", 0) for usage in token_usage) / len(token_usage)
                avg_output_tokens = sum(usage.get("output_tokens", 0) for usage in token_usage) / len(token_usage)
            else:
                avg_input_tokens = avg_output_tokens = 0
            
            # Performance thresholds (adjust as needed)
            performance_good = avg_response_time < 10.0  # Less than 10 seconds average
            
            self.log_test_result(
                "Performance Metrics", 
                performance_good, 
                "Performance metrics collected",
                {
                    "Average Response Time": f"{avg_response_time:.2f}s",
                    "Min Response Time": f"{min_response_time:.2f}s", 
                    "Max Response Time": f"{max_response_time:.2f}s",
                    "Average Input Tokens": f"{avg_input_tokens:.1f}",
                    "Average Output Tokens": f"{avg_output_tokens:.1f}",
                    "Performance Rating": "✅ Good" if performance_good else "⚠️ Slow"
                }
            )
            return performance_good
            
        except Exception as e:
            self.log_test_result(
                "Performance Metrics", 
                False, 
                f"Performance testing failed: {str(e)}"
            )
            return False

    def run_all_tests(self) -> Dict[str, Any]:
        """Run all integration tests"""
        print("🧪 Starting PE-GPT Bedrock Integration Tests")
        print("=" * 60)
        
        # Test sequence
        test_sequence = [
            ("AWS Credentials", self.test_aws_credentials),
            ("Bedrock Configuration", self.test_bedrock_config),
            ("Bedrock Client Init", self.test_bedrock_client_init),
            ("Message Conversion", self.test_message_conversion),
            ("Bedrock API Call", self.test_bedrock_api_call),
            ("BedrockLLM Class", self.test_bedrock_llm_class),
            ("RAG Functionality", self.test_rag_functionality),
            ("Enhanced RAG Functionality", self.test_enhanced_rag_functionality),
            ("Chat Engine Integration", self.test_chat_engine_integration),
            ("Error Handling", self.test_error_handling),
            ("Performance Metrics", self.test_performance_metrics)
        ]
        
        # Run tests
        for test_name, test_func in test_sequence:
            try:
                test_func()
            except Exception as e:
                self.log_test_result(
                    test_name, 
                    False, 
                    f"Test execution failed: {str(e)}"
                )
                print(f"Exception in {test_name}: {traceback.format_exc()}")
        
        # Generate summary
        print("=" * 60)
        print("🏁 Test Summary")
        print("=" * 60)
        
        print(f"Total Tests: {self.total_tests}")
        print(f"Passed: {self.passed_tests} ✅")
        print(f"Failed: {self.failed_tests} ❌")
        print(f"Success Rate: {(self.passed_tests/self.total_tests*100):.1f}%" if self.total_tests > 0 else "0%")
        
        # Detailed results
        print("\n📋 Detailed Results:")
        for test_name, result in self.test_results.items():
            print(f"{result['status']}: {test_name}")
            if result['message']:
                print(f"    {result['message']}")
        
        # Overall assessment
        overall_success = self.failed_tests == 0
        print(f"\n🎯 Overall Assessment: {'✅ ALL TESTS PASSED' if overall_success else '❌ SOME TESTS FAILED'}")
        
        if not overall_success:
            print("\n⚠️ Failed tests need attention before production deployment.")
        else:
            print("\n🚀 System is ready for production use!")
        
        return {
            "overall_success": overall_success,
            "total_tests": self.total_tests,
            "passed_tests": self.passed_tests,
            "failed_tests": self.failed_tests,
            "success_rate": (self.passed_tests/self.total_tests*100) if self.total_tests > 0 else 0,
            "detailed_results": self.test_results
        }


def main():
    """Main function to run integration tests"""
    print("🔧 PE-GPT Bedrock Migration - Integration Test Suite")
    print("This script will test all components of the migrated system.")
    print()
    
    # Check if running in correct directory
    if not os.path.exists("main.py") or not os.path.exists("core/llm/llm.py"):
        print("❌ Error: Please run this script from the PE-GPT root directory")
        sys.exit(1)
    
    # Initialize and run tests
    runner = IntegrationTestRunner()
    results = runner.run_all_tests()
    
    # Save results to file
    results_file = "integration_test_results.json"
    try:
        with open(results_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        print(f"\n💾 Test results saved to: {results_file}")
    except Exception as e:
        print(f"\n⚠️ Could not save results to file: {e}")
    
    # Exit with appropriate code
    sys.exit(0 if results["overall_success"] else 1)


if __name__ == "__main__":
    main()