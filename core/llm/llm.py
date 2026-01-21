# -*- coding: utf-8 -*-
"""
@reference: PE-GPT: a New Paradigm for Power Electronics Design, by Fanfan Lin, Xinze Li, et al.
@code-author: Xinze Li, Fanfan Lin, and Weihao Lei
@github: https://github.com/XinzeLee/PE-GPT

@reference:
    Following references are related to power electronics GPT (PE-GPT)
    1: PE-GPT: a New Paradigm for Power Electronics Design
        Authors: Fanfan Lin, Xinze Li (corresponding), Weihao Lei, Juan J. Rodriguez-Andina, Josep M. Guerrero, Changyun Wen, Xin Zhang, and Hao Ma
        Paper DOI: 10.1109/TIE.2024.3454408
"""

import streamlit as st
import json
import boto3
import os
import time
from botocore.exceptions import ClientError, NoCredentialsError
from llama_index.core import VectorStoreIndex, SimpleDirectoryReader
from llama_index.core.llms import ChatMessage, MessageRole

from llama_index.core.node_parser import SimpleNodeParser
from llama_index.core.llms.llm import LLM
from llama_index.core.base.llms.types import ChatMessage as LLMChatMessage, MessageRole as LLMMessageRole
from typing import Any, List, Optional, Sequence




class BedrockConfig:
    """
    Configuration class for Bedrock settings with environment variable support
    """
    
    # Default values for configuration
    DEFAULT_REGION = "us-east-1"
    DEFAULT_MODEL_ID = "us.anthropic.claude-sonnet-4-5-20250929-v1:0"
    DEFAULT_EMBEDDING_MODEL_ID = "amazon.titan-embed-text-v2:0"
    DEFAULT_MAX_TOKENS = 5000
    DEFAULT_TEMPERATURE = 0.0
    
    # Available Claude models (verified with AWS Bedrock)
    AVAILABLE_MODELS = {
        # Claude 4.5 models using inference profiles (verified available in us-east-1)
        "claude-4.5-sonnet": "us.anthropic.claude-sonnet-4-5-20250929-v1:0",
        "claude-4.5-haiku": "us.anthropic.claude-haiku-4-5-20251001-v1:0",
        # Claude 4.0 models using inference profiles (verified available in us-east-1)
        "claude-4-sonnet": "us.anthropic.claude-sonnet-4-20250514-v1:0",
        "claude-4-opus": "us.anthropic.claude-opus-4-20250514-v1:0",
        "claude-4.1-opus": "us.anthropic.claude-opus-4-1-20250805-v1:0",
        # Global inference profiles (alternative)
        "claude-4.5-sonnet-global": "global.anthropic.claude-sonnet-4-5-20250929-v1:0",
        "claude-4.5-haiku-global": "global.anthropic.claude-haiku-4-5-20251001-v1:0",
        "claude-4-sonnet-global": "global.anthropic.claude-sonnet-4-20250514-v1:0"
    }
    
    def __init__(self):
        """Initialize configuration from environment variables with fallback to defaults"""
        self.aws_region = self._get_env_var("AWS_REGION", self.DEFAULT_REGION)
        self.bedrock_model_id = self._get_env_var("BEDROCK_MODEL_ID", self.DEFAULT_MODEL_ID)
        self.bedrock_embedding_model_id = self._get_env_var("BEDROCK_EMBEDDING_MODEL_ID", self.DEFAULT_EMBEDDING_MODEL_ID)
        self.max_tokens = int(self._get_env_var("BEDROCK_MAX_TOKENS", str(self.DEFAULT_MAX_TOKENS)))
        self.temperature = float(self._get_env_var("BEDROCK_TEMPERATURE", str(self.DEFAULT_TEMPERATURE)))
        
        # Validate configuration
        self._validate_config()
    
    def _get_env_var(self, var_name: str, default_value: str) -> str:
        """Get environment variable with default fallback"""
        value = os.getenv(var_name, default_value)
        if value != default_value:
            st.info(f"Using {var_name}={value} from environment variable")
        return value
    
    def _validate_config(self):
        """Validate configuration values"""
        # Validate region format
        if not self.aws_region or len(self.aws_region.split('-')) < 3:
            st.warning(f"Invalid AWS region format: {self.aws_region}. Using default: {self.DEFAULT_REGION}")
            self.aws_region = self.DEFAULT_REGION
        
        # Validate model ID format (including cross-region inference profiles)
        valid_prefixes = ('anthropic.', 'amazon.', 'us.anthropic.', 'eu.anthropic.')
        if not self.bedrock_model_id.startswith(valid_prefixes):
            st.warning(f"Invalid model ID format: {self.bedrock_model_id}. Using default: {self.DEFAULT_MODEL_ID}")
            self.bedrock_model_id = self.DEFAULT_MODEL_ID
        
        # Validate max_tokens range
        if self.max_tokens < 1 or self.max_tokens > 4096:
            st.warning(f"Invalid max_tokens value: {self.max_tokens}. Using default: {self.DEFAULT_MAX_TOKENS}")
            self.max_tokens = self.DEFAULT_MAX_TOKENS
        
        # Validate temperature range
        if self.temperature < 0.0 or self.temperature > 1.0:
            st.warning(f"Invalid temperature value: {self.temperature}. Using default: {self.DEFAULT_TEMPERATURE}")
            self.temperature = self.DEFAULT_TEMPERATURE
    
    def get_model_display_name(self) -> str:
        """Get human-readable model name"""
        for name, model_id in self.AVAILABLE_MODELS.items():
            if model_id == self.bedrock_model_id:
                return name
        return self.bedrock_model_id
    
    def to_dict(self) -> dict:
        """Convert configuration to dictionary"""
        return {
            "aws_region": self.aws_region,
            "bedrock_model_id": self.bedrock_model_id,
            "bedrock_embedding_model_id": self.bedrock_embedding_model_id,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature
        }


