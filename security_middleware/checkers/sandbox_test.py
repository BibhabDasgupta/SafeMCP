#!/usr/bin/env python3
"""
Sandbox test script - runs inside Docker container
Tests if shortened URL redirects to expected destination
"""
import sys
import json
import requests
from urllib.parse import urlparse

def normalize_domain(domain: str) -> str:
    """
    Normalize domain for comparison
    Removes www. prefix and converts to lowercase
    """
    domain = domain.lower().strip()
    if domain.startswith('www.'):
        domain = domain[4:]
    return domain

def test_redirect(short_url: str, expected_url: str) -> dict:
    """Test if short_url redirects to expected_url"""
    result = {
        "success": False,
        "redirect_url": None,
        "domain_match": False,
        "error": None
    }
    
    try:
        # Follow redirects and get final URL
        response = requests.get(
            short_url,
            allow_redirects=True,
            timeout=10
        )
        
        final_url = response.url
        result["redirect_url"] = final_url
        result["success"] = True
        
        # Check if domains match (with normalization)
        expected_domain = urlparse(expected_url).netloc
        actual_domain = urlparse(final_url).netloc
        
        # Normalize domains for comparison (remove www, lowercase)
        expected_normalized = normalize_domain(expected_domain)
        actual_normalized = normalize_domain(actual_domain)
        
        result["domain_match"] = (expected_normalized == actual_normalized)
        result["expected_domain"] = expected_domain
        result["actual_domain"] = actual_domain
        result["expected_normalized"] = expected_normalized
        result["actual_normalized"] = actual_normalized
        
    except Exception as e:
        result["error"] = str(e)
    
    return result

if __name__ == "__main__":
    try:
        # Read input from stdin
        input_data = json.loads(sys.stdin.read())
        
        short_url = input_data.get("short_url")
        expected_url = input_data.get("expected_url")
        
        # Perform test
        result = test_redirect(short_url, expected_url)
        
        # Output result as JSON
        print(json.dumps(result))
        sys.stdout.flush()
        
    except Exception as e:
        error_result = {
            "success": False,
            "error": f"Script error: {str(e)}"
        }
        print(json.dumps(error_result))
        sys.stdout.flush()
        sys.exit(1)