#!/usr/bin/env python3
import logging
import yaml
import validators
from typing import Dict, List, Any
from urllib.parse import urlparse

logger = logging.getLogger("semantic_engine")

class SemanticEngine:
    """Validate responses against semantic rules"""
    
    def __init__(self, rules_file: str = "security_middleware/rules/semantic_rules.yaml"):
        self.rules_file = rules_file
        self.rules = self._load_rules()
        self.max_score = 30
        
    def _load_rules(self) -> Dict:
        """Load semantic rules from YAML file"""
        try:
            with open(self.rules_file, 'r') as f:
                return yaml.safe_load(f)
        except Exception as e:
            logger.error(f"Failed to load rules: {e}")
            return {"rules": {}, "thresholds": {}}
    
    async def validate_response(
        self,
        response_data: Dict,
        request_data: Dict,
        service_url: str
    ) -> Dict:
        """
        Validate response against semantic rules
        Returns: {
            "score": 0-30,
            "violations": [],
            "severity": "low|medium|high"
        }
        """
        logger.info("Starting semantic validation...")
        
        score = self.max_score
        violations = []
        
        # 1. Response validation
        response_violations = self._check_response_validation(response_data)
        violations.extend(response_violations)
        
        # 2. URL format validation
        url_violations = self._check_url_format(response_data, request_data, service_url)
        violations.extend(url_violations)
        
        # 3. Service validation
        service_violations = self._check_service_validation(response_data)
        violations.extend(service_violations)
        
        # 4. Data integrity
        integrity_violations = self._check_data_integrity(response_data)
        violations.extend(integrity_violations)
        
        # Calculate score
        for violation in violations:
            score -= violation["score_penalty"]
        
        score = max(0, score)
        
        # Determine severity
        thresholds = self.rules.get("thresholds", {})
        if score >= thresholds.get("safe", 25):
            severity = "low"
        elif score >= thresholds.get("suspicious", 15):
            severity = "medium"
        else:
            severity = "high"
        
        result = {
            "score": score,
            "max_score": self.max_score,
            "violations": violations,
            "severity": severity,
            "violations_count": len(violations)
        }
        
        logger.info(f"Semantic validation complete: Score={score}/30, Violations={len(violations)}")
        return result
    
    def _check_response_validation(self, response_data: Dict) -> List[Dict]:
        """Check required fields in response"""
        violations = []
        rules = self.rules.get("rules", {}).get("response_validation", [])
        
        for rule in rules:
            field = rule.get("field")
            required = rule.get("required", False)
            
            if required and field not in response_data:
                violations.append({
                    "rule": rule["name"],
                    "description": rule["description"],
                    "severity": "high" if rule["score_penalty"] >= 10 else "medium",
                    "score_penalty": rule["score_penalty"],
                    "details": f"Missing required field: {field}"
                })
        
        return violations
    
    def _check_url_format(
        self,
        response_data: Dict,
        request_data: Dict,
        service_url: str
    ) -> List[Dict]:
        """Validate URL formats and matching"""
        violations = []
        rules = self.rules.get("rules", {}).get("url_format_validation", [])
        
        original_url = response_data.get("original_url", "")
        short_url = response_data.get("short_url", "")
        requested_url = request_data.get("url", "")
        
        for rule in rules:
            rule_type = rule.get("type")
            
            if rule_type == "url_match":
                # Check if original_url matches what was requested
                if original_url != requested_url:
                    violations.append({
                        "rule": rule["name"],
                        "description": rule["description"],
                        "severity": "high",
                        "score_penalty": rule["score_penalty"],
                        "details": f"URL mismatch: requested='{requested_url}', got='{original_url}'"
                    })
            
            elif rule_type == "url_format":
                # Check if short_url is valid format
                if short_url and not validators.url(short_url):
                    violations.append({
                        "rule": rule["name"],
                        "description": rule["description"],
                        "severity": "medium",
                        "score_penalty": rule["score_penalty"],
                        "details": f"Invalid URL format: {short_url}"
                    })
            
            elif rule_type == "domain_match":
                # Check if short_url domain matches service domain
                if short_url and service_url:
                    short_domain = urlparse(short_url).netloc
                    service_domain = urlparse(service_url).netloc
                    
                    if short_domain and service_domain and short_domain != service_domain:
                        violations.append({
                            "rule": rule["name"],
                            "description": rule["description"],
                            "severity": "medium",
                            "score_penalty": rule["score_penalty"],
                            "details": f"Domain mismatch: short_url domain='{short_domain}', service='{service_domain}'"
                        })
        
        return violations
    
    def _check_service_validation(self, response_data: Dict) -> List[Dict]:
        """Validate service-specific fields"""
        violations = []
        rules = self.rules.get("rules", {}).get("service_validation", [])
        
        for rule in rules:
            rule_type = rule.get("type")
            
            if rule_type == "message_check":
                # Check for suspicious keywords in message
                message = response_data.get("message", "").lower()
                service = response_data.get("service", "").lower()
                
                keywords = rule.get("keywords", [])
                found_keywords = [kw for kw in keywords if kw in message or kw in service]
                
                if found_keywords:
                    violations.append({
                        "rule": rule["name"],
                        "description": rule["description"],
                        "severity": "medium",
                        "score_penalty": rule["score_penalty"],
                        "details": f"Suspicious keywords found: {', '.join(found_keywords)}"
                    })
        
        return violations
    
    def _check_data_integrity(self, response_data: Dict) -> List[Dict]:
        """Check data integrity"""
        violations = []
        rules = self.rules.get("rules", {}).get("data_integrity", [])
        
        for rule in rules:
            field = rule.get("field")
            required = rule.get("required", True)
            expected_value = rule.get("expected_value")
            
            if field in response_data:
                actual_value = response_data[field]
                
                if expected_value is not None and actual_value != expected_value:
                    violations.append({
                        "rule": rule["name"],
                        "description": rule["description"],
                        "severity": "low",
                        "score_penalty": rule["score_penalty"],
                        "details": f"Expected {field}={expected_value}, got {actual_value}"
                    })
            elif required:
                violations.append({
                    "rule": rule["name"],
                    "description": rule["description"],
                    "severity": "low",
                    "score_penalty": rule["score_penalty"],
                    "details": f"Missing field: {field}"
                })
        
        return violations