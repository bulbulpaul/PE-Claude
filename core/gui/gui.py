"""
@reference: PE-GPT: a New Paradigm for Power Electronics Design, by Fanfan Lin, Xinze Li, et al.
@code-author: Xinze Li, Fanfan Lin, Weihao Lei
@github: https://github.com/XinzeLee/PE-GPT

@reference:
    Following references are related to power electronics GPT (PE-GPT)
    1: PE-GPT: a New Paradigm for Power Electronics Design
        Authors: Fanfan Lin, Xinze Li (corresponding), Weihao Lei, Juan J. Rodriguez-Andina, Josep M. Guerrero, Changyun Wen, Xin Zhang, and Hao Ma
        Paper DOI: 10.1109/TIE.2024.3454408
"""


import streamlit as st
import numpy as np
import re




def build_gui():
    """
        Create a graphical user interface (GUI) using streamlit
    """
    
    # Graphical User Interface
    st.set_page_config(page_title="PE-GPT", page_icon="💎", layout="centered",
                       initial_sidebar_state="auto", menu_items=None)
    
    # Initialize KnowledgeBase settings
    init_kb_settings()
    st.title("Chat with the Power electronic robot🤖")
    st.info( "Hello, I am a robot specifically for power electronics design!", icon="🤟")
    
    with st.sidebar:
        st.markdown("<h1 style='color: #FF5733;'>PE-GPT (v2.0)</h1>", unsafe_allow_html=True)
        st.markdown('---')
        
        # Knowledge Base Status Panel
        st.markdown("### 🔍 Knowledge Base Status")
        
        # Load configuration from environment variables
        from core.knowledge.kb_config import load_config_from_env
        import os
        
        # Debug: Show environment variables
        with st.expander("🔧 デバッグ情報"):
            st.write("**環境変数の状態:**")
            env_vars = [
                'BEDROCK_KB_ID', 'BEDROCK_KB_REGION', 'BEDROCK_KB_MODE',
                'BEDROCK_KB_TOP_K', 'BEDROCK_KB_CONFIDENCE_THRESHOLD',
                'AWS_ACCESS_KEY_ID', 'AWS_SECRET_ACCESS_KEY', 'AWS_DEFAULT_REGION'
            ]
            for var in env_vars:
                value = os.getenv(var)
                if var in ['AWS_ACCESS_KEY_ID', 'AWS_SECRET_ACCESS_KEY']:
                    # Mask sensitive values
                    display_value = f"{value[:4]}***{value[-4:]}" if value and len(value) > 8 else "未設定" if not value else "設定済み"
                else:
                    display_value = value if value else "未設定"
                st.write(f"- `{var}`: {display_value}")
        
        kb_config = load_config_from_env()
        if kb_config:
            st.success(f"✅ Bedrock KnowledgeBase設定済み")
            st.info(f"**Mode:** {kb_config.mode}")
            st.info(f"**KnowledgeBase ID:** {kb_config.knowledge_base_id}")
            st.info(f"**Region:** {kb_config.region}")
            st.info(f"**Top K:** {kb_config.similarity_top_k}")
            st.info(f"**Confidence Threshold:** {kb_config.confidence_threshold}")
            
            # Test connection button
            if st.button("🔍 接続テスト"):
                with st.spinner("Bedrock KnowledgeBaseへの接続をテスト中..."):
                    try:
                        from core.llm.bedrock_kb_retriever import BedrockKnowledgeBaseRetriever
                        retriever = BedrockKnowledgeBaseRetriever(kb_config)
                        # Test with a simple query
                        results = retriever.retrieve("test query")
                        st.success(f"✅ 接続成功! {len(results)}件の結果を取得しました")
                    except Exception as e:
                        st.error(f"❌ 接続失敗: {str(e)}")
                        st.info("詳細なエラー情報については、ログを確認してください")
            
            # Store config in session state for use by other components
            st.session_state["kb_config"] = kb_config
            st.session_state["kb_config_changed"] = True
        else:
            st.warning("⚠️ Bedrock KnowledgeBase未設定")
            st.info("環境変数 `BEDROCK_KB_ID` を設定してください")
            
            # Show example configuration
            with st.expander("設定例"):
                st.code("""
export BEDROCK_KB_ID=ABCDEFGHIJ
export BEDROCK_KB_REGION=us-east-1
export BEDROCK_KB_MODE=hybrid
export BEDROCK_KB_TOP_K=5
export BEDROCK_KB_CONFIDENCE_THRESHOLD=0.0
                """, language="bash")
            
            # Set local mode as fallback
            st.session_state["kb_config"] = None
            st.info("ℹ️ ローカルファイルのみを使用")
        
        st.markdown('---')
        
        #st.markdown('\n- SPS:\n- EPS\n- DPS\n- TPS\n- 5DOF')
        st.markdown('\n- PE-GPT (v2.0) supports the design of modulation strategies for dual-active-bridge converters and circuit for buck converters.')
        st.markdown('\n- This repo highlights the software architecture with necessary submodules for your customized PE design tasks ')
        st.markdown('\n- @Reference: PE-GPT: a New Paradigm for Power Electronics Design ')
        st.markdown('\n- @Authors: Fanfan Lin, Xinze Li, et al. ')
        st.markdown('\n- @GitHub: https://github.com/XinzeLee/PE-GPT ')
        st.markdown('---')
        
    clear_button = st.sidebar.button('Clear Conversation',key='clear')
    # Create a scroll down selection box
    file_type = st.sidebar.selectbox("Select file type", ("vp", "vs", "iL"))
    # Create a file uploader
    uploaded_file = st.sidebar.file_uploader("Upload file", key="file_uploader")
    
    # A buttom to confirm file upload
    if st.sidebar.button("Confirm Upload"):
        if uploaded_file is not None:
            # load data for training
            upload_func(uploaded_file, file_type)
    
            # Notifications that file has been uploaded successfully
            st.sidebar.write(f"{file_type} file uploaded successfully.")
    
    # Provide initial guiding prompt after clicking the clear button
    with open('core/knowledge/prompts/prompt.txt', 'r') as file:
        content1 = file.read()
    with open('core/knowledge/prompts/init_reply.txt', 'r') as file:
        reply = file.read()
        
    if clear_button or ("messages" not in st.session_state):  # Initialize the chat messages history
        st.session_state.messages = [{"role": "user", "content": content1},
                                     {"role": "assistant", "content": reply},]


