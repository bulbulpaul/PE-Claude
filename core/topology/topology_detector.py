"""
Topology Detection Module

Automatically detects converter topology from user queries
to route to appropriate design tasks.
"""

import re
from typing import Dict, Tuple


class TopologyDetector:
    """
    Detects converter topology from user input text
    """
    
    # Keyword patterns for each topology
    TOPOLOGY_KEYWORDS = {
        'PFC': {
            'english': [
                'pfc', 'power factor correction', 'power factor', 
                'ac-dc', 'ac dc', 'ac to dc', 'thd', 
                'total harmonic distortion', 'harmonic', 
                'boost pfc', 'ccm', 'dcm', 'bcm'
            ],
            'japanese': [
                '力率', '力率改善', '力率補正', 'pfc', 'pfcコンバーター',
                '交流直流', '交流直流変換', 'ac-dc', '高調波', '歪み率',
                'thd', '全高調波歪'
            ]
        },
        'Buck': {
            'english': [
                'buck', 'buck converter', 'step-down', 'step down',
                'dc-dc buck', 'buck regulator', 'switching regulator',
                'voltage reduction', '降圧'
            ],
            'japanese': [
                'バック', 'バックコンバーター', 'バックコンバータ',
                '降圧', '降圧コンバーター', '降圧型', 'ステップダウン'
            ]
        },
        'DAB': {
            'english': [
                'dab', 'dual active bridge', 'bidirectional',
                'isolated dc-dc', 'phase shift', 'sps', 'dps', 'eps', 'tps',
                '5dof', 'dual bridge'
            ],
            'japanese': [
                'デュアルアクティブブリッジ', 'dab', '双方向',
                '絶縁型', '位相シフト', 'フェーズシフト'
            ]
        }
    }
    
    # Weight for different match types
    WEIGHTS = {
        'exact_match': 10,
        'partial_match': 5,
        'context_match': 2
    }
    
    def __init__(self):
        """Initialize topology detector"""
        self.detection_history = []
    
    def detect(self, user_input: str) -> Tuple[str, float, Dict]:
        """
        Detect topology from user input
        
        Args:
            user_input: User's query text
        
        Returns:
            Tuple of (topology, confidence, details)
            - topology: 'PFC', 'Buck', 'DAB', or 'Unknown'
            - confidence: Confidence score (0-1)
            - details: Dictionary with detection details
        """
        if not user_input or not isinstance(user_input, str):
            return 'Unknown', 0.0, {'reason': 'Empty or invalid input'}
        
        # Normalize input
        text_lower = user_input.lower().strip()
        
        # Score each topology
        scores = {
            'PFC': self._score_topology(text_lower, 'PFC'),
            'Buck': self._score_topology(text_lower, 'Buck'),
            'DAB': self._score_topology(text_lower, 'DAB')
        }
        
        # Find best match
        best_topology = max(scores, key=scores.get)
        best_score = scores[best_topology]
        
        # Calculate confidence (normalize to 0-1)
        max_possible_score = self.WEIGHTS['exact_match'] * 3  # Assume 3 keyword matches max
        confidence = min(best_score / max_possible_score, 1.0)
        
        # Determine if detection is reliable
        if confidence < 0.3:
            topology = 'Unknown'
            reason = 'No clear topology indicators found'
        else:
            topology = best_topology
            reason = f'Detected based on keyword matches (score: {best_score})'
        
        details = {
            'scores': scores,
            'reason': reason,
            'input_length': len(user_input),
            'matched_keywords': self._get_matched_keywords(text_lower, topology)
        }
        
        # Store in history
        self.detection_history.append({
            'input': user_input,
            'topology': topology,
            'confidence': confidence,
            'details': details
        })
        
        return topology, confidence, details
    
    def _score_topology(self, text: str, topology: str) -> float:
        """
        Calculate score for a specific topology
        
        Args:
            text: Normalized user input
            topology: Topology name ('PFC', 'Buck', 'DAB')
        
        Returns:
            Score value
        """
        score = 0.0
        keywords = self.TOPOLOGY_KEYWORDS.get(topology, {})
        
        # Check English keywords
        for keyword in keywords.get('english', []):
            if keyword in text:
                # Exact word match gets higher score
                if re.search(r'\b' + re.escape(keyword) + r'\b', text):
                    score += self.WEIGHTS['exact_match']
                else:
                    score += self.WEIGHTS['partial_match']
        
        # Check Japanese keywords
        for keyword in keywords.get('japanese', []):
            if keyword in text:
                score += self.WEIGHTS['exact_match']
        
        # Context-based scoring
        score += self._context_score(text, topology)
        
        return score
    
    def _context_score(self, text: str, topology: str) -> float:
        """
        Calculate context-based score
        
        Args:
            text: Normalized user input
            topology: Topology name
        
        Returns:
            Context score
        """
        score = 0.0
        
        # PFC context
        if topology == 'PFC':
            if any(word in text for word in ['設計', 'design', '相談', 'consult', '質問', 'question']):
                score += self.WEIGHTS['context_match']
            if any(word in text for word in ['効率', 'efficiency', '性能', 'performance']):
                score += self.WEIGHTS['context_match']
        
        # Buck context
        elif topology == 'Buck':
            if any(word in text for word in ['dc-dc', 'dcdc', '電圧', 'voltage']):
                score += self.WEIGHTS['context_match']
            if any(word in text for word in ['デューティ', 'duty', 'pwm']):
                score += self.WEIGHTS['context_match']
        
        # DAB context
        elif topology == 'DAB':
            if any(word in text for word in ['変調', 'modulation', '位相', 'phase']):
                score += self.WEIGHTS['context_match']
            if any(word in text for word in ['zvs', 'zcs', 'soft switching', 'ソフトスイッチング']):
                score += self.WEIGHTS['context_match']
        
        return score
    
    def _get_matched_keywords(self, text: str, topology: str) -> list:
        """
        Get list of matched keywords for a topology
        
        Args:
            text: Normalized user input
            topology: Topology name
        
        Returns:
            List of matched keywords
        """
        matched = []
        keywords = self.TOPOLOGY_KEYWORDS.get(topology, {})
        
        for keyword in keywords.get('english', []) + keywords.get('japanese', []):
            if keyword in text:
                matched.append(keyword)
        
        return matched
    
    def get_detection_history(self) -> list:
        """
        Get detection history
        
        Returns:
            List of detection records
        """
        return self.detection_history
    
    def clear_history(self):
        """Clear detection history"""
        self.detection_history = []
    
    def get_topology_info(self, topology: str) -> Dict:
        """
        Get information about a topology
        
        Args:
            topology: Topology name
        
        Returns:
            Dictionary with topology information
        """
        info = {
            'PFC': {
                'full_name': 'Power Factor Correction Converter',
                'japanese_name': '力率改善コンバーター',
                'tasks': ['Task 6: evaluate_pfc', 'Task 7: build_pfc_pann'],
                'description': 'AC-DC converter for power factor correction'
            },
            'Buck': {
                'full_name': 'Buck Converter',
                'japanese_name': 'バックコンバーター（降圧型）',
                'tasks': ['Task 8: design_buck_converter'],
                'description': 'Step-down DC-DC converter'
            },
            'DAB': {
                'full_name': 'Dual Active Bridge Converter',
                'japanese_name': 'デュアルアクティブブリッジコンバーター',
                'tasks': ['Task 0-5: DAB design tasks'],
                'description': 'Bidirectional isolated DC-DC converter'
            }
        }
        
        return info.get(topology, {
            'full_name': 'Unknown',
            'japanese_name': '不明',
            'tasks': [],
            'description': 'Topology not recognized'
        })


# Singleton instance
_detector_instance = None

def get_topology_detector() -> TopologyDetector:
    """
    Get singleton topology detector instance
    
    Returns:
        TopologyDetector instance
    """
    global _detector_instance
    if _detector_instance is None:
        _detector_instance = TopologyDetector()
    return _detector_instance
