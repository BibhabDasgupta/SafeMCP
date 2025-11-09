#!/usr/bin/env python3
import logging
import httpx
import asyncio
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import json
import os

logger = logging.getLogger("cve_checker")

class CVEChecker:
    """Check for known vulnerabilities and security advisories"""
    
    def __init__(self):
        self.github_api = "https://api.github.com/advisories"
        self.nvd_api = "https://services.nvd.nist.gov/rest/json/cves/2.0"
        self.cache_file = "data/cve_cache.json"
        self.cache_duration = timedelta(hours=24)
        self.cache = self._load_cache()
        
    def _load_cache(self) -> Dict:
        """Load CVE cache from file"""
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load cache: {e}")
        return {}
    
    def _save_cache(self):
        """Save CVE cache to file"""
        try:
            os.makedirs(os.path.dirname(self.cache_file), exist_ok=True)
            with open(self.cache_file, 'w') as f:
                json.dump(self.cache, f)
        except Exception as e:
            logger.warning(f"Failed to save cache: {e}")
    
    async def check_service(self, service_name: str, service_url: str) -> Dict:
        """
        Check if service has known vulnerabilities
        Returns: {
            "score": 0-30,
            "issues": [],
            "severity": "low|medium|high|critical"
        }
        """
        logger.info(f"Checking CVE/Advisory for: {service_name}")
        
        # Check cache
        cache_key = f"{service_name}_{service_url}"
        if cache_key in self.cache:
            cached_data = self.cache[cache_key]
            cache_time = datetime.fromisoformat(cached_data["timestamp"])
            if datetime.now() - cache_time < self.cache_duration:
                logger.info("Using cached CVE data")
                return cached_data["result"]
        
        # Perform checks
        issues = []
        score = 30  # Start with perfect score
        
        # Check GitHub Security Advisories
        github_issues = await self._check_github_advisories(service_name)
        issues.extend(github_issues)
        
        # Check NVD database
        nvd_issues = await self._check_nvd_database(service_name)
        issues.extend(nvd_issues)
        
        # Check against known malicious patterns
        pattern_issues = self._check_malicious_patterns(service_url, service_name)
        issues.extend(pattern_issues)
        
        # Calculate score deductions
        for issue in issues:
            if issue["severity"] == "critical":
                score -= 15
            elif issue["severity"] == "high":
                score -= 10
            elif issue["severity"] == "medium":
                score -= 5
            elif issue["severity"] == "low":
                score -= 2
        
        score = max(0, score)  # Ensure non-negative
        
        # Determine overall severity
        severities = [issue["severity"] for issue in issues]
        if "critical" in severities:
            overall_severity = "critical"
        elif "high" in severities:
            overall_severity = "high"
        elif "medium" in severities:
            overall_severity = "medium"
        elif "low" in severities:
            overall_severity = "low"
        else:
            overall_severity = "none"
        
        result = {
            "score": score,
            "max_score": 30,
            "issues": issues,
            "severity": overall_severity,
            "issues_count": len(issues)
        }
        
        # Cache result
        self.cache[cache_key] = {
            "timestamp": datetime.now().isoformat(),
            "result": result
        }
        self._save_cache()
        
        logger.info(f"CVE Check complete: Score={score}/30, Issues={len(issues)}")
        return result
    
    async def _check_github_advisories(self, service_name: str) -> List[Dict]:
        """Check GitHub Security Advisories"""
        issues = []
        
        try:
            async with httpx.AsyncClient() as client:
                # Search for advisories related to service
                response = await client.get(
                    self.github_api,
                    params={"affects": service_name},
                    headers={"Accept": "application/vnd.github+json"},
                    timeout=10.0
                )
                
                if response.status_code == 200:
                    advisories = response.json()
                    for advisory in advisories[:5]:  # Limit to 5 most relevant
                        issues.append({
                            "source": "GitHub Advisory",
                            "severity": advisory.get("severity", "medium").lower(),
                            "description": advisory.get("summary", "Security advisory found"),
                            "id": advisory.get("ghsa_id", "N/A"),
                            "published": advisory.get("published_at", "")
                        })
        except Exception as e:
            logger.warning(f"GitHub Advisory check failed: {e}")
        
        return issues
    
    async def _check_nvd_database(self, service_name: str) -> List[Dict]:
        """Check National Vulnerability Database"""
        issues = []
        
        try:
            async with httpx.AsyncClient() as client:
                # Search NVD for CVEs
                response = await client.get(
                    self.nvd_api,
                    params={"keywordSearch": service_name},
                    timeout=10.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    vulnerabilities = data.get("vulnerabilities", [])
                    
                    for vuln in vulnerabilities[:5]:  # Limit to 5
                        cve = vuln.get("cve", {})
                        metrics = cve.get("metrics", {})
                        
                        # Extract severity
                        severity = "medium"
                        if "cvssMetricV31" in metrics:
                            cvss = metrics["cvssMetricV31"][0]["cvssData"]
                            base_score = cvss.get("baseScore", 5.0)
                            if base_score >= 9.0:
                                severity = "critical"
                            elif base_score >= 7.0:
                                severity = "high"
                            elif base_score >= 4.0:
                                severity = "medium"
                            else:
                                severity = "low"
                        
                        issues.append({
                            "source": "NVD",
                            "severity": severity,
                            "description": cve.get("descriptions", [{}])[0].get("value", "CVE found"),
                            "id": cve.get("id", "N/A"),
                            "published": cve.get("published", "")
                        })
        except Exception as e:
            logger.warning(f"NVD check failed: {e}")
        
        return issues
    
    def _check_malicious_patterns(self, service_url: str, service_name: str) -> List[Dict]:
        """Check for known malicious patterns"""
        issues = []
        
        # Known malicious indicators
        malicious_keywords = [
            "fastlink pro", "enterprise-grade", "professional analytics",
            "advanced analytics", "rugpull", "scam"
        ]
        
        suspicious_ports = [8001]  # Known bad port from our demo
        
        service_lower = service_name.lower()
        
        # Check for suspicious keywords
        for keyword in malicious_keywords:
            if keyword in service_lower:
                issues.append({
                    "source": "Pattern Detection",
                    "severity": "high",
                    "description": f"Service name contains suspicious keyword: '{keyword}'",
                    "id": "PATTERN-001",
                    "published": datetime.now().isoformat()
                })
        
        # Check for suspicious ports
        for port in suspicious_ports:
            if f":{port}" in service_url or f"port {port}" in service_lower:
                issues.append({
                    "source": "Pattern Detection",
                    "severity": "medium",
                    "description": f"Service uses suspicious port: {port}",
                    "id": "PATTERN-002",
                    "published": datetime.now().isoformat()
                })
        
        return issues