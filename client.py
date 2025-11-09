#!/usr/bin/env python3
import sys
import logging
import os
from fastmcp import FastMCP
import httpx

logging.basicConfig(
    stream=sys.stderr,
    level=logging.INFO,
    format="[URL Shortener] %(levelname)s: %(message)s"
)
log = logging.getLogger(__name__)

# Initialize MCP server
mcp = FastMCP("url_shortening_service")

DEFAULT_PORT = "8001"  # Good server
SERVICE_PORT = os.getenv("URL_SERVICE_PORT", DEFAULT_PORT)

# USE SECURITY PROXY INSTEAD OF DIRECT CONNECTION
PROXY_BASE = "http://localhost:9000"
SERVICE_API_BASE = f"{PROXY_BASE}/{SERVICE_PORT}"

USER_AGENT = "universal-url-client/1.0"

async def _get_json(url: str):
    """Fetch JSON data via security proxy"""
    headers = {"User-Agent": USER_AGENT, "Accept": "application/json"}
    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=headers, timeout=30.0)
        response.raise_for_status()
        return response.json()

@mcp.tool()
async def create_short_url(url: str) -> str:
    """Create a shortened URL for easy sharing"""
    log.info(f"Creating short URL for: {url}")
    
    try:
        # Call through security proxy
        shorten_url = f"{SERVICE_API_BASE}/shorten"
        async with httpx.AsyncClient() as client:
            response = await client.post(
                shorten_url, 
                json={"url": url},
                headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
                timeout=60.0  # Increased timeout for security checks
            )
            
            if response.status_code == 403:
                # Service was blocked by security proxy
                error_data = response.json()
                log.error(f"Service blocked by security proxy!")
                
                result = "🚨 **SECURITY ALERT** 🚨\n\n"
                result += f"The URL shortening service has been blocked due to security concerns.\n\n"
                result += f"**Reason:** {error_data.get('reason', 'Security validation failed')}\n\n"
                
                if "security_score" in error_data:
                    score_data = error_data["security_score"]
                    result += f"**Security Score:** {score_data.get('total_score', 0):.2f}/100\n"
                    result += f"**Risk Level:** {score_data.get('risk_level', 'unknown').upper()}\n"
                    result += f"**Threshold:** {score_data.get('threshold', 70)} (minimum required)\n\n"
                    
                    issues = score_data.get("issues_summary", {})
                    if issues.get("total", 0) > 0:
                        result += f"**Issues Found:**\n"
                        result += f"- Critical: {issues.get('critical', 0)}\n"
                        result += f"- High: {issues.get('high', 0)}\n"
                        result += f"- Total: {issues.get('total', 0)}\n\n"
                
                result += "❌ This service cannot be used. Please choose a different URL shortening service."
                return result
            
            response.raise_for_status()
            data = response.json()
        
        # Extract response data
        original_url = data.get("original_url", url)
        short_url = data.get("short_url", "")
        short_code = data.get("short_code", "")
        clicks = data.get("clicks", 0)
        service = data.get("service", "URL Shortener")
        message = data.get("message", "")
        
        log.info(f"URL shortening successful: {short_code}")
        
        result = f"✅ URL shortened successfully!\n\n"
        result += f"Original URL: {original_url}\n"
        result += f"Shortened URL: {short_url}\n"
        result += f"Short Code: {short_code}\n" 
        result += f"Current clicks: {clicks}\n"
        result += f"Service: {service}\n\n"
        result += f"🔗 Your shortened URL: {short_url}\n\n"
        
        # Show security validation status
        if "_security_validation" in data:
            security = data["_security_validation"]
            result += f"🛡️ Security validated: Score {security['score']:.2f}/100 ({security['risk_level']} risk)\n"
        
        return result
        
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 400:
            log.error(f"Invalid URL provided: {url}")
            return f"❌ Invalid URL provided. Please ensure the URL is properly formatted (e.g., https://example.com)"
        elif e.response.status_code == 403:
            return "🚨 Service blocked by security validation"
        else:
            log.error(f"HTTP error shortening URL: {e}")
            return f"❌ Service error: {str(e)}"
    except Exception as e:
        log.error(f"Error shortening URL: {e}")
        return f"❌ Unable to shorten URL: {str(e)}"

@mcp.tool()
async def get_service_info() -> str:
    """Get information about the URL shortening service"""
    log.info("Getting service information...")
    
    try:
        info_url = f"{SERVICE_API_BASE}/"
        info_data = await _get_json(info_url)
        
        service_name = info_data.get("service", "URL Shortening Service")
        description = info_data.get("description", "")
        status = info_data.get("status", "unknown")
        
        result = f"ℹ️ **{service_name}**\n\n"
        result += f"Status: {status}\n"
        if description:
            result += f"Description: {description}\n"
        
        result += f"\nProtected by: MCP Security Proxy\n"
        result += f"Connected via: {SERVICE_API_BASE}"
        
        return result
        
    except Exception as e:
        log.error(f"Error getting service info: {e}")
        return f"❌ Service information unavailable: {str(e)}"

@mcp.tool()
async def get_service_statistics() -> str:
    """Get statistics about the URL shortening service"""
    log.info("Getting service statistics...")
    
    try:
        stats_url = f"{SERVICE_API_BASE}/stats"
        stats_data = await _get_json(stats_url)
        
        service_name = stats_data.get("service", "URL Shortening Service")
        total_urls = stats_data.get("total_urls_shortened", 0)
        total_redirects = stats_data.get("total_redirects_performed", 0)
        
        result = f"📊 **{service_name} Statistics**\n\n"
        result += f"Total URLs shortened: {total_urls}\n"
        result += f"Total redirects performed: {total_redirects}\n"
        
        return result
        
    except Exception as e:
        log.error(f"Error getting statistics: {e}")
        return f"❌ Statistics unavailable: {str(e)}"

if __name__ == "__main__":
    log.info("Starting URL Shortening Service Client...")
    log.info(f"🛡️ Protected by Security Proxy on port 9000")
    log.info(f"Connecting to service on port {SERVICE_PORT}")
    
    log.info("Available tools:")
    log.info("  - create_short_url(url) - Create shortened URLs")
    log.info("  - get_service_info() - Service information")
    log.info("  - get_service_statistics() - Service usage statistics")
    
    try:
        mcp.run()
    except KeyboardInterrupt:
        log.info("URL shortening service client stopped")
    except Exception as e:
        log.error(f"Client error: {e}")
        sys.exit(1)