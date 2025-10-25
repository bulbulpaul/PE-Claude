#!/usr/bin/env python3
"""
Basic functionality test script for PE-GPT Bedrock migration
Tests components that don't require AWS credentials
"""

import os
import sys
import json
import traceback
from typing import Dict, List, Any

# Add core modules to path
sys.path.append('.')
sys.path.append('core')

# Import application modules
from core.llm.llm import (
    convert_messages_to_bedrock_format,
    BedrockConfig,
    BedrockError
)

class BasicTestRunner:
    """
    Basic test runner for PE-GPT Bedrock migration (no AWS required)
    """
    
    def __init__(self):
        self.test_results = {}
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

    def test_bedrock_config(self) -> bool:
        """Test Bedrock configuration"""
        print("⚙️ Testing Bedrock Configuration...")
        
        try:
            config = BedrockConfig()
            
            # Validate configuration values
            config_valid = True
            config_issues = []
            
            if not config.aws_region:
                config_valid = False
                config_issues.append("Missing AWS region")
            
            if not config.bedrock_model_id:
                config_valid = False
                config_issues.append("Missing Bedrock model ID")
            
            if config.max_tokens < 1 or config.max_tokens > 4096:
                config_valid = False
                config_issues.append(f"Invalid max_tokens: {config.max_tokens}")
            
            if config.temperature < 0.0 or config.temperature > 1.0:
                config_valid = False
                config_issues.append(f"Invalid temperature: {config.temperature}")
            
            self.log_test_result(
                "Bedrock Configuration", 
                config_valid, 
                "Configuration validation completed" if config_valid else f"Configuration issues: {', '.join(config_issues)}",
                {
                    "AWS Region": config.aws_region,
                    "Model ID": config.bedrock_model_id,
                    "Max Tokens": config.max_tokens,
                    "Temperature": config.temperature,
                    "Model Display Name": config.get_model_display_name()
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
                },
                {
                    "name": "Empty content handling",
                    "input": [
                        {"role": "user", "content": ""},
                        {"role": "user", "content": "Valid message"}
                    ],
                    "expected_length": 1  # Empty message should be filtered out
                },
                {
                    "name": "Invalid message format handling",
                    "input": [
                        {"invalid": "format"},
                        {"role": "user", "content": "Valid message"}
                    ],
                    "expected_length": 1  # Invalid message should be filtered out
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
        """Test actual Bedrock API call (requires AWS credentials)"""
        print("🌐 Testing Bedrock API Call...")
        
        try:
            # Check if AWS credentials are available
            import boto3
            from botocore.exceptions import NoCredentialsError, ClientError
            
            try:
                session = boto3.Session()
                credentials = session.get_credentials()
                if not credentials:
                    self.log_test_result(
                        "Bedrock API Call", 
                        False, 
                        "No AWS credentials found - skipping API test",
                        {"Note": "Set up AWS credentials to enable this test"}
                    )
                    return False
            except Exception as e:
                self.log_test_result(
                    "Bedrock API Call", 
                    False, 
                    f"AWS credentials check failed: {str(e)}"
                )
                return False
            
            # Import Bedrock functions
            from core.llm.llm import bedrock_init, bedrock_chat_completion, BedrockConfig
            
            # Initialize Bedrock client
            try:
                client = bedrock_init()
                if not client:
                    self.log_test_result(
                        "Bedrock API Call", 
                        False, 
                        "Failed to initialize Bedrock client"
                    )
                    return False
            except Exception as e:
                self.log_test_result(
                    "Bedrock API Call", 
                    False, 
                    f"Bedrock client initialization failed: {str(e)}"
                )
                return False
            
            # Get configuration
            config = BedrockConfig()
            
            # Simple test message
            test_messages = [
                {"role": "user", "content": "Hello! Please respond with exactly 'API test successful' to confirm the connection is working."}
            ]
            
            # Record start time
            import time
            start_time = time.time()
            
            # Make API call
            try:
                response = bedrock_chat_completion(
                    client=client,
                    messages=test_messages,
                    model_id=config.bedrock_model_id,
                    max_tokens=50,
                    temperature=0.0
                )
                
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
                        "Model Used": config.bedrock_model_id,
                        "Input Tokens": response.get("usage", {}).get("input_tokens", "Unknown"),
                        "Output Tokens": response.get("usage", {}).get("output_tokens", "Unknown"),
                        "Response Preview": response["content"][:100] + "..." if len(response["content"]) > 100 else response["content"]
                    }
                )
                return True
                
            except Exception as e:
                self.log_test_result(
                    "Bedrock API Call", 
                    False, 
                    f"API call failed: {str(e)}"
                )
                return False
            
        except Exception as e:
            self.log_test_result(
                "Bedrock API Call", 
                False, 
                f"Bedrock API test failed: {str(e)}"
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
            
            # Test 3: Non-list input
            try:
                convert_messages_to_bedrock_format("not a list")
                error_tests["Non-list Input"] = "❌ Should have raised error"
            except BedrockError:
                error_tests["Non-list Input"] = "✅ Correctly handled"
            except Exception as e:
                error_tests["Non-list Input"] = f"⚠️ Unexpected error: {type(e).__name__}"
            
            # Test 4: BedrockError creation
            try:
                raise BedrockError("Test error", "TestCode")
            except BedrockError as e:
                if hasattr(e, 'error_code') and e.error_code == "TestCode":
                    error_tests["BedrockError Creation"] = "✅ Correctly handled"
                else:
                    error_tests["BedrockError Creation"] = "⚠️ Missing error code"
            except Exception as e:
                error_tests["BedrockError Creation"] = f"⚠️ Unexpected error: {type(e).__name__}"
            
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

    def test_imports_and_structure(self) -> bool:
        """Test that all imports work correctly"""
        print("📦 Testing Imports and Code Structure...")
        
        try:
            import_tests = {}
            
            # Test core imports
            try:
                from core.llm.llm import bedrock_init, bedrock_chat_completion, BedrockLLM
                import_tests["Core LLM Imports"] = "✅ Success"
            except Exception as e:
                import_tests["Core LLM Imports"] = f"❌ Failed: {str(e)}"
            
            # Test main application import
            try:
                import main
                import_tests["Main Application"] = "✅ Success"
            except Exception as e:
                import_tests["Main Application"] = f"❌ Failed: {str(e)}"
            
            # Test GUI imports
            try:
                from core.gui import gui, design_stages
                import_tests["GUI Modules"] = "✅ Success"
            except Exception as e:
                import_tests["GUI Modules"] = f"❌ Failed: {str(e)}"
            
            # Test knowledge base structure
            kb_paths = [
                "core/knowledge/kb/database",
                "core/knowledge/kb/database1", 
                "core/knowledge/kb/introduction"
            ]
            
            existing_kb = []
            for path in kb_paths:
                if os.path.exists(path) and os.path.isdir(path):
                    files = [f for f in os.listdir(path) if f.endswith('.txt')]
                    if files:
                        existing_kb.append(f"{path} ({len(files)} files)")
            
            if existing_kb:
                import_tests["Knowledge Base Structure"] = f"✅ Found: {', '.join(existing_kb)}"
            else:
                import_tests["Knowledge Base Structure"] = "⚠️ No knowledge base files found"
            
            # Test requirements file
            if os.path.exists("requirements.txt"):
                with open("requirements.txt", 'r') as f:
                    requirements = f.read()
                    if "boto3" in requirements and "llama_index" in requirements:
                        import_tests["Requirements File"] = "✅ Contains required dependencies"
                    else:
                        import_tests["Requirements File"] = "⚠️ Missing some dependencies"
            else:
                import_tests["Requirements File"] = "❌ requirements.txt not found"
            
            # Count successful imports
            successful_imports = sum(1 for result in import_tests.values() if "✅" in result)
            total_import_tests = len(import_tests)
            
            self.log_test_result(
                "Imports and Structure", 
                successful_imports >= total_import_tests - 1,  # Allow one failure
                f"Import tests completed ({successful_imports}/{total_import_tests} passed)",
                import_tests
            )
            return successful_imports >= total_import_tests - 1
            
        except Exception as e:
            self.log_test_result(
                "Imports and Structure", 
                False, 
                f"Import test failed: {str(e)}"
            )
            return False

    def test_file_structure(self) -> bool:
        """Test that all required files exist"""
        print("📁 Testing File Structure...")
        
        try:
            required_files = [
                "main.py",
                "core/llm/llm.py",
                "core/gui/gui.py",
                "core/gui/design_stages.py",
                "requirements.txt"
            ]
            
            optional_files = [
                "AWS_SETUP.md",
                "MIGRATION_GUIDE.md",
                "README.md"
            ]
            
            file_tests = {}
            
            # Check required files
            for file_path in required_files:
                if os.path.exists(file_path):
                    file_tests[f"Required: {file_path}"] = "✅ Exists"
                else:
                    file_tests[f"Required: {file_path}"] = "❌ Missing"
            
            # Check optional files
            for file_path in optional_files:
                if os.path.exists(file_path):
                    file_tests[f"Optional: {file_path}"] = "✅ Exists"
                else:
                    file_tests[f"Optional: {file_path}"] = "⚠️ Missing"
            
            # Count required files
            required_exists = sum(1 for key, result in file_tests.items() 
                                if key.startswith("Required:") and "✅" in result)
            total_required = len(required_files)
            
            self.log_test_result(
                "File Structure", 
                required_exists == total_required, 
                f"File structure check completed ({required_exists}/{total_required} required files found)",
                file_tests
            )
            return required_exists == total_required
            
        except Exception as e:
            self.log_test_result(
                "File Structure", 
                False, 
                f"File structure test failed: {str(e)}"
            )
            return False

    def run_all_tests(self) -> Dict[str, Any]:
        """Run all basic tests"""
        print("🧪 Starting PE-GPT Bedrock Basic Tests (No AWS Required)")
        print("=" * 60)
        
        # Test sequence
        test_sequence = [
            ("File Structure", self.test_file_structure),
            ("Imports and Structure", self.test_imports_and_structure),
            ("Bedrock Configuration", self.test_bedrock_config),
            ("Message Conversion", self.test_message_conversion),
            ("Bedrock API Call", self.test_bedrock_api_call),
            ("Error Handling", self.test_error_handling)
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
            print("\n⚠️ Failed tests indicate issues with the basic implementation.")
            print("💡 Note: AWS connectivity tests require proper credentials and are not included here.")
        else:
            print("\n🚀 Basic implementation is working correctly!")
            print("💡 Next step: Set up AWS credentials and run full integration tests.")
        
        return {
            "overall_success": overall_success,
            "total_tests": self.total_tests,
            "passed_tests": self.passed_tests,
            "failed_tests": self.failed_tests,
            "success_rate": (self.passed_tests/self.total_tests*100) if self.total_tests > 0 else 0,
            "detailed_results": self.test_results
        }


def main():
    """Main function to run basic tests"""
    print("🔧 PE-GPT Bedrock Migration - Basic Test Suite")
    print("This script tests basic components and includes Bedrock API call test.")
    print("Note: Bedrock API test requires AWS credentials to be configured.")
    print()
    
    # Check if running in correct directory
    if not os.path.exists("main.py") or not os.path.exists("core/llm/llm.py"):
        print("❌ Error: Please run this script from the PE-GPT root directory")
        sys.exit(1)
    
    # Initialize and run tests
    runner = BasicTestRunner()
    results = runner.run_all_tests()
    
    # Save results to file
    results_file = "tests/basic_test_results.json"
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