def bedrock_init(model_id=None, region=None):
    """
    Initialize Amazon Bedrock client for Claude models with enhanced configuration support
    
    Args:
        model_id: Bedrock model ID (overrides environment variable)
        region: AWS region (overrides environment variable)
    
    Returns:
        boto3 Bedrock Runtime client
    """
    try:
        # Initialize configuration
        config = BedrockConfig()
        
        # Override with provided parameters
        if region:
            config.aws_region = region
        if model_id:
            config.bedrock_model_id = model_id
        
        # Display configuration info
        st.info(f"Initializing Bedrock client in region: {config.aws_region}")
        st.info(f"Using model: {config.get_model_display_name()} ({config.bedrock_model_id})")
        
        # Initialize Bedrock Runtime client
        bedrock_client = boto3.client('bedrock-runtime', region_name=config.aws_region)
        
        # Test client connectivity (optional - don't fail if this doesn't work)
        try:
            # Create a separate bedrock client (not runtime) to test connectivity
            bedrock_control_client = boto3.client('bedrock', region_name=config.aws_region)
            bedrock_control_client.list_foundation_models()
            st.success("✅ Successfully connected to Amazon Bedrock")
        except ClientError as e:
            if e.response['Error']['Code'] == 'AccessDeniedException':
                st.info("⚠️ Limited Bedrock access detected. Runtime operations may still work.")
            else:
                st.info(f"ℹ️ Bedrock connectivity test skipped: {e.response['Error']['Code']}")
        except Exception as e:
            st.info(f"ℹ️ Bedrock connectivity test skipped: {str(e)}")
            
        # Always show success for client initialization
        st.success("🚀 Bedrock Runtime client initialized successfully")
        
        # Store configuration in session state
        if "bedrock_config" not in st.session_state:
            st.session_state["bedrock_config"] = config.to_dict()
        
        # Store individual values for backward compatibility
        if "bedrock_model" not in st.session_state:
            st.session_state["bedrock_model"] = config.bedrock_model_id
        
        if "aws_region" not in st.session_state:
            st.session_state["aws_region"] = config.aws_region
            
        return bedrock_client
        
    except NoCredentialsError:
        error_msg = """
        🔐 **AWS認証情報が見つかりません**
        
        以下のいずれかの方法でAWS認証情報を設定してください：
        
        **方法1: 環境変数**
        ```bash
        export AWS_ACCESS_KEY_ID=your_access_key_id
        export AWS_SECRET_ACCESS_KEY=your_secret_access_key
        export AWS_REGION=us-east-1
        ```
        
        **方法2: AWS CLI**
        ```bash
        aws configure
        ```
        
        **方法3: IAMロール (EC2/ECS環境)**
        - インスタンスまたはタスクに適切なIAMロールをアタッチ
        
        詳細な設定方法については、AWS_SETUP.mdを参照してください。
        """
        st.error(error_msg)
        raise
    except ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code == 'UnauthorizedOperation':
            st.error("🚫 **権限エラー**: Bedrockサービスへのアクセス権限がありません。IAMポリシーを確認してください。")
        elif error_code == 'InvalidRegion':
            st.error(f"🌍 **無効なリージョン**: {config.aws_region if 'config' in locals() else region} は無効なリージョンです。")
        else:
            st.error(f"⚠️ **AWS エラー**: {e.response['Error']['Message']}")
        raise
    except Exception as e:
        st.error(f"❌ **予期しないエラー**: Bedrock初期化中にエラーが発生しました: {e}")
        raise


