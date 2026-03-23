"""
Buck Converter設計計算機能

このモジュールは、Buck Converter（降圧型DC-DCコンバーター）の設計計算機能を提供します。
- デューティ比計算
- インダクタンス計算
- キャパシタンス計算
- 効率最適化アルゴリズム
- リップル解析

@reference: PE-GPT: a New Paradigm for Power Electronics Design
@code-author: Xinze Li, Fanfan Lin, Weihao Lei
"""

import math
import re
from typing import Dict, Optional, Tuple, List
from dataclasses import dataclass


@dataclass
class BuckSpecifications:
    """Buck Converter設計仕様"""
    input_voltage: float  # 入力電圧 [V]
    output_voltage: float  # 出力電圧 [V]
    output_current: float  # 出力電流 [A]
    switching_frequency: float  # スイッチング周波数 [Hz]
    ripple_current_percent: float = 0.3  # リップル電流率 [%]
    ripple_voltage_percent: float = 0.01  # リップル電圧率 [%]
    efficiency_target: float = 0.9  # 目標効率


@dataclass
class BuckDesignResults:
    """Buck Converter設計結果"""
    duty_cycle: float  # デューティ比
    inductor_value: float  # インダクタンス [H]
    capacitor_value: float  # キャパシタンス [F]
    peak_inductor_current: float  # インダクタピーク電流 [A]
    rms_inductor_current: float  # インダクタRMS電流 [A]
    output_power: float  # 出力電力 [W]
    estimated_efficiency: float  # 推定効率
    ripple_current: float  # リップル電流 [A]
    ripple_voltage: float  # リップル電圧 [V]


