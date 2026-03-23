"""
Buck Converter LLMエージェント

このモジュールは、Buck Converter（降圧型DC-DCコンバーター）の設計支援のための
LLMベースのエージェント機能を提供します。
- 設計ガイドラインとベストプラクティス
- 専門的な設計アドバイス
- リップル解析機能
- 効率最適化提案

@reference: PE-GPT: a New Paradigm for Power Electronics Design
@code-author: Xinze Li, Fanfan Lin, Weihao Lei
"""

from typing import List, Dict, Optional
try:
    from .buck_design_calculator import BuckDesignCalculator, BuckSpecifications
except ImportError:
    from buck_design_calculator import BuckDesignCalculator, BuckSpecifications


class BuckLLMAgent:
    """Buck Converter専門LLMエージェント"""
    
    def __init__(self):
        self.design_calculator = BuckDesignCalculator()
        self.system_prompt = self._create_system_prompt()
        self.design_guidelines = self._load_design_guidelines()
        self.best_practices = self._load_best_practices()
    
    def _create_system_prompt(self) -> str:
        """Buck Converter専門システムプロンプト"""
        return """You are now an expert in the power electronics industry, 
                 and you are proficient in optimal design of buck converter. 
                 
                 Your expertise includes:
                 - Buck converter circuit topology and operation principles
                 - Component selection (inductors, capacitors, MOSFETs, diodes)
                 - Control methods (PWM, PFM, PSM)
                 - Efficiency optimization techniques
                 - Ripple current and voltage analysis
                 - Continuous Conduction Mode (CCM) and Discontinuous Conduction Mode (DCM)
                 - Thermal management and layout considerations
                 - EMI/EMC considerations
                 - Feedback control loop design
                 
                 Please provide detailed, technical guidance while being warm, positive and friendly. 
                 Keep your answers comprehensive but under 200 words unless detailed calculations 
                 are requested. Make sure your answers are professional and accurate -- don't hallucinate.
                 
                 When providing design advice, consider:
                 1. Application requirements (power level, efficiency, size)
                 2. Operating conditions (input voltage range, load variations)
                 3. Performance trade-offs (efficiency vs size, cost vs performance)
                 4. Industry best practices and standards"""
    
    def _load_design_guidelines(self) -> Dict[str, List[str]]:
        """設計ガイドライン"""
        return {
            "component_selection": [
                "インダクタ選定: リップル電流を出力電流の20-40%に設定",
                "出力キャパシタ: ESRとリップル電圧要件を考慮",
                "MOSFET選定: Ron、ゲート電荷、熱特性を評価",
                "ダイオード選定: 順方向電圧降下と逆回復時間を考慮"
            ],
            "frequency_selection": [
                "低電力(<10W): 50-200kHz - 小型化重視",
                "中電力(10-100W): 20-100kHz - バランス重視", 
                "高電力(>100W): 10-50kHz - 効率重視",
                "EMI要件に応じてスペクトラム拡散を検討"
            ],
            "control_methods": [
                "PWM制御: 一定周波数、線形制御特性",
                "PFM制御: 軽負荷時の効率向上",
                "PSM制御: 超軽負荷時のスタンバイ電力削減",
                "適応制御: 負荷に応じた制御方式切り替え"
            ],
            "layout_considerations": [
                "スイッチングループを最小化",
                "グランドプレーンの適切な配置",
                "熱設計とコンポーネント配置",
                "EMI対策（フィルタ、シールド）"
            ]
        }
    
    def _load_best_practices(self) -> Dict[str, List[str]]:
        """ベストプラクティス"""
        return {
            "efficiency_optimization": [
                "同期整流の採用でダイオード損失を削減",
                "適切なデッドタイムの設定",
                "ゼロ電圧スイッチング（ZVS）の活用",
                "低Ron値MOSFETの選択",
                "最適なスイッチング周波数の選定"
            ],
            "ripple_reduction": [
                "十分なインダクタンス値の確保",
                "低ESR出力キャパシタの使用",
                "マルチフェーズ構成の検討",
                "入力フィルタの適切な設計"
            ],
            "reliability": [
                "適切なディレーティング（80%ルール）",
                "温度サイクル耐性の考慮",
                "過電流・過電圧保護の実装",
                "ソフトスタート機能の追加"
            ],
            "cost_optimization": [
                "標準部品の活用",
                "統合コントローラICの使用",
                "PCB層数の最適化",
                "量産性を考慮した設計"
            ]
        }
    
    def get_enhanced_buck_expertise(self, query: str, messages_history: List[Dict] = None) -> str:
        """強化されたBuck Converter専門知識の提供"""
        
        # クエリの分析
        query_lower = query.lower()
        response_parts = []
        
        # 設計計算が必要かチェック
        if any(keyword in query_lower for keyword in ['calculate', '計算', 'design', '設計', 'component', '部品']):
            calc_result = self.design_calculator.provide_design_guidance(query)
            if "Buck Converter設計計算結果" in calc_result:
                response_parts.append(calc_result)
                return calc_result  # 計算結果がある場合はそれを返す
        
        # 特定のトピックに対する専門的回答
        if any(keyword in query_lower for keyword in ['efficiency', '効率', 'optimize', '最適化']):
            response_parts.append(self._provide_efficiency_guidance())
        
        if any(keyword in query_lower for keyword in ['ripple', 'リップル', 'noise', 'ノイズ']):
            response_parts.append(self._provide_ripple_guidance())
        
        if any(keyword in query_lower for keyword in ['component', '部品', 'selection', '選定']):
            response_parts.append(self._provide_component_guidance())
        
        if any(keyword in query_lower for keyword in ['control', '制御', 'pwm', 'pfm']):
            response_parts.append(self._provide_control_guidance())
        
        if any(keyword in query_lower for keyword in ['layout', 'レイアウト', 'pcb', 'emi']):
            response_parts.append(self._provide_layout_guidance())
        
        # 一般的なBuck Converter質問への回答
        if not response_parts:
            response_parts.append(self._provide_general_guidance(query))
        
        return "\n\n".join(response_parts)
    
    def _provide_efficiency_guidance(self) -> str:
        """効率最適化ガイダンス"""
        return """## Buck Converter効率最適化

**主要な効率向上手法:**

🔹 **同期整流の採用**
- ダイオードをMOSFETに置き換えて導通損失を大幅削減
- 特に低電圧出力で効果的

🔹 **最適なスイッチング周波数**
- 導通損失とスイッチング損失のバランス
- 高周波数: 小型化、低周波数: 高効率

🔹 **適切なMOSFET選択**
- 低Ron値で導通損失を削減
- 低ゲート電荷でスイッチング損失を削減

🔹 **デッドタイム最適化**
- 短すぎると貫通電流、長すぎるとボディダイオード導通

**効率測定のポイント:**
- 全負荷範囲での効率特性を確認
- 軽負荷時の効率も重要（PFM制御検討）"""
    
    def _provide_ripple_guidance(self) -> str:
        """リップル解析ガイダンス"""
        return """## Buck Converterリップル解析

**リップル電流の制御:**

🔹 **インダクタンス設計**
- L = (Vin-Vout) × D / (ΔIL × fsw)
- リップル電流を出力電流の20-40%に設定

🔹 **リップル電圧の制御**
- 出力キャパシタのESRが主要因
- 低ESRキャパシタ（セラミック、タンタル）を使用

🔹 **CCM/DCM動作**
- CCM: 連続導通、安定した制御
- DCM: 不連続導通、軽負荷時に発生

**リップル低減手法:**
- マルチフェーズ構成でリップル相殺
- 適切な入力フィルタ設計
- レイアウト最適化でノイズ低減"""
    
    def _provide_component_guidance(self) -> str:
        """部品選定ガイダンス"""
        return """## Buck Converter部品選定

**インダクタ選定:**
🔹 飽和電流 > ピーク電流 × 1.2
🔹 温度上昇 < 40°C
🔹 DCR（直流抵抗）を最小化

**出力キャパシタ選定:**
🔹 セラミック: 低ESR、高周波特性良好
🔹 電解: 大容量、コスト効果
🔹 タンタル: 中間特性、信頼性

**MOSFET選定:**
🔹 Vds > Vin × 1.5（安全率）
🔹 低Ron値で導通損失削減
🔹 低Qg値でスイッチング損失削減

**制御IC選定:**
🔹 入出力電圧範囲の確認
🔹 保護機能（OCP、OVP、UVLO）
🔹 制御方式（PWM/PFM切替）"""
    
    def _provide_control_guidance(self) -> str:
        """制御方式ガイダンス"""
        return """## Buck Converter制御方式

**PWM制御（Pulse Width Modulation）:**
🔹 一定周波数、デューティ比で出力制御
🔹 線形制御特性、設計が容易
🔹 中〜重負荷で高効率

**PFM制御（Pulse Frequency Modulation）:**
🔹 軽負荷時の効率向上
🔹 周波数変動によるEMI課題
🔹 オーディオノイズの可能性

**PSM制御（Pulse Skip Mode）:**
🔹 超軽負荷時のスタンバイ電力削減
🔹 間欠動作でさらなる省電力

**適応制御:**
🔹 負荷に応じた制御方式自動切替
🔹 全負荷範囲で最適効率を実現"""
    
    def _provide_layout_guidance(self) -> str:
        """レイアウトガイダンス"""
        return """## Buck Converter PCBレイアウト

**重要なレイアウト原則:**

🔹 **スイッチングループ最小化**
- Vin → MOSFET → インダクタ → 負荷のループ
- 高周波電流経路を短く

🔹 **グランド設計**
- 信号グランドとパワーグランドの分離
- 適切なグランドプレーン配置

🔹 **熱設計**
- MOSFETとインダクタの熱結合避ける
- 適切なビア配置で熱拡散

🔹 **EMI対策**
- 入力フィルタの適切な配置
- シールド構造の検討
- 高周波成分の抑制

**配線のポイント:**
- 太い配線でDC抵抗最小化
- 対称レイアウトでバランス改善"""
    
    def _provide_general_guidance(self, query: str) -> str:
        """一般的なガイダンス"""
        return """## Buck Converter設計支援

Buck Converter（降圧型DC-DCコンバーター）は、入力電圧より低い出力電圧を効率的に生成する回路です。

**基本動作原理:**
🔹 MOSFETのON/OFF制御で電圧を降圧
🔹 インダクタで電流を平滑化
🔹 出力キャパシタで電圧リップルを低減

**主要な設計パラメータ:**
- デューティ比: D = Vout/Vin
- インダクタンス: リップル電流で決定
- 出力キャパシタ: リップル電圧で決定
- スイッチング周波数: 効率と小型化のトレードオフ

**設計時の考慮事項:**
✅ 効率目標の設定
✅ 負荷変動への対応
✅ EMI/EMC要件
✅ 熱設計とサイズ制約

具体的な設計計算や詳細な質問があれば、お気軽にお聞かせください！"""
    
    def analyze_design_requirements(self, requirements: str) -> Dict[str, any]:
        """設計要件の分析"""
        analysis = {
            "power_level": "unknown",
            "application_type": "unknown", 
            "key_requirements": [],
            "recommended_approach": []
        }
        
        req_lower = requirements.lower()
        
        # 電力レベルの推定
        if any(word in req_lower for word in ['low power', '低電力', 'battery', 'バッテリー']):
            analysis["power_level"] = "low"
            analysis["recommended_approach"].append("高周波数設計で小型化重視")
        elif any(word in req_lower for word in ['high power', '高電力', 'motor', 'モーター']):
            analysis["power_level"] = "high"
            analysis["recommended_approach"].append("低周波数設計で効率重視")
        
        # アプリケーションタイプの推定
        if any(word in req_lower for word in ['automotive', '車載', 'industrial', '産業']):
            analysis["application_type"] = "industrial"
            analysis["recommended_approach"].append("高信頼性設計、広温度範囲対応")
        elif any(word in req_lower for word in ['consumer', '民生', 'portable', 'ポータブル']):
            analysis["application_type"] = "consumer"
            analysis["recommended_approach"].append("コスト最適化、小型化重視")
        
        return analysis