class BedrockLLM(LLM):
    """
    Custom LLM class for Amazon Bedrock Claude integration with llama_index
    """
    
    model_id: str
    region: str
    temperature: float
    max_tokens: int
    system_prompt: str
    client: object = None
    
    def __init__(self, model_id: str = None, region: str = None, temperature: float = None, 
                 max_tokens: int = None, system_prompt: str = None, **kwargs):
        # Initialize configuration to get default values
        config = BedrockConfig()
        
        # Prepare data for Pydantic initialization using BedrockConfig defaults
        data = {
            'model_id': model_id or config.bedrock_model_id,
            'region': region or config.aws_region,
            'temperature': temperature if temperature is not None else config.temperature,
            'max_tokens': max_tokens or config.max_tokens,
            'system_prompt': system_prompt or "",
            'client': None
        }
        
        # Add any additional kwargs
        data.update(kwargs)
        
        super().__init__(**data)
        
    def _get_client(self):
        """Lazy initialization of Bedrock client with error handling"""
        if self.client is None:
            try:
                self.client = boto3.client('bedrock-runtime', region_name=self.region)
            except Exception as e:
                raise BedrockError(f"Bedrockクライアントの初期化に失敗しました: {str(e)}", "ClientInitError", e)
        return self.client
    
    @property
    def metadata(self):
        from llama_index.core.base.llms.types import LLMMetadata
        return LLMMetadata(
            context_window=200000,  # Claude 3 Sonnet context window
            num_output=self.max_tokens,
            is_chat_model=True,
            model_name=self.model_id
        )
    
    def chat(self, messages: Sequence[LLMChatMessage], **kwargs) -> Any:
        """
        Chat method for llama_index integration with error handling
        """
        try:
            # Validate input messages
            if not messages:
                raise BedrockError("メッセージが提供されていません", "EmptyMessages")
            
            # Convert llama_index messages to OpenAI format for our conversion function
            bedrock_messages = []
            print(f"DEBUG: Processing {len(messages)} messages")
            
            for i, msg in enumerate(messages):
                try:
                    print(f"DEBUG: Message {i+1}: role={msg.role}, content_type={type(msg.content)}, content_length={len(str(msg.content)) if msg.content else 0}")
                    
                    # Import here to avoid scope issues
                    from llama_index.core.base.llms.types import MessageRole as LLMMessageRole
                    
                    role = "user" if msg.role == LLMMessageRole.USER else "assistant"
                    if msg.role == LLMMessageRole.SYSTEM:
                        role = "system"
                    
                    # More lenient content checking
                    content = getattr(msg, 'content', None)
                    if content is None or (isinstance(content, str) and len(content.strip()) == 0):
                        print(f"DEBUG: Skipping message {i+1} - empty content")
                        continue
                        
                    bedrock_messages.append({"role": role, "content": str(content)})
                    print(f"DEBUG: Added message {i+1}: {role} - {str(content)[:100]}...")
                    
                except Exception as e:
                    print(f"DEBUG: Error processing message {i+1}: {str(e)}")
                    continue
            
            print(f"DEBUG: Final bedrock_messages count: {len(bedrock_messages)}")
            
            if not bedrock_messages:
                raise BedrockError("有効なメッセージがありません", "NoValidMessages")
            
            # Use our bedrock_chat_completion function
            client = self._get_client()
            response = bedrock_chat_completion(
                client=client,
                messages=bedrock_messages,
                model_id=self.model_id,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                system_prompt=self.system_prompt
            )
            
            # Return ChatResponse object as expected by llama_index
            from llama_index.core.base.llms.types import ChatResponse, ChatMessage as LLMChatMessage
            from llama_index.core.base.llms.types import MessageRole as LLMMessageRole
            
            content = response.get("content", "応答の生成に失敗しました")
            message = LLMChatMessage(role=LLMMessageRole.ASSISTANT, content=content)
            return ChatResponse(message=message, raw=response)
            
        except BedrockError:
            # Re-raise BedrockError as-is
            raise
        except Exception as e:
            error_msg = f"チャット処理中にエラーが発生しました: {str(e)}"
            st.error(f"❌ **チャットエラー**: {error_msg}")
            raise BedrockError(error_msg, "ChatError", e)
    
    def complete(self, prompt: str, **kwargs) -> Any:
        """
        Complete method for llama_index integration with error handling
        """
        try:
            # Validate input prompt
            if not prompt or not isinstance(prompt, str):
                raise BedrockError("有効なプロンプトが提供されていません", "InvalidPrompt")
            
            if len(prompt.strip()) == 0:
                raise BedrockError("プロンプトが空です", "EmptyPrompt")
            
            messages = [{"role": "user", "content": prompt.strip()}]
            client = self._get_client()
            response = bedrock_chat_completion(
                client=client,
                messages=messages,
                model_id=self.model_id,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                system_prompt=self.system_prompt
            )
            
            # Return CompletionResponse object as expected by llama_index
            from llama_index.core.base.llms.types import CompletionResponse
            
            content = response.get("content", "応答の生成に失敗しました")
            return CompletionResponse(text=content, raw=response)
            
        except BedrockError:
            # Re-raise BedrockError as-is
            raise
        except Exception as e:
            error_msg = f"完了処理中にエラーが発生しました: {str(e)}"
            st.error(f"❌ **完了エラー**: {error_msg}")
            raise BedrockError(error_msg, "CompleteError", e)
    
    async def achat(self, messages: Sequence[LLMChatMessage], **kwargs) -> Any:
        """Async chat method - delegates to sync version for now"""
        return self.chat(messages, **kwargs)
    
    async def acomplete(self, prompt: str, **kwargs) -> Any:
        """Async complete method - delegates to sync version for now"""
        return self.complete(prompt, **kwargs)
    
    def stream_chat(self, messages: Sequence[LLMChatMessage], **kwargs) -> Any:
        """Streaming chat method - returns regular response for now"""
        return self.chat(messages, **kwargs)
    
    def stream_complete(self, prompt: str, **kwargs) -> Any:
        """Streaming complete method - returns regular response for now"""
        return self.complete(prompt, **kwargs)
    
    async def astream_chat(self, messages: Sequence[LLMChatMessage], **kwargs) -> Any:
        """Async streaming chat method - delegates to sync version for now"""
        return self.stream_chat(messages, **kwargs)
    
    async def astream_complete(self, prompt: str, **kwargs) -> Any:
        """Async streaming complete method - delegates to sync version for now"""
        return self.stream_complete(prompt, **kwargs)


# Specialized multi-agents to handle different tasks with Retrieval Augmented Generation (RAG)
@st.cache_resource(show_spinner=False)
def rag_load(database_folder, llm_model=None, 
              temperature=None, chunk_size=None, system_prompt=None, use_bedrock=True):
    """
    This function is the retrieval-augmented generation (RAG) for LLM
    Uses Amazon Bedrock Claude models for document processing and chat
    
    Args:
        database_folder: Path to documents folder
        llm_model: Optional Bedrock model ID (uses BedrockConfig default if None)
        temperature: Model temperature (default: 0.0)
        chunk_size: Document chunk size (default: 1024)
        system_prompt: System prompt for the model
        use_bedrock: Whether to use Bedrock (always True, kept for compatibility)
    """
    
    if chunk_size is None: chunk_size = 1024
    if temperature is None: temperature = 0.0
    
    with st.spinner(text="Loading and indexing docs – hang tight! This should take 1-2 minutes."):
        
        docs = SimpleDirectoryReader(database_folder).load_data()
        node_parser = SimpleNodeParser.from_defaults(chunk_size=chunk_size)
        nodes = node_parser.get_nodes_from_documents(docs)
        
        # Use Bedrock Claude model with BedrockConfig defaults
        llm_kwargs = {
            'temperature': temperature,
            'system_prompt': system_prompt
        }
        if llm_model is not None:
            llm_kwargs['model_id'] = llm_model
            
        llm = BedrockLLM(**llm_kwargs)
        
        # Use the new Settings API instead of deprecated ServiceContext
        from llama_index.core.settings import Settings
        from llama_index.embeddings.bedrock import BedrockEmbedding
        
        # Set up Bedrock embedding model using config default
        config = BedrockConfig()
        embed_model = BedrockEmbedding(
            model_name=config.bedrock_embedding_model_id,
            region_name=llm.region
        )
        
        Settings.llm = llm
        Settings.embed_model = embed_model
        index = VectorStoreIndex(nodes)
        return index