class BuckDesignCalculator:
    """Buck Converter設計計算クラス"""
    
    def __init__(self):
        self.design_templates = {
            "low_power": {"fsw_range": (50e3, 200e3), "ripple_current": 0.3},
            "medium_power": {"fsw_range": (20e3, 100e3), "ripple_current": 0.25},
            "high_power": {"fsw_range": (10e3, 50e3), "ripple_current": 0.2}
        }
    
    def calculate_basic_parameters(self, specs: BuckSpecifications) -> BuckDesignResults:
        """基本パラメータの計算"""
        
        # デューティ比計算
        duty_cycle = specs.output_voltage / specs.input_voltage
        
        # 出力電力計算
        output_power = specs.output_voltage * specs.output_current
        
        # インダクタンス計算
        # L = (Vin - Vout) * D / (ΔIL * fsw)
        ripple_current = specs.output_current * specs.ripple_current_percent
        inductor_value = ((specs.input_voltage - specs.output_voltage) * duty_cycle) / \
                        (ripple_current * specs.switching_frequency)
        
        # キャパシタンス計算
        # C = ΔIL / (8 * fsw * ΔVout)
        ripple_voltage = specs.output_voltage * specs.ripple_voltage_percent
        capacitor_value = ripple_current / (8 * specs.switching_frequency * ripple_voltage)
        
        # インダクタ電流計算
        peak_inductor_current = specs.output_current + ripple_current / 2
        rms_inductor_current = math.sqrt(specs.output_current**2 + (ripple_current**2) / 12)
        
        # 効率推定（簡易モデル）
        estimated_efficiency = self._estimate_efficiency(specs, duty_cycle, rms_inductor_current)
        
        return BuckDesignResults(
            duty_cycle=duty_cycle,
            inductor_value=inductor_value,
            capacitor_value=capacitor_value,
            peak_inductor_current=peak_inductor_current,
            rms_inductor_current=rms_inductor_current,
            output_power=output_power,
            estimated_efficiency=estimated_efficiency,
            ripple_current=ripple_current,
            ripple_voltage=ripple_voltage
        )
    
    def _estimate_efficiency(self, specs: BuckSpecifications, duty_cycle: float, 
                           rms_current: float) -> float:
        """効率推定（簡易モデル）"""
        # 導通損失の推定
        ron_mosfet = 0.01  # MOSFET on抵抗 [Ω] (仮定値)
        ron_diode = 0.02   # ダイオード抵抗 [Ω] (仮定値)
        vf_diode = 0.7     # ダイオード順方向電圧 [V]
        
        # スイッチング損失の推定
        switching_loss_factor = 1e-6  # スイッチング損失係数 (仮定値)
        
        # 導通損失
        mosfet_conduction_loss = ron_mosfet * (rms_current**2) * duty_cycle
        diode_conduction_loss = (ron_diode * (rms_current**2) + vf_diode * specs.output_current) * (1 - duty_cycle)
        
        # スイッチング損失
        switching_loss = switching_loss_factor * specs.switching_frequency * specs.input_voltage * specs.output_current
        
        # 総損失
        total_loss = mosfet_conduction_loss + diode_conduction_loss + switching_loss
        
        # 効率計算
        efficiency = specs.output_voltage * specs.output_current / \
                    (specs.output_voltage * specs.output_current + total_loss)
        
        return min(efficiency, 0.98)  # 最大効率を98%に制限
    
    def optimize_efficiency(self, specs: BuckSpecifications) -> Tuple[BuckDesignResults, List[str]]:
        """効率最適化"""
        recommendations = []
        
        # 最適なスイッチング周波数の提案
        power_level = specs.output_voltage * specs.output_current
        
        if power_level < 10:  # 低電力
            optimal_fsw_range = self.design_templates["low_power"]["fsw_range"]
            recommendations.append("低電力アプリケーションのため、高いスイッチング周波数（50-200kHz）を推奨します。")
        elif power_level < 100:  # 中電力
            optimal_fsw_range = self.design_templates["medium_power"]["fsw_range"]
            recommendations.append("中電力アプリケーションのため、中程度のスイッチング周波数（20-100kHz）を推奨します。")
        else:  # 高電力
            optimal_fsw_range = self.design_templates["high_power"]["fsw_range"]
            recommendations.append("高電力アプリケーションのため、低いスイッチング周波数（10-50kHz）を推奨します。")
        
        # 現在の周波数が最適範囲内かチェック
        if not (optimal_fsw_range[0] <= specs.switching_frequency <= optimal_fsw_range[1]):
            optimal_fsw = (optimal_fsw_range[0] + optimal_fsw_range[1]) / 2
            recommendations.append(f"効率向上のため、スイッチング周波数を{optimal_fsw/1000:.1f}kHz付近に調整することを推奨します。")
            
            # 最適化された仕様で再計算
            optimized_specs = BuckSpecifications(
                input_voltage=specs.input_voltage,
                output_voltage=specs.output_voltage,
                output_current=specs.output_current,
                switching_frequency=optimal_fsw,
                ripple_current_percent=specs.ripple_current_percent,
                ripple_voltage_percent=specs.ripple_voltage_percent,
                efficiency_target=specs.efficiency_target
            )
            results = self.calculate_basic_parameters(optimized_specs)
        else:
            results = self.calculate_basic_parameters(specs)
            recommendations.append("現在のスイッチング周波数は適切な範囲内です。")
        
        # その他の最適化提案
        if results.duty_cycle < 0.2:
            recommendations.append("デューティ比が低いため、入力電圧を下げるか、出力電圧を上げることを検討してください。")
        elif results.duty_cycle > 0.8:
            recommendations.append("デューティ比が高いため、入力電圧を上げるか、出力電圧を下げることを検討してください。")
        
        if results.estimated_efficiency < specs.efficiency_target:
            recommendations.append("目標効率に達していません。同期整流やより低いRon値のMOSFETの使用を検討してください。")
        
        return results, recommendations
    
    def analyze_ripple(self, specs: BuckSpecifications) -> Dict[str, any]:
        """リップル解析"""
        results = self.calculate_basic_parameters(specs)
        
        # CCM/DCM判定
        critical_inductance = ((specs.input_voltage - specs.output_voltage) * specs.output_voltage) / \
                            (2 * specs.switching_frequency * specs.output_current * specs.input_voltage)
        
        operation_mode = "CCM" if results.inductor_value > critical_inductance else "DCM"
        
        # リップル分析結果
        ripple_analysis = {
            "operation_mode": operation_mode,
            "critical_inductance": critical_inductance,
            "actual_inductance": results.inductor_value,
            "ripple_current_percent": (results.ripple_current / specs.output_current) * 100,
            "ripple_voltage_percent": (results.ripple_voltage / specs.output_voltage) * 100,
            "recommendations": []
        }
        
        # 推奨事項
        if operation_mode == "DCM":
            ripple_analysis["recommendations"].append("不連続導通モード（DCM）で動作しています。連続導通モード（CCM）にするためインダクタンスを増加してください。")
        
        if ripple_analysis["ripple_current_percent"] > 40:
            ripple_analysis["recommendations"].append("リップル電流が大きすぎます。インダクタンスを増加するか、スイッチング周波数を上げてください。")
        
        if ripple_analysis["ripple_voltage_percent"] > 2:
            ripple_analysis["recommendations"].append("リップル電圧が大きすぎます。出力キャパシタンスを増加してください。")
        
        return ripple_analysis
    
    def extract_specs_from_text(self, text: str) -> Optional[BuckSpecifications]:
        """テキストから設計仕様を抽出"""
        try:
            # 電圧の抽出パターン
            vin_pattern = r'(?:入力電圧|input.*voltage|vin).*?(\d+(?:\.\d+)?)\s*[vV]'
            vout_pattern = r'(?:出力電圧|output.*voltage|vout).*?(\d+(?:\.\d+)?)\s*[vV]'
            
            # 電流の抽出パターン
            iout_pattern = r'(?:出力電流|output.*current|iout).*?(\d+(?:\.\d+)?)\s*[aA]'
            
            # 周波数の抽出パターン
            fsw_pattern = r'(?:スイッチング周波数|switching.*frequency|fsw).*?(\d+(?:\.\d+)?)\s*(?:khz|kHz|KHz|hz|Hz)'
            
            vin_match = re.search(vin_pattern, text, re.IGNORECASE)
            vout_match = re.search(vout_pattern, text, re.IGNORECASE)
            iout_match = re.search(iout_pattern, text, re.IGNORECASE)
            fsw_match = re.search(fsw_pattern, text, re.IGNORECASE)
            
            if vin_match and vout_match and iout_match:
                vin = float(vin_match.group(1))
                vout = float(vout_match.group(1))
                iout = float(iout_match.group(1))
                
                # スイッチング周波数のデフォルト値
                fsw = 100e3  # 100kHz
                if fsw_match:
                    fsw_value = float(fsw_match.group(1))
                    # kHzかHzかを判定
                    if 'khz' in text.lower():
                        fsw = fsw_value * 1000
                    else:
                        fsw = fsw_value
                
                return BuckSpecifications(
                    input_voltage=vin,
                    output_voltage=vout,
                    output_current=iout,
                    switching_frequency=fsw
                )
        except Exception as e:
            print(f"仕様抽出エラー: {e}")
            return None
        
        return None
    
    def provide_design_guidance(self, user_input: str) -> str:
        """設計ガイダンスの提供"""
        # テキストから仕様を抽出
        specs = self.extract_specs_from_text(user_input)
        
        if specs is None:
            return """Buck Converter設計計算を行うには、以下の情報が必要です：
            
**必要な仕様:**
- 入力電圧 (Vin) [V]
- 出力電圧 (Vout) [V]  
- 出力電流 (Iout) [A]
- スイッチング周波数 (fsw) [kHz] (オプション、デフォルト100kHz)

**例:** 入力電圧12V、出力電圧5V、出力電流2A、スイッチング周波数100kHzでBuck Converterを設計してください。"""
        
        # 基本計算実行
        results = self.calculate_basic_parameters(specs)
        
        # 効率最適化
        optimized_results, recommendations = self.optimize_efficiency(specs)
        
        # リップル解析
        ripple_analysis = self.analyze_ripple(specs)
        
        # 結果をフォーマット
        guidance = f"""
## Buck Converter設計計算結果

### 入力仕様
- 入力電圧: {specs.input_voltage:.1f}V
- 出力電圧: {specs.output_voltage:.1f}V
- 出力電流: {specs.output_current:.1f}A
- スイッチング周波数: {specs.switching_frequency/1000:.1f}kHz

### 設計パラメータ
- **デューティ比**: {results.duty_cycle:.3f} ({results.duty_cycle*100:.1f}%)
- **インダクタンス**: {results.inductor_value*1e6:.1f}μH
- **キャパシタンス**: {results.capacitor_value*1e6:.1f}μF
- **出力電力**: {results.output_power:.1f}W

### 電流解析
- ピーク電流: {results.peak_inductor_current:.2f}A
- RMS電流: {results.rms_inductor_current:.2f}A
- リップル電流: {results.ripple_current:.3f}A ({(results.ripple_current/specs.output_current)*100:.1f}%)

### 動作モード
- **動作モード**: {ripple_analysis['operation_mode']}
- 臨界インダクタンス: {ripple_analysis['critical_inductance']*1e6:.1f}μH

### 効率推定
- **推定効率**: {results.estimated_efficiency*100:.1f}%

### 最適化提案
"""
        
        for rec in recommendations:
            guidance += f"- {rec}\n"
        
        if ripple_analysis['recommendations']:
            guidance += "\n### リップル解析結果\n"
            for rec in ripple_analysis['recommendations']:
                guidance += f"- {rec}\n"
        
        return guidance