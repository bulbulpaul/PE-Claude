"""
Tests for Topology Detector

Tests automatic topology detection from user queries
"""

import sys
import os
import re
from typing import Dict, Tuple

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import directly without going through core.__init__
topology_detector_path = os.path.join(os.path.dirname(__file__), '..', 'core', 'topology', 'topology_detector.py')
import importlib.util
spec = importlib.util.spec_from_file_location("topology_detector", topology_detector_path)
topology_detector_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(topology_detector_module)

TopologyDetector = topology_detector_module.TopologyDetector
get_topology_detector = topology_detector_module.get_topology_detector


def test_pfc_detection_english():
    """Test PFC detection with English keywords"""
    detector = TopologyDetector()
    
    test_cases = [
        "I want to design a PFC converter",
        "Help me with power factor correction",
        "What is the best approach for AC-DC conversion with high power factor?",
        "I need to reduce THD in my power supply",
        "Design a boost PFC converter for 1000W"
    ]
    
    for query in test_cases:
        topology, confidence, details = detector.detect(query)
        print(f"\nQuery: {query}")
        print(f"Detected: {topology} (confidence: {confidence:.2%})")
        print(f"Matched keywords: {details['matched_keywords']}")
        assert topology == 'PFC', f"Expected PFC, got {topology}"
        assert confidence > 0.3, f"Low confidence: {confidence}"
    
    print("\n✓ PFC English detection tests passed")


def test_pfc_detection_japanese():
    """Test PFC detection with Japanese keywords"""
    detector = TopologyDetector()
    
    test_cases = [
        "PFC コンバーターの設計に関して相談をさせてください。",
        "力率改善回路を設計したいです",
        "AC-DC変換で高調波を減らしたい",
        "力率を0.99以上にする方法を教えてください",
        "THDを5%以下にしたい"
    ]
    
    for query in test_cases:
        topology, confidence, details = detector.detect(query)
        print(f"\nQuery: {query}")
        print(f"Detected: {topology} (confidence: {confidence:.2%})")
        print(f"Matched keywords: {details['matched_keywords']}")
        assert topology == 'PFC', f"Expected PFC, got {topology} for query: {query}"
        assert confidence > 0.3, f"Low confidence: {confidence} for query: {query}"
    
    print("\n✓ PFC Japanese detection tests passed")


def test_buck_detection_english():
    """Test Buck detection with English keywords"""
    detector = TopologyDetector()
    
    test_cases = [
        "I need help designing a buck converter",
        "How do I calculate the inductor for a step-down converter?",
        "Buck converter design for 12V to 5V",
        "What duty cycle should I use for my buck regulator?"
    ]
    
    for query in test_cases:
        topology, confidence, details = detector.detect(query)
        print(f"\nQuery: {query}")
        print(f"Detected: {topology} (confidence: {confidence:.2%})")
        assert topology == 'Buck', f"Expected Buck, got {topology}"
        assert confidence > 0.3, f"Low confidence: {confidence}"
    
    print("\n✓ Buck English detection tests passed")


def test_buck_detection_japanese():
    """Test Buck detection with Japanese keywords"""
    detector = TopologyDetector()
    
    test_cases = [
        "バックコンバーターの設計を手伝ってください",
        "降圧型コンバーターのインダクタンス計算",
        "ステップダウンコンバーターの効率を上げたい"
    ]
    
    for query in test_cases:
        topology, confidence, details = detector.detect(query)
        print(f"\nQuery: {query}")
        print(f"Detected: {topology} (confidence: {confidence:.2%})")
        assert topology == 'Buck', f"Expected Buck, got {topology}"
        assert confidence > 0.3, f"Low confidence: {confidence}"
    
    print("\n✓ Buck Japanese detection tests passed")