@st.cache_resource(show_spinner=False)
def enhanced_rag_load(
    database_folder: str = None,
    knowledge_base_config=None,
    llm_model: str = None,
    temperature: float = None,
    chunk_size: int = None,
    system_prompt: str = None,
    use_bedrock: bool = True
):
    """
    Enhanced RAG function with Bedrock KnowledgeBase integration support.
    
    This function extends the original rag_load function to support:
    - Local file-based document indexing (original functionality)
    - Amazon Bedrock KnowledgeBase integration
    - Hybrid search combining both sources
    - Backward compatibility with existing rag_load usage
    
    Args:
        database_folder: Path to local documents folder (optional if using bedrock-only mode)
        knowledge_base_config: KnowledgeBaseConfig instance for Bedrock integration (optional)
        llm_model: Optional Bedrock model ID (uses BedrockConfig default if None)
        temperature: Model temperature (default: 0.0)
        chunk_size: Document chunk size for local files (default: 1024)
        system_prompt: System prompt for the model
        use_bedrock: Whether to use Bedrock (always True, kept for compatibility)
    
    Returns:
        VectorStoreIndex: Enhanced index supporting hybrid search or local-only search
    """
    from core.knowledge.kb_config import KnowledgeBaseConfig
    from core.llm.hybrid_retriever import HybridRetriever
    from core.llm.error_handler import get_error_handler, handle_error, format_error_for_user
    
    # Set defaults
    if chunk_size is None: 
        chunk_size = 1024
    if temperature is None: 
        temperature = 0.0
    
    # Determine search mode based on provided parameters
    has_local = database_folder is not None
    has_bedrock = knowledge_base_config is not None and knowledge_base_config.is_bedrock_enabled()
    
    # Validate that at least one source is available
    if not has_local and not has_bedrock:
        raise ValueError("少なくともローカルフォルダまたはKnowledgeBase設定のいずれかが必要です")
    
    # Determine effective mode
    if has_local and has_bedrock:
        effective_mode = knowledge_base_config.mode if knowledge_base_config.mode in ["local", "bedrock", "hybrid"] else "hybrid"
    elif has_local:
        effective_mode = "local"
    else:
        effective_mode = "bedrock"
    
    with st.spinner(text=f"Enhanced RAG初期化中 (モード: {effective_mode}) – しばらくお待ちください..."):
        
        # Initialize LLM
        llm_kwargs = {
            'temperature': temperature,
            'system_prompt': system_prompt
        }
        if llm_model is not None:
            llm_kwargs['model_id'] = llm_model
            
        llm = BedrockLLM(**llm_kwargs)
        
        # Set up embedding model
        from llama_index.core.settings import Settings
        from llama_index.embeddings.bedrock import BedrockEmbedding
        
        config = BedrockConfig()
        embed_model = BedrockEmbedding(
            model_name=config.bedrock_embedding_model_id,
            region_name=llm.region
        )
        
        Settings.llm = llm
        Settings.embed_model = embed_model
        
        # Initialize local retriever if needed
        local_retriever = None
        if has_local and effective_mode in ["local", "hybrid"]:
            try:
                st.info("ローカルファイルをインデックス化中...")
                docs = SimpleDirectoryReader(database_folder).load_data()
                node_parser = SimpleNodeParser.from_defaults(chunk_size=chunk_size)
                nodes = node_parser.get_nodes_from_documents(docs)
                
                local_index = VectorStoreIndex(nodes)
                local_retriever = local_index.as_retriever(
                    similarity_top_k=knowledge_base_config.similarity_top_k if knowledge_base_config else 5
                )
                st.success(f"ローカルファイル {len(docs)} 件をインデックス化完了")
                
            except Exception as e:
                # Use enhanced error handler
                error_handler = get_error_handler()
                error_info = error_handler.handle_error(e, "Local file indexing")
                
                # Display user-friendly error message
                user_message = error_handler.format_user_message(error_info, include_actions=True)
                st.error(user_message)
                
                if effective_mode == "local":
                    raise
                # For hybrid mode, continue without local
                st.warning("ハイブリッドモードでローカル検索を無効化し、Bedrockのみで続行します")
                effective_mode = "bedrock"
        
        # Create hybrid retriever or return local-only index
        if effective_mode == "local":
            # Return traditional VectorStoreIndex for backward compatibility
            return local_index
        
        elif effective_mode in ["bedrock", "hybrid"]:
            # Create hybrid retriever with appropriate configuration
            try:
                hybrid_retriever = HybridRetriever(
                    local_retriever=local_retriever,
                    config=knowledge_base_config,
                    mode=effective_mode
                )
                
                # Create a custom index that uses the hybrid retriever
                enhanced_index = EnhancedVectorStoreIndex(
                    hybrid_retriever=hybrid_retriever,
                    local_index=local_index if local_retriever else None
                )
                
                st.success(f"Enhanced RAG初期化完了 (モード: {effective_mode})")
                return enhanced_index
                
            except Exception as e:
                # Use enhanced error handler
                error_handler = get_error_handler()
                error_info = error_handler.handle_error(e, "Enhanced RAG initialization")
                
                # Display user-friendly error message
                user_message = error_handler.format_user_message(error_info, include_actions=True)
                st.error(user_message)
                
                # Fallback logic
                if knowledge_base_config and knowledge_base_config.enable_fallback and local_retriever:
                    st.warning("Bedrock初期化に失敗しました。ローカルモードにフォールバックします")
                    return local_index
                else:
                    raise
        
        else:
            raise ValueError(f"サポートされていないモード: {effective_mode}")


