#!/usr/bin/env python3
import logging
from typing import Dict, List
from datetime import datetime

logger = logging.getLogger("scoring_engine")

class ScoringEngine:
    """Aggregate security scores and make decision"""
    
    def __init__(self, threshold: float = 70.0):
        self.threshold = threshold
        self.max_score = 100
        
        # Weight distribution
        self.weights = {
            "cve_check": 0.30,      # 30%
            "semantic_check": 0.30,  # 30%
            "runtime_check": 0.40    # 40%
        }
    
    def calculate_score(
        self,
        cve_result: Dict,
        semantic_result: Dict,
        runtime_result: Dict
    ) -> Dict:
        """
        Aggregate scores from all checks
        Returns: {
            "total_score": 0-100,
            "is_safe": bool,
            "risk_level": "low|medium|high|critical",
            "details": {}
        }
        """
        logger.info("Calculating aggregate security score...")
        
        # Extract individual scores
        cve_score = cve_result.get("score", 0)
        cve_max = cve_result.get("max_score", 30)
        
        semantic_score = semantic_result.get("score", 0)
        semantic_max = semantic_result.get("max_score", 30)
        
        runtime_score = runtime_result.get("score", 0)
        runtime_max = runtime_result.get("max_score", 40)
        
        # Normalize scores to 0-100
        cve_normalized = (cve_score / cve_max) * 100 if cve_max > 0 else 0
        semantic_normalized = (semantic_score / semantic_max) * 100 if semantic_max > 0 else 0
        runtime_normalized = (runtime_score / runtime_max) * 100 if runtime_max > 0 else 0
        
        # Calculate weighted total
        total_score = (
            cve_normalized * self.weights["cve_check"] +
            semantic_normalized * self.weights["semantic_check"] +
            runtime_normalized * self.weights["runtime_check"]
        )
        
        # Determine if safe
        is_safe = total_score >= self.threshold
        
        # Determine risk level
        if total_score >= 85:
            risk_level = "low"
        elif total_score >= 70:
            risk_level = "medium"
        elif total_score >= 50:
            risk_level = "high"
        else:
            risk_level = "critical"
        
        # Collect all issues
        all_issues = []
        all_issues.extend(cve_result.get("issues", []))
        all_issues.extend(semantic_result.get("violations", []))
        all_issues.extend(runtime_result.get("issues", []))
        
        # Count critical issues
        critical_issues = [i for i in all_issues if i.get("severity") == "critical"]
        high_issues = [i for i in all_issues if i.get("severity") == "high"]
        
        result = {
            "total_score": round(total_score, 2),
            "max_score": 100,
            "threshold": self.threshold,
            "is_safe": is_safe,
            "risk_level": risk_level,
            "timestamp": datetime.now().isoformat(),
            "component_scores": {
                "cve_check": {
                    "score": cve_score,
                    "max": cve_max,
                    "normalized": round(cve_normalized, 2),
                    "weight": self.weights["cve_check"]
                },
                "semantic_check": {
                    "score": semantic_score,
                    "max": semantic_max,
                    "normalized": round(semantic_normalized, 2),
                    "weight": self.weights["semantic_check"]
                },
                "runtime_check": {
                    "score": runtime_score,
                    "max": runtime_max,
                    "normalized": round(runtime_normalized, 2),
                    "weight": self.weights["runtime_check"]
                }
            },
            "issues_summary": {
                "total": len(all_issues),
                "critical": len(critical_issues),
                "high": len(high_issues),
                "details": all_issues
            }
        }
        
        logger.info(f"Final Score: {total_score:.2f}/100 - {'SAFE' if is_safe else 'MALICIOUS'} ({risk_level} risk)")
        return result