def test_dab_detection_english():
    """Test DAB detection with English keywords"""
    detector = TopologyDetector()
    
    test_cases = [
        "I want to design a dual active bridge converter",
        "Help me with DAB modulation strategies",
        "What is the best phase shift modulation for my DAB?",
        "I need to optimize ZVS range in my bidirectional converter"
    ]
    
    for query in test_cases:
        topology, confidence, details = detector.detect(query)
        print(f"\nQuery: {query}")
        print(f"Detected: {topology} (confidence: {confidence:.2%})")
        assert topology == 'DAB', f"Expected DAB, got {topology}"
        assert confidence > 0.3, f"Low confidence: {confidence}"
    
    print("\n✓ DAB English detection tests passed")


def test_dab_detection_japanese():
    """Test DAB detection with Japanese keywords"""
    detector = TopologyDetector()
    
    test_cases = [
        "デュアルアクティブブリッジの設計を教えてください",
        "DABコンバーターの変調方式について",
        "双方向コンバーターの位相シフト制御"
    ]
    
    for query in test_cases:
        topology, confidence, details = detector.detect(query)
        print(f"\nQuery: {query}")
        print(f"Detected: {topology} (confidence: {confidence:.2%})")
        assert topology == 'DAB', f"Expected DAB, got {topology}"
        assert confidence > 0.3, f"Low confidence: {confidence}"
    
    print("\n✓ DAB Japanese detection tests passed")


def test_unknown_detection():
    """Test detection with unclear queries"""
    detector = TopologyDetector()
    
    test_cases = [
        "Hello",
        "What is power electronics?",
        "Tell me about converters in general"
    ]
    
    for query in test_cases:
        topology, confidence, details = detector.detect(query)
        print(f"\nQuery: {query}")
        print(f"Detected: {topology} (confidence: {confidence:.2%})")
        # These should have low confidence or be Unknown
        assert confidence < 0.5 or topology == 'Unknown', f"Unexpected high confidence for unclear query"
    
    print("\n✓ Unknown detection tests passed")


def test_singleton_instance():
    """Test singleton pattern"""
    detector1 = get_topology_detector()
    detector2 = get_topology_detector()
    
    assert detector1 is detector2, "Singleton pattern not working"
    print("\n✓ Singleton instance test passed")


def test_topology_info():
    """Test topology information retrieval"""
    detector = TopologyDetector()
    
    for topology in ['PFC', 'Buck', 'DAB']:
        info = detector.get_topology_info(topology)
        assert 'full_name' in info
        assert 'japanese_name' in info
        assert 'tasks' in info
        assert 'description' in info
        print(f"\n{topology} Info:")
        print(f"  Full Name: {info['full_name']}")
        print(f"  Japanese: {info['japanese_name']}")
        print(f"  Tasks: {info['tasks']}")
    
    print("\n✓ Topology info test passed")


def run_all_tests():
    """Run all topology detector tests"""
    print("\n" + "="*60)
    print("Running Topology Detector Tests")
    print("="*60 + "\n")
    
    tests = [
        ("PFC Detection (English)", test_pfc_detection_english),
        ("PFC Detection (Japanese)", test_pfc_detection_japanese),
        ("Buck Detection (English)", test_buck_detection_english),
        ("Buck Detection (Japanese)", test_buck_detection_japanese),
        ("DAB Detection (English)", test_dab_detection_english),
        ("DAB Detection (Japanese)", test_dab_detection_japanese),
        ("Unknown Detection", test_unknown_detection),
        ("Singleton Instance", test_singleton_instance),
        ("Topology Info", test_topology_info),
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        try:
            print(f"\nRunning: {test_name}")
            print("-" * 60)
            test_func()
            passed += 1
        except Exception as e:
            print(f"✗ {test_name} FAILED: {str(e)}")
            import traceback
            traceback.print_exc()
            failed += 1
    
    print("\n" + "="*60)
    print(f"Test Results: {passed} passed, {failed} failed")
    print("="*60 + "\n")
    
    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