class EnhancedVectorStoreIndex:
    """
    Enhanced VectorStoreIndex that supports hybrid retrieval.
    
    This class provides backward compatibility with the original VectorStoreIndex
    while adding support for hybrid search capabilities.
    """
    
    def __init__(self, hybrid_retriever: 'HybridRetriever', local_index=None):
        """
        Initialize enhanced index.
        
        Args:
            hybrid_retriever: HybridRetriever instance
            local_index: Original VectorStoreIndex for fallback (optional)
        """
        self.hybrid_retriever = hybrid_retriever
        self.local_index = local_index
        self._retriever = None
    
    def as_retriever(self, **kwargs):
        """
        Create retriever interface compatible with llama_index.
        
        Args:
            **kwargs: Additional retriever parameters
            
        Returns:
            BaseRetriever: Retriever instance
        """
        # Update hybrid retriever configuration if parameters provided
        if 'similarity_top_k' in kwargs and hasattr(self.hybrid_retriever, 'config'):
            if self.hybrid_retriever.config:
                self.hybrid_retriever.config.similarity_top_k = kwargs['similarity_top_k']
        
        return self.hybrid_retriever
    
    def as_query_engine(self, **kwargs):
        """
        Create query engine interface compatible with llama_index.
        
        Args:
            **kwargs: Additional query engine parameters
            
        Returns:
            BaseQueryEngine: Query engine instance
        """
        from llama_index.core.query_engine import RetrieverQueryEngine
        
        retriever = self.as_retriever(**kwargs)
        return RetrieverQueryEngine.from_args(retriever=retriever, **kwargs)
    
    def as_chat_engine(self, **kwargs):
        """
        Create chat engine interface compatible with llama_index.
        
        Args:
            **kwargs: Additional chat engine parameters
            
        Returns:
            BaseChatEngine: Chat engine instance
        """
        from llama_index.core.chat_engine import CondensePlusContextChatEngine
        
        retriever = self.as_retriever(**kwargs)
        return CondensePlusContextChatEngine.from_defaults(
            retriever=retriever,
            **kwargs
        )
    
    def get_nodes(self, node_ids=None):
        """
        Get nodes from the index (backward compatibility).
        
        Args:
            node_ids: Optional list of node IDs
            
        Returns:
            List: List of nodes
        """
        if self.local_index and hasattr(self.local_index, 'get_nodes'):
            return self.local_index.get_nodes(node_ids)
        return []
    
    def insert_nodes(self, nodes):
        """
        Insert nodes into the index (backward compatibility).
        
        Args:
            nodes: List of nodes to insert
        """
        # For hybrid mode, node insertion is not supported
        if hasattr(self, 'hybrid_retriever') and self.hybrid_retriever:
            raise NotImplementedError("Node insertion not supported in hybrid mode")
        
        if self.local_index and hasattr(self.local_index, 'insert_nodes'):
            return self.local_index.insert_nodes(nodes)
        raise NotImplementedError("Node insertion not supported")
    
    def delete_nodes(self, node_ids):
        """
        Delete nodes from the index (backward compatibility).
        
        Args:
            node_ids: List of node IDs to delete
        """
        # For hybrid mode, node deletion is not supported
        if hasattr(self, 'hybrid_retriever') and self.hybrid_retriever:
            raise NotImplementedError("Node deletion not supported in hybrid mode")
        
        if self.local_index and hasattr(self.local_index, 'delete_nodes'):
            return self.local_index.delete_nodes(node_ids)
        raise NotImplementedError("Node deletion not supported")
    
    def get_retriever_info(self):
        """
        Get information about the configured retrievers.
        
        Returns:
            Dict: Retriever information
        """
        if hasattr(self.hybrid_retriever, 'get_retriever_info'):
            return self.hybrid_retriever.get_retriever_info()
        return {"type": "enhanced", "mode": "unknown"}
    
    # Backward compatibility methods
    def __getattr__(self, name):
        """
        Delegate unknown attributes to local_index for backward compatibility.
        
        Args:
            name: Attribute name
            
        Returns:
            Any: Attribute value from local_index
        """
        if self.local_index and hasattr(self.local_index, name):
            return getattr(self.local_index, name)
        raise AttributeError(f"'{self.__class__.__name__}' object has no attribute '{name}'")


def get_msg_history():
    """
        get the message history 
    """
    messages_history = [ChatMessage(role=MessageRole.USER 
                                    if msg["role"] == "user" 
                                    else MessageRole.ASSISTANT, 
                                    content=msg["content"])
                        for msg in st.session_state.messages]
    return messages_history


