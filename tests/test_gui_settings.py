"""
GUI Settings Panel Tests

This module tests the KnowledgeBase settings panel functionality
including session state management and configuration validation.

@reference: PE-GPT: a New Paradigm for Power Electronics Design, by Fanfan Lin, Xinze Li, et al.
@code-author: Xinze Li, Fanfan Lin
@github: https://github.com/XinzeLee/PE-GPT
"""

import unittest
import unittest.mock as mock
from unittest.mock import MagicMock, patch
import sys
import os

# Add the project root to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.gui.gui import (
    init_kb_settings,
    update_kb_config,
    get_current_kb_config,
    is_kb_config_changed,
    reset_kb_config_changed_flag,
    save_kb_config_to_session
)
from core.knowledge.kb_config import KnowledgeBaseConfig


class TestGUISettings(unittest.TestCase):
    """GUI設定パネルのテストクラス"""
    
    def setUp(self):
        """各テストメソッドの前に実行される初期化"""
        # Mock streamlit session state
        self.mock_session_state = {}
        
    def test_init_kb_settings(self):
        """KnowledgeBase設定の初期化テスト"""
        with patch('streamlit.session_state', self.mock_session_state):
            init_kb_settings()
            
            # デフォルト値が正しく設定されているかチェック
            assert self.mock_session_state["kb_mode"] == "hybrid"
            assert self.mock_session_state["kb_id"] == ""
            assert self.mock_session_state["kb_region"] == "us-east-1"
            assert self.mock_session_state["similarity_top_k"] == 5
            assert self.mock_session_state["confidence_threshold"] == 0.0
            assert self.mock_session_state["enable_fallback"] == True
            assert self.mock_session_state["retry_attempts"] == 3
            assert self.mock_session_state["kb_config"] is None
            assert self.mock_session_state["kb_config_changed"] == False
    
    def test_init_kb_settings_preserves_existing(self):
        """既存の設定値を保持することをテスト"""
        # 既存の値を設定
        self.mock_session_state["kb_mode"] = "local"
        self.mock_session_state["kb_id"] = "existing_id"
        
        with patch('streamlit.session_state', self.mock_session_state):
            init_kb_settings()
            
            # 既存の値が保持されているかチェック
            assert self.mock_session_state["kb_mode"] == "local"
            assert self.mock_session_state["kb_id"] == "existing_id"
    
    def test_update_kb_config_valid_bedrock(self):
        """有効なBedrock設定での設定更新テスト"""
        self.mock_session_state.update({
            "kb_mode": "bedrock",
            "kb_id": "ABCDEFGHIJ",
            "kb_region": "us-east-1",
            "similarity_top_k": 10,
            "confidence_threshold": 0.5,
            "enable_fallback": True,
            "retry_attempts": 2,
            "kb_config": None,
            "kb_config_changed": False
        })
        
        with patch('streamlit.session_state', self.mock_session_state):
            config = update_kb_config()
            
            # 設定オブジェクトが正しく作成されているかチェック
            assert config is not None
            assert isinstance(config, KnowledgeBaseConfig)
            assert config.knowledge_base_id == "ABCDEFGHIJ"
            assert config.region == "us-east-1"
            assert config.mode == "bedrock"
            assert config.similarity_top_k == 10
            assert config.confidence_threshold == 0.5
            
            # セッション状態が更新されているかチェック
            assert self.mock_session_state["kb_config"] == config
            assert self.mock_session_state["kb_config_changed"] == True
    
    def test_update_kb_config_invalid_settings(self):
        """無効な設定での設定更新テスト"""
        self.mock_session_state.update({
            "kb_mode": "bedrock",
            "kb_id": "invalid_id",  # 無効なID形式
            "kb_region": "invalid-region",  # 無効なリージョン形式
            "similarity_top_k": 5,
            "confidence_threshold": 0.0,
            "enable_fallback": True,
            "retry_attempts": 3,
            "kb_config": None,
            "kb_config_changed": False
        })
        
        with patch('streamlit.session_state', self.mock_session_state):
            config = update_kb_config()
            
            # 無効な設定の場合はNoneが返されるかチェック
            assert config is None
            assert self.mock_session_state["kb_config"] is None
    
    def test_update_kb_config_local_mode(self):
        """ローカルモードでの設定更新テスト"""
        self.mock_session_state.update({
            "kb_mode": "local",
            "kb_id": "",
            "kb_region": "us-east-1",
            "similarity_top_k": 5,
            "confidence_threshold": 0.0,
            "enable_fallback": True,
            "retry_attempts": 3,
            "kb_config": None,
            "kb_config_changed": False
        })
        
        with patch('streamlit.session_state', self.mock_session_state):
            config = update_kb_config()
            
            # ローカルモードではNoneが返されるかチェック
            assert config is None
            assert self.mock_session_state["kb_config"] is None
    
    def test_get_current_kb_config(self):
        """現在の設定取得テスト"""
        test_config = KnowledgeBaseConfig(
            knowledge_base_id="ABCDEFGHIJ",
            region="us-east-1"
        )
        self.mock_session_state["kb_config"] = test_config
        
        with patch('streamlit.session_state', self.mock_session_state):
            config = get_current_kb_config()
            
            assert config == test_config
    
    def test_is_kb_config_changed(self):
        """設定変更フラグのテスト"""
        self.mock_session_state["kb_config_changed"] = True
        
        with patch('streamlit.session_state', self.mock_session_state):
            assert is_kb_config_changed() == True
        
        self.mock_session_state["kb_config_changed"] = False
        
        with patch('streamlit.session_state', self.mock_session_state):
            assert is_kb_config_changed() == False
    
    def test_reset_kb_config_changed_flag(self):
        """設定変更フラグのリセットテスト"""
        self.mock_session_state["kb_config_changed"] = True
        
        with patch('streamlit.session_state', self.mock_session_state):
            reset_kb_config_changed_flag()
            
            assert self.mock_session_state["kb_config_changed"] == False
    
    def test_save_kb_config_to_session(self):
        """設定のセッション保存テスト"""
        test_config = KnowledgeBaseConfig(
            knowledge_base_id="ABCDEFGHIJ",
            region="us-west-2",
            similarity_top_k=8,
            confidence_threshold=0.3,
            mode="hybrid",
            enable_fallback=False,
            retry_attempts=5
        )
        
        with patch('streamlit.session_state', self.mock_session_state):
            save_kb_config_to_session(test_config)
            
            # 全ての設定値がセッション状態に保存されているかチェック
            assert self.mock_session_state["kb_config"] == test_config
            assert self.mock_session_state["kb_mode"] == "hybrid"
            assert self.mock_session_state["kb_id"] == "ABCDEFGHIJ"
            assert self.mock_session_state["kb_region"] == "us-west-2"
            assert self.mock_session_state["similarity_top_k"] == 8
            assert self.mock_session_state["confidence_threshold"] == 0.3
            assert self.mock_session_state["enable_fallback"] == False
            assert self.mock_session_state["retry_attempts"] == 5
    
    def test_save_kb_config_to_session_none(self):
        """None設定の保存テスト"""
        with patch('streamlit.session_state', self.mock_session_state):
            save_kb_config_to_session(None)
            
            # Noneの場合は何も変更されないかチェック
            assert len(self.mock_session_state) == 0
    
    def test_config_change_detection(self):
        """設定変更の検出テスト"""
        # 初期設定
        initial_config = KnowledgeBaseConfig(
            knowledge_base_id="ABCDEFGHIJ",
            region="us-east-1",
            similarity_top_k=5
        )
        
        self.mock_session_state.update({
            "kb_mode": "bedrock",
            "kb_id": "ABCDEFGHIJ",
            "kb_region": "us-east-1",
            "similarity_top_k": 5,
            "confidence_threshold": 0.0,
            "enable_fallback": True,
            "retry_attempts": 3,
            "kb_config": initial_config,
            "kb_config_changed": False
        })
        
        with patch('streamlit.session_state', self.mock_session_state):
            # 変更なしの場合
            config = update_kb_config()
            # 初回は設定が作成されるため変更フラグがTrueになる
            assert self.mock_session_state["kb_config_changed"] == True
            
            # 設定を変更
            self.mock_session_state["similarity_top_k"] = 10
            
            # 変更が検出されるかテスト
            config = update_kb_config()
            assert self.mock_session_state["kb_config_changed"] == True
            assert config.similarity_top_k == 10


if __name__ == "__main__":
    unittest.main()