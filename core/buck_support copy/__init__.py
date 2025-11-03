"""
Buck Converter設計支援システム

このモジュールは、Buck Converter（降圧型DC-DCコンバーター）の設計支援機能を提供します。
- LLMベースの設計ガイダンス
- 設計計算機能
- 効率最適化アルゴリズム
- リップル解析機能

@reference: PE-GPT: a New Paradigm for Power Electronics Design
@code-author: Xinze Li, Fanfan Lin, Weihao Lei
"""

__version__ = "1.0.0"
__author__ = "PE-GPT Team"

from .buck_design_calculator import BuckDesignCalculator
from .buck_llm_agent import BuckLLMAgent

__all__ = [
    "BuckDesignCalculator",
    "BuckLLMAgent"
]