def convert_messages_to_bedrock_format(openai_messages):
    """
    Convert OpenAI format messages to Bedrock Claude format with validation
    
    Args:
        openai_messages: List of messages in OpenAI format
                        [{"role": "user", "content": "message"}, ...]
    
    Returns:
        List of messages in Bedrock Claude format
        [{"role": "user", "content": "message"}, ...]
        
    Raises:
        BedrockError: If message format is invalid
    """
    try:
        if not openai_messages:
            raise BedrockError("変換するメッセージがありません", "EmptyMessageList")
        
        if not isinstance(openai_messages, list):
            raise BedrockError("メッセージはリスト形式である必要があります", "InvalidMessageType")
        
        bedrock_messages = []
        system_messages = []  # Collect system messages separately
        valid_roles = {"user", "assistant", "system"}
        
        for i, msg in enumerate(openai_messages):
            try:
                # Validate message structure
                if not isinstance(msg, dict):
                    st.warning(f"メッセージ {i+1} が辞書形式ではありません。スキップします。")
                    continue
                
                if "role" not in msg or "content" not in msg:
                    st.warning(f"メッセージ {i+1} にroleまたはcontentが含まれていません。スキップします。")
                    continue
                
                role = msg["role"]
                content = msg["content"]
                
                # Validate role
                if role not in valid_roles:
                    st.warning(f"メッセージ {i+1} の無効なrole: {role}。スキップします。")
                    continue
                
                # Collect system messages separately for Claude 4.5
                if role == "system":
                    if content and isinstance(content, str) and len(content.strip()) > 0:
                        system_messages.append(content.strip())
                    continue
                
                # Validate content
                if not content or (isinstance(content, str) and len(content.strip()) == 0):
                    st.warning(f"メッセージ {i+1} の内容が空です。スキップします。")
                    continue
                
                # Ensure content is string
                if not isinstance(content, str):
                    content = str(content)
                
                # Convert role and content to Bedrock format
                # Use string format for compatibility with all Claude models
                bedrock_msg = {
                    "role": role,  # "user" or "assistant"
                    "content": content.strip()
                }
                
                bedrock_messages.append(bedrock_msg)
                
            except Exception as e:
                st.warning(f"メッセージ {i+1} の変換中にエラーが発生しました: {str(e)}。スキップします。")
                continue
        
        # Validate that we have at least one valid message
        if not bedrock_messages:
            raise BedrockError("変換後に有効なメッセージがありません", "NoValidMessagesAfterConversion")
        
        # Ensure conversation starts with user message
        if bedrock_messages[0]["role"] != "user":
            st.warning("会話はユーザーメッセージから開始する必要があります。")
        
        return bedrock_messages
        
    except BedrockError:
        # Re-raise BedrockError as-is
        raise
    except Exception as e:
        error_msg = f"メッセージ変換中に予期しないエラーが発生しました: {str(e)}"
        st.error(f"🔧 **変換エラー**: {error_msg}")
        raise BedrockError(error_msg, "MessageConversionError", e)


def bedrock_chat_completion(client, messages, model_id=None, **kwargs):
    """
    Bedrock chat completion function with comprehensive error handling
    
    Args:
        client: Bedrock Runtime client
        messages: List of messages in OpenAI format
        model_id: Bedrock model ID (uses session state if not provided)
        **kwargs: Additional parameters (max_tokens, temperature, etc.)
    
    Returns:
        Dictionary with response content and metadata
    """
    try:
        # Validate inputs
        if not client:
            raise BedrockError("Bedrockクライアントが初期化されていません", "ClientNotInitialized")
        
        if not messages or len(messages) == 0:
            raise BedrockError("メッセージが提供されていません", "EmptyMessages")
        
        # Use model from session state if not provided
        if model_id is None:
            model_id = st.session_state.get("bedrock_model")
            if not model_id:
                config = BedrockConfig()
                model_id = config.bedrock_model_id
        
        # Validate message format
        for i, msg in enumerate(messages):
            if not isinstance(msg, dict) or "role" not in msg or "content" not in msg:
                raise BedrockError(f"メッセージ {i+1} の形式が正しくありません", "InvalidMessageFormat")
        
        # Convert OpenAI format messages to Bedrock format
        try:
            bedrock_messages = convert_messages_to_bedrock_format(messages)
        except Exception as e:
            raise BedrockError(f"メッセージ変換に失敗しました: {str(e)}", "MessageConversionError", e)
        
        if not bedrock_messages:
            raise BedrockError("変換後のメッセージが空です", "EmptyConvertedMessages")
        
        # Prepare request body for Claude with validation
        max_tokens = kwargs.get("max_tokens", 1000)
        temperature = kwargs.get("temperature", 0.0)
        
        # Validate parameters - Claude 4+ models may have different limits
        max_token_limit = 8192 if ("claude-4" in model_id or "claude-sonnet-4" in model_id or "claude-haiku-4" in model_id or "claude-opus-4" in model_id) else 4096
        
        if not isinstance(max_tokens, int) or max_tokens < 1 or max_tokens > max_token_limit:
            st.warning(f"無効なmax_tokens値: {max_tokens}。デフォルト値1000を使用します。")
            max_tokens = 1000
        
        if not isinstance(temperature, (int, float)) or temperature < 0.0 or temperature > 1.0:
            st.warning(f"無効なtemperature値: {temperature}。デフォルト値0.0を使用します。")
            temperature = 0.0
        
        # Use appropriate API version based on model
        if "claude-4" in model_id or "sonnet-4" in model_id or "haiku-4" in model_id or "opus-4" in model_id:
            anthropic_version = "bedrock-2023-05-31"  # Claude 4+ models
        else:
            anthropic_version = "bedrock-2023-05-31"  # Standard version
        
        request_body = {
            "anthropic_version": anthropic_version,
            "max_tokens": max_tokens,
            "messages": bedrock_messages
        }
        
        # Add temperature if provided
        if temperature > 0.0:
            request_body["temperature"] = temperature
        
        # Add system prompt if provided in kwargs
        if "system_prompt" in kwargs and kwargs["system_prompt"]:
            if isinstance(kwargs["system_prompt"], str) and len(kwargs["system_prompt"].strip()) > 0:
                request_body["system"] = kwargs["system_prompt"].strip()
        
        # Log request details for debugging (without sensitive content)
        st.info(f"Bedrock API呼び出し: モデル={model_id}, メッセージ数={len(bedrock_messages)}, max_tokens={max_tokens}")
        
        # Debug: Log request body structure (without content)
        debug_info = {
            "anthropic_version": request_body.get("anthropic_version"),
            "max_tokens": request_body.get("max_tokens"),
            "temperature": request_body.get("temperature"),
            "has_system": "system" in request_body,
            "message_count": len(request_body.get("messages", [])),
            "message_roles": [msg.get("role") for msg in request_body.get("messages", [])]
        }
        print(f"DEBUG: Request structure: {debug_info}")
        
        # Call Bedrock API with retry logic
        response = robust_bedrock_call(client, model_id, request_body)
        
        # Parse and return response
        parsed_response = parse_bedrock_response(response)
        
        # Validate response
        if not parsed_response.get("content"):
            st.warning("Claudeからの応答が空でした。")
            parsed_response["content"] = "申し訳ございませんが、応答を生成できませんでした。"
        
        return parsed_response
        
    except BedrockError:
        # Re-raise BedrockError as-is (already has user-friendly message)
        raise
        
    except Exception as e:
        error_msg = f"チャット完了処理中に予期しないエラーが発生しました: {str(e)}"
        st.error(f"❌ **予期しないエラー**: {error_msg}")
        
        # Return error response in expected format
        return {
            "content": "申し訳ございませんが、リクエストの処理中にエラーが発生しました。しばらく時間を置いてから再度お試しください。",
            "usage": {"input_tokens": 0, "output_tokens": 0},
            "model": model_id or "",
            "stop_reason": "error",
            "id": "",
            "role": "assistant",
            "error": str(e)
        }