def upload_func(uploaded_file, file_type):
    """
        A function linked to the file upload button
    """
    
    if file_type == "vp":
        st.session_state.vp = np.loadtxt(uploaded_file, skiprows=1, delimiter=',')
    elif file_type == "vs":
        st.session_state.vs = np.loadtxt(uploaded_file, skiprows=1, delimiter=',')
    elif file_type == "iL":
        st.session_state.iL = np.loadtxt(uploaded_file, skiprows=1, delimiter=',')
    

def init_states(initial_values):
    """
        initialize st.session_state
    """
    for key, value in initial_values.items():
        if key not in st.session_state:
            st.session_state[key] = value


def init_kb_settings():
    """
    KnowledgeBase設定の初期化（環境変数ベース）
    """
    # 環境変数から設定を読み込み、セッション状態に保存
    from core.knowledge.kb_config import load_config_from_env
    kb_config = load_config_from_env()
    st.session_state["kb_config"] = kb_config
    st.session_state["kb_config_changed"] = True if kb_config else False


def get_current_kb_config():
    """
    現在のKnowledgeBase設定を取得する（環境変数から）
    
    Returns:
        KnowledgeBaseConfig or None: 現在の設定オブジェクト
    """
    from core.knowledge.kb_config import load_config_from_env
    return load_config_from_env()


def is_kb_config_changed():
    """
    KnowledgeBase設定が変更されたかどうかを確認する（環境変数ベースでは常にFalse）
    
    Returns:
        bool: 常にFalse（環境変数は実行時に固定）
    """
    return False


def reset_kb_config_changed_flag():
    """
    設定変更フラグをリセットする（環境変数ベースでは何もしない）
    """
    pass


def display_history():
    """
        Display the historical chat messages
    """
    for msg in st.session_state.messages[2:]:  # Display the prior chat messages
        with st.chat_message(msg["role"]):
            st.write(msg["content"])
            if "images" in msg:
                st.image(msg["images"])



