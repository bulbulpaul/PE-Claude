"""
Checkpoint test for LLM-related changes (Tasks 1-3)
Tests BedrockConfig updates, model support, and max_tokens handling
"""
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Mock streamlit before importing llm module
from unittest.mock import MagicMock
mock_st = MagicMock()
mock_st.session_state = {}
sys.modules['streamlit'] = mock_st

# Mock llama_index modules
sys.modules['llama_index'] = MagicMock()
sys.modules['llama_index.core'] = MagicMock()
sys.modules['llama_index.core.llms'] = MagicMock()
sys.modules['llama_index.core.llms.types'] = MagicMock()
sys.modules['llama_index.core.base'] = MagicMock()
sys.modules['llama_index.core.base.llms'] = MagicMock()
sys.modules['llama_index.core.base.llms.types'] = MagicMock()
sys.modules['llama_index.embeddings'] = MagicMock()
sys.modules['llama_index.embeddings.bedrock'] = MagicMock()
sys.modules['llama_index.core.indices'] = MagicMock()
sys.modules['llama_index.core.indices.vector_store'] = MagicMock()
sys.modules['llama_index.core.storage'] = MagicMock()
sys.modules['llama_index.core.storage.storage_context'] = MagicMock()
sys.modules['llama_index.core.node_parser'] = MagicMock()
sys.modules['llama_index.readers'] = MagicMock()
sys.modules['llama_index.readers.file'] = MagicMock()

# Now import only BedrockConfig class directly from the file
import importlib.util
spec = importlib.util.spec_from_file_location("llm_module", "core/llm/llm.py")
llm_module = importlib.util.module_from_spec(spec)

# Execute only the class definition part
with open("core/llm/llm.py", "r") as f:
    content = f.read()

# Extract BedrockConfig class
import re
class_match = re.search(r'(class BedrockConfig:.*?)(?=\ndef bedrock_init|\nclass )', content, re.DOTALL)
if class_match:
    class_code = class_match.group(1)
    # Add necessary imports
    exec_globals = {"os": os, "st": mock_st}
    exec(class_code, exec_globals)
    BedrockConfig = exec_globals['BedrockConfig']

def test_default_model_id():
    """Task 1.1: DEFAULT_MODEL_IDがClaude 4.5 Opusであること"""
    expected = "us.anthropic.claude-opus-4-5-20251101-v1:0"
    actual = BedrockConfig.DEFAULT_MODEL_ID
    assert actual == expected, f"Expected {expected}, got {actual}"
    print("✅ Task 1.1: DEFAULT_MODEL_ID is Claude 4.5 Opus")

def test_default_max_tokens():
    """Task 1.2: DEFAULT_MAX_TOKENSが8000であること"""
    expected = 8000
    actual = BedrockConfig.DEFAULT_MAX_TOKENS
    assert actual == expected, f"Expected {expected}, got {actual}"
    print("✅ Task 1.2: DEFAULT_MAX_TOKENS is 8000")

def test_available_models():
    """Task 1.3: AVAILABLE_MODELSにClaude 4.5モデルが含まれること"""
    models = BedrockConfig.AVAILABLE_MODELS
    
    # Check Claude 4.5 Opus
    assert "claude-4.5-opus" in models, "Missing claude-4.5-opus"
    assert models["claude-4.5-opus"] == "us.anthropic.claude-opus-4-5-20251101-v1:0"
    
    # Check Claude 4.5 Sonnet
    assert "claude-4.5-sonnet" in models, "Missing claude-4.5-sonnet"
    
    # Check Claude 4.5 Haiku
    assert "claude-4.5-haiku" in models, "Missing claude-4.5-haiku"
    
    # Check global inference profiles
    assert "claude-4.5-opus-global" in models, "Missing claude-4.5-opus-global"
    
    print("✅ Task 1.3: AVAILABLE_MODELS contains Claude 4.5 models")

def test_get_max_token_limit():
    """Task 1.4: _get_max_token_limit()が正しく動作すること"""
    config = BedrockConfig()
    
    # Claude 4.x -> 64000
    assert config._get_max_token_limit("us.anthropic.claude-opus-4-5-20251101-v1:0") == 64000
    assert config._get_max_token_limit("us.anthropic.claude-sonnet-4-20250514-v1:0") == 64000
    assert config._get_max_token_limit("claude-4-test") == 64000
    
    # Claude 3.5 -> 8192
    assert config._get_max_token_limit("anthropic.claude-3-5-sonnet-20241022-v2:0") == 8192
    assert config._get_max_token_limit("claude-3.5-test") == 8192
    
    # Legacy -> 4096
    assert config._get_max_token_limit("anthropic.claude-3-sonnet-20240229-v1:0") == 4096
    
    print("✅ Task 1.4: _get_max_token_limit() works correctly")

def test_validate_config_prefixes():
    """Task 1.5: _validate_config()が有効なプレフィックスを受け入れること"""
    valid_prefixes = [
        "us.anthropic.claude-opus-4-5-20251101-v1:0",
        "eu.anthropic.claude-opus-4-5-20251101-v1:0",
        "global.anthropic.claude-opus-4-5-20251101-v1:0",
        "anthropic.claude-3-5-sonnet-20241022-v2:0",
        "amazon.titan-embed-text-v2:0"
    ]
    
    for model_id in valid_prefixes:
        config = BedrockConfig()
        config.bedrock_model_id = model_id
        config._validate_config()
        assert config.bedrock_model_id == model_id, f"Valid prefix rejected: {model_id}"
    
    print("✅ Task 1.5: _validate_config() accepts valid prefixes")

def test_validate_config_invalid_prefix():
    """Task 1.5: 無効なプレフィックスがデフォルトにフォールバックすること"""
    config = BedrockConfig()
    config.bedrock_model_id = "invalid.model-id"
    config._validate_config()
    assert config.bedrock_model_id == BedrockConfig.DEFAULT_MODEL_ID
    print("✅ Task 1.5: Invalid prefix falls back to default")

def run_all_tests():
    """Run all checkpoint tests"""
    print("\n" + "="*60)
    print("LLM Checkpoint Tests (Tasks 1-3)")
    print("="*60 + "\n")
    
    tests = [
        test_default_model_id,
        test_default_max_tokens,
        test_available_models,
        test_get_max_token_limit,
        test_validate_config_prefixes,
        test_validate_config_invalid_prefix,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            test()
            passed += 1
        except AssertionError as e:
            print(f"❌ {test.__name__}: {e}")
            failed += 1
        except Exception as e:
            print(f"❌ {test.__name__}: Unexpected error - {e}")
            failed += 1
    
    print("\n" + "="*60)
    print(f"Results: {passed} passed, {failed} failed")
    print("="*60 + "\n")
    
    return failed == 0

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