class BedrockError(Exception):
    """Custom exception class for Bedrock-related errors"""
    
    def __init__(self, message: str, error_code: str = None, original_error: Exception = None):
        super().__init__(message)
        self.error_code = error_code
        self.original_error = original_error


def get_user_friendly_error_message(error_code: str, error_message: str, model_id: str = None) -> str:
    """
    Convert AWS error codes to user-friendly messages with actionable guidance
    
    Args:
        error_code: AWS error code
        error_message: Original error message
        model_id: Bedrock model ID (if applicable)
    
    Returns:
        User-friendly error message with guidance
    """
    error_messages = {
        'ThrottlingException': {
            'title': '🚦 **レート制限に達しました**',
            'message': 'リクエストが多すぎます。しばらく待ってから再試行してください。',
            'action': '• 少し時間を置いてから再度お試しください\n• 同時リクエスト数を減らしてください'
        },
        'ValidationException': {
            'title': '📝 **リクエストパラメータエラー**',
            'message': f'リクエストの形式が正しくありません。\n\n**詳細エラー:** {error_message}',
            'action': f'• 入力内容を確認してください\n• メッセージが長すぎる場合は短くしてください\n• モデルID: {model_id if model_id else "未指定"}\n• Claude 4/4.5はinference profileを使用:\n  - Claude 4.5: us.anthropic.claude-sonnet-4-5-20250929-v1:0, us.anthropic.claude-haiku-4-5-20251001-v1:0\n  - Claude 4.0: us.anthropic.claude-sonnet-4-20250514-v1:0, us.anthropic.claude-opus-4-20250514-v1:0'
        },
        'AccessDeniedException': {
            'title': '🔒 **アクセス権限エラー**',
            'message': 'Bedrockサービスへのアクセス権限がありません。',
            'action': '• IAMポリシーでbedrock:InvokeModel権限を確認してください\n• AWS_SETUP.mdの権限設定を参照してください'
        },
        'ResourceNotFoundException': {
            'title': '🔍 **モデルが見つかりません**',
            'message': f'指定されたモデル ({model_id}) が利用できません。',
            'action': '• モデルIDが正しいか確認してください\n• 使用リージョンでモデルが利用可能か確認してください\n• Bedrockコンソールでモデルアクセスを有効にしてください'
        },
        'ServiceUnavailableException': {
            'title': '🔧 **サービス一時停止**',
            'message': 'Bedrockサービスが一時的に利用できません。',
            'action': '• しばらく時間を置いてから再試行してください\n• AWS Status Pageでサービス状況を確認してください'
        },
        'InternalServerException': {
            'title': '⚠️ **内部サーバーエラー**',
            'message': 'AWS側で内部エラーが発生しました。',
            'action': '• 少し時間を置いてから再試行してください\n• 問題が続く場合はAWSサポートにお問い合わせください'
        }
    }
    
    error_info = error_messages.get(error_code, {
        'title': f'❌ **予期しないエラー ({error_code})**',
        'message': error_message,
        'action': '• 設定を確認してください\n• 問題が続く場合はログを確認してください'
    })
    
    return f"{error_info['title']}\n\n{error_info['message']}\n\n**対処方法:**\n{error_info['action']}"


def robust_bedrock_call(client, model_id, request_body, max_retries=3):
    """
    Make Bedrock API call with comprehensive error handling and retry logic
    
    Args:
        client: Bedrock Runtime client
        model_id: Bedrock model ID
        request_body: Request payload for the model
        max_retries: Maximum number of retry attempts
    
    Returns:
        Raw Bedrock API response
        
    Raises:
        BedrockError: Custom exception with user-friendly error messages
    """
    last_error = None
    
    for attempt in range(max_retries):
        try:
            # Log attempt for debugging
            if attempt > 0:
                st.info(f"Bedrock API呼び出し試行 {attempt + 1}/{max_retries}")
            
            # Debug: Log request details on first attempt or if debugging is enabled
            if attempt == 0:
                print(f"DEBUG: Bedrock Request - Model: {model_id}")
                print(f"DEBUG: Request body keys: {list(request_body.keys())}")
                if 'messages' in request_body:
                    print(f"DEBUG: Messages count: {len(request_body['messages'])}")
                    for i, msg in enumerate(request_body['messages']):
                        print(f"DEBUG: Message {i}: role={msg.get('role')}, content_type={type(msg.get('content'))}")
            
            response = client.invoke_model(
                modelId=model_id,
                body=json.dumps(request_body)
            )
            
            # Success - log if this was a retry
            if attempt > 0:
                st.success(f"Bedrock API呼び出しが成功しました (試行 {attempt + 1})")
            
            return response
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_message = e.response['Error']['Message']
            last_error = e
            
            # Handle retryable errors
            if error_code in ['ThrottlingException', 'ServiceUnavailableException', 'InternalServerException']:
                if attempt < max_retries - 1:
                    wait_time = min(2 ** attempt, 30)  # Cap at 30 seconds
                    st.warning(f"一時的なエラーが発生しました。{wait_time}秒後に再試行します... (試行 {attempt + 1}/{max_retries})")
                    time.sleep(wait_time)
                    continue
            
            # Handle non-retryable errors immediately
            user_message = get_user_friendly_error_message(error_code, error_message, model_id)
            st.error(user_message)
            raise BedrockError(user_message, error_code, e)
                
        except json.JSONEncodeError as e:
            error_msg = "リクエストデータのJSON変換に失敗しました。"
            st.error(f"🔧 **データ形式エラー**: {error_msg}")
            raise BedrockError(error_msg, "JSONEncodeError", e)
            
        except Exception as e:
            last_error = e
            
            # Retry for unexpected errors
            if attempt < max_retries - 1:
                wait_time = min(2 ** attempt, 30)
                st.warning(f"予期しないエラーが発生しました。{wait_time}秒後に再試行します... (試行 {attempt + 1}/{max_retries})")
                time.sleep(wait_time)
                continue
            else:
                error_msg = f"Bedrock API呼び出し中に予期しないエラーが発生しました: {str(e)}"
                st.error(f"❌ **予期しないエラー**: {error_msg}")
                raise BedrockError(error_msg, "UnexpectedError", e)
    
    # If we get here, all retries failed
    final_error_msg = f"Bedrock API呼び出しが{max_retries}回の試行後に失敗しました。"
    if last_error:
        final_error_msg += f" 最後のエラー: {str(last_error)}"
    
    st.error(f"🔄 **再試行失敗**: {final_error_msg}")
    raise BedrockError(final_error_msg, "MaxRetriesExceeded", last_error)


def parse_bedrock_response(bedrock_response):
    """
    Parse Bedrock Claude response with comprehensive error handling
    
    Args:
        bedrock_response: Raw response from Bedrock invoke_model API
    
    Returns:
        Dictionary containing parsed response data
        
    Raises:
        BedrockError: If response parsing fails
    """
    try:
        # Validate response structure
        if not bedrock_response or 'body' not in bedrock_response:
            raise BedrockError("Bedrockレスポンスの形式が正しくありません", "InvalidResponseFormat")
        
        # Read the response body
        try:
            response_body = bedrock_response['body'].read()
        except Exception as e:
            raise BedrockError(f"レスポンスボディの読み取りに失敗しました: {str(e)}", "ResponseReadError", e)
        
        # Parse JSON
        try:
            response_json = json.loads(response_body)
        except json.JSONDecodeError as e:
            st.error(f"🔧 **JSON解析エラー**: レスポンスの解析に失敗しました")
            raise BedrockError(f"レスポンスのJSON解析に失敗しました: {str(e)}", "JSONParseError", e)
        
        # Validate response structure
        if not isinstance(response_json, dict):
            raise BedrockError("レスポンスが辞書形式ではありません", "InvalidResponseType")
        
        # Extract text content from Claude response
        content = ""
        if "content" in response_json:
            if isinstance(response_json["content"], list) and len(response_json["content"]) > 0:
                # Claude returns content as a list of content blocks
                for content_block in response_json["content"]:
                    if isinstance(content_block, dict) and content_block.get("type") == "text":
                        text_content = content_block.get("text", "")
                        if isinstance(text_content, str):
                            content += text_content
            elif isinstance(response_json["content"], str):
                # Handle direct string content
                content = response_json["content"]
        
        # Validate that we got some content
        if not content or not isinstance(content, str):
            st.warning("⚠️ Claudeからの応答が空でした")
            content = "申し訳ございませんが、応答を生成できませんでした。"
        
        # Extract and validate usage information
        usage = response_json.get("usage", {})
        if not isinstance(usage, dict):
            usage = {"input_tokens": 0, "output_tokens": 0}
        else:
            # Ensure usage has required fields with defaults
            usage = {
                "input_tokens": usage.get("input_tokens", 0),
                "output_tokens": usage.get("output_tokens", 0)
            }
        
        # Extract metadata with defaults
        parsed_response = {
            "content": content,
            "usage": usage,
            "model": response_json.get("model", ""),
            "stop_reason": response_json.get("stop_reason", ""),
            "id": response_json.get("id", ""),
            "role": response_json.get("role", "assistant")
        }
        
        # Log successful parsing for debugging
        token_info = f"入力: {usage['input_tokens']} トークン, 出力: {usage['output_tokens']} トークン"
        st.info(f"✅ レスポンス解析完了 ({token_info})")
        
        return parsed_response
        
    except BedrockError:
        # Re-raise BedrockError as-is
        raise
        
    except Exception as e:
        error_msg = f"レスポンス解析中に予期しないエラーが発生しました: {str(e)}"
        st.error(f"❌ **解析エラー**: {error_msg}")
        
        # Return error response in expected format
        return {
            "content": "レスポンスの解析中にエラーが発生しました。",
            "usage": {"input_tokens": 0, "output_tokens": 0},
            "model": "",
            "stop_reason": "error",
            "id": "",
            "role": "assistant",
            "error": str(e)
        }




