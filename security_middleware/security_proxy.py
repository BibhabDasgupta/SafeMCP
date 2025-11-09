# #!/usr/bin/env python3
# import logging
# import sys
# from fastapi import FastAPI, HTTPException, Request
# from fastapi.responses import JSONResponse
# import httpx
# from typing import Dict
# import asyncio

# from security_middleware.checkers.cve_checker import CVEChecker
# from security_middleware.checkers.semantic_engine import SemanticEngine
# from security_middleware.checkers.runtime_sandbox import RuntimeSandbox
# from security_middleware.scoring_engine import ScoringEngine

# # Configure logging
# logging.basicConfig(
#     level=logging.INFO,
#     format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
#     handlers=[
#         logging.FileHandler("logs/security_proxy.log"),
#         logging.StreamHandler(sys.stdout)
#     ]
# )
# logger = logging.getLogger("security_proxy")

# app = FastAPI(title="MCP Security Proxy", version="1.0.0")

# # Initialize security checkers
# cve_checker = CVEChecker()
# semantic_engine = SemanticEngine()
# runtime_sandbox = RuntimeSandbox()
# scoring_engine = ScoringEngine(threshold=70.0)

# # Backend service URLs
# BACKENDS = {
#     "8001": "http://localhost:8001",  # Bad service
#     "8002": "http://localhost:8002"   # Good service
# }

# @app.middleware("http")
# async def log_requests(request: Request, call_next):
#     logger.info(f"Request: {request.method} {request.url.path}")
#     response = await call_next(request)
#     return response

# @app.get("/health")
# async def health_check():
#     return {"status": "healthy", "service": "MCP Security Proxy"}

# @app.post("/{port}/shorten")
# async def proxy_shorten(port: str, request: Request):
#     """
#     Proxy /shorten requests through security checks
#     """
#     if port not in BACKENDS:
#         raise HTTPException(status_code=404, detail="Backend not found")
    
#     backend_url = BACKENDS[port]
#     logger.info(f"🔒 Proxying request to backend: {backend_url}")
    
#     # Get request data
#     request_data = await request.json()
#     original_url = request_data.get("url", "")
    
#     logger.info(f"📝 User requesting to shorten: {original_url}")
    
#     # Forward request to backend
#     try:
#         async with httpx.AsyncClient() as client:
#             response = await client.post(
#                 f"{backend_url}/shorten",
#                 json=request_data,
#                 timeout=30.0
#             )
#             response.raise_for_status()
#             response_data = response.json()
#     except Exception as e:
#         logger.error(f"Backend request failed: {e}")
#         raise HTTPException(status_code=502, detail=f"Backend error: {str(e)}")
    
#     logger.info(f"✅ Received response from backend")
    
#     # SECURITY CHECKS START HERE
#     logger.info("🛡️ Starting security validation...")
    
#     # Run all checks in parallel
#     cve_task = cve_checker.check_service(
#         service_name=response_data.get("service", "unknown"),
#         service_url=backend_url
#     )
    
#     semantic_task = semantic_engine.validate_response(
#         response_data=response_data,
#         request_data=request_data,
#         service_url=backend_url
#     )
    
#     runtime_task = runtime_sandbox.test_redirect(
#         response_data=response_data,
#         request_data=request_data
#     )
    
#     # Wait for all checks to complete
#     cve_result, semantic_result, runtime_result = await asyncio.gather(
#         cve_task,
#         semantic_task,
#         runtime_task
#     )
    
#     logger.info("📊 All security checks completed")
    
#     # Calculate aggregate score
#     security_score = scoring_engine.calculate_score(
#         cve_result=cve_result,
#         semantic_result=semantic_result,
#         runtime_result=runtime_result
#     )
    
#     # Log detailed results
#     logger.info("=" * 70)
#     logger.info("SECURITY VALIDATION REPORT")
#     logger.info("=" * 70)
#     logger.info(f"Service: {response_data.get('service', 'Unknown')}")
#     logger.info(f"Requested URL: {original_url}")
#     logger.info(f"Short URL: {response_data.get('short_url', 'N/A')}")
#     logger.info("")
#     logger.info(f"CVE/Advisory Score: {cve_result['score']}/{cve_result['max_score']} ({cve_result['issues_count']} issues)")
#     logger.info(f"Semantic Score: {semantic_result['score']}/{semantic_result['max_score']} ({semantic_result['violations_count']} violations)")
#     logger.info(f"Runtime Score: {runtime_result['score']}/{runtime_result['max_score']} (Match: {runtime_result.get('domain_match', False)})")
#     logger.info("")
#     logger.info(f"🎯 TOTAL SCORE: {security_score['total_score']:.2f}/100")
#     logger.info(f"🚦 RISK LEVEL: {security_score['risk_level'].upper()}")
#     logger.info(f"✅ VERDICT: {'SAFE ✓' if security_score['is_safe'] else 'MALICIOUS ✗'}")
#     logger.info("=" * 70)
    
#     # If runtime check detected domain mismatch, log details
#     if not runtime_result.get("domain_match", False):
#         logger.warning(f"⚠️  DOMAIN MISMATCH DETECTED!")
#         logger.warning(f"   Expected: {runtime_result.get('expected_domain', 'unknown')}")
#         logger.warning(f"   Actual: {runtime_result.get('actual_domain', 'unknown')}")
    
#     # Make decision
#     if not security_score["is_safe"]:
#         logger.error(f"🚨 BLOCKING MALICIOUS SERVICE!")
#         logger.error(f"   Score: {security_score['total_score']:.2f} (threshold: {security_score['threshold']})")
#         logger.error(f"   Critical Issues: {security_score['issues_summary']['critical']}")
#         logger.error(f"   High Issues: {security_score['issues_summary']['high']}")
        
#         return JSONResponse(
#             status_code=403,
#             content={
#                 "error": "Service blocked by security proxy",
#                 "reason": "Service failed security validation",
#                 "security_score": security_score,
#                 "message": "This service has been identified as potentially malicious and has been blocked."
#             }
#         )
    
#     # Service is safe, return original response with security metadata
#     logger.info("✅ Service passed security validation")
#     response_data["_security_validation"] = {
#         "validated": True,
#         "score": security_score["total_score"],
#         "risk_level": security_score["risk_level"],
#         "timestamp": security_score["timestamp"]
#     }
    
#     return response_data

# @app.get("/{port}/{path:path}")
# async def proxy_get(port: str, path: str):
#     """Proxy GET requests to backend"""
#     if port not in BACKENDS:
#         raise HTTPException(status_code=404, detail="Backend not found")
    
#     backend_url = BACKENDS[port]
    
#     try:
#         async with httpx.AsyncClient() as client:
#             response = await client.get(
#                 f"{backend_url}/{path}",
#                 timeout=30.0
#             )
#             response.raise_for_status()
#             return response.json()
#     except Exception as e:
#         logger.error(f"Backend request failed: {e}")
#         raise HTTPException(status_code=502, detail=f"Backend error: {str(e)}")

# if __name__ == "__main__":
#     import uvicorn
#     logger.info("Starting MCP Security Proxy...")
#     logger.info("Proxy will intercept and validate all requests to backends")
#     uvicorn.run(app, host="0.0.0.0", port=9000)









#!/usr/bin/env python3
import logging
import sys
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
import httpx
from typing import Dict
import asyncio
import os

from security_middleware.checkers.cve_checker import CVEChecker
from security_middleware.checkers.semantic_engine import SemanticEngine
from security_middleware.checkers.runtime_sandbox import RuntimeSandbox
from security_middleware.scoring_engine import ScoringEngine

# Create logs directory
os.makedirs("logs", exist_ok=True)

# Configure logging (Windows-compatible)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("logs/security_proxy.log", encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)

# Fix Windows console encoding
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except:
        pass

logger = logging.getLogger("security_proxy")

app = FastAPI(title="MCP Security Proxy", version="1.0.0")

# Initialize security checkers
cve_checker = CVEChecker()
semantic_engine = SemanticEngine()
runtime_sandbox = RuntimeSandbox()
scoring_engine = ScoringEngine(threshold=70.0)

# Backend service URLs
BACKENDS = {
    "8001": "http://localhost:8001",  # Bad service
    "8002": "http://localhost:8002"   # Good service
}

@app.middleware("http")
async def log_requests(request: Request, call_next):
    logger.info(f"Request: {request.method} {request.url.path}")
    response = await call_next(request)
    return response

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "MCP Security Proxy"}

@app.post("/{port}/shorten")
async def proxy_shorten(port: str, request: Request):
    """
    Proxy /shorten requests through security checks
    """
    if port not in BACKENDS:
        raise HTTPException(status_code=404, detail="Backend not found")
    
    backend_url = BACKENDS[port]
    logger.info(f"[PROXY] Proxying request to backend: {backend_url}")
    
    # Get request data
    request_data = await request.json()
    original_url = request_data.get("url", "")
    
    logger.info(f"[REQUEST] User requesting to shorten: {original_url}")
    
    # Forward request to backend
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{backend_url}/shorten",
                json=request_data,
                timeout=30.0
            )
            response.raise_for_status()
            response_data = response.json()
    except Exception as e:
        logger.error(f"Backend request failed: {e}")
        raise HTTPException(status_code=502, detail=f"Backend error: {str(e)}")
    
    logger.info(f"[SUCCESS] Received response from backend")
    
    # SECURITY CHECKS START HERE
    logger.info("[SECURITY] Starting security validation...")
    
    # Run all checks in parallel
    cve_task = cve_checker.check_service(
        service_name=response_data.get("service", "unknown"),
        service_url=backend_url
    )
    
    semantic_task = semantic_engine.validate_response(
        response_data=response_data,
        request_data=request_data,
        service_url=backend_url
    )
    
    runtime_task = runtime_sandbox.test_redirect(
        response_data=response_data,
        request_data=request_data
    )
    
    # Wait for all checks to complete
    cve_result, semantic_result, runtime_result = await asyncio.gather(
        cve_task,
        semantic_task,
        runtime_task
    )
    
    logger.info("[COMPLETE] All security checks completed")
    
    # Calculate aggregate score
    security_score = scoring_engine.calculate_score(
        cve_result=cve_result,
        semantic_result=semantic_result,
        runtime_result=runtime_result
    )
    
    # Log detailed results
    logger.info("=" * 70)
    logger.info("SECURITY VALIDATION REPORT")
    logger.info("=" * 70)
    logger.info(f"Service: {response_data.get('service', 'Unknown')}")
    logger.info(f"Requested URL: {original_url}")
    logger.info(f"Short URL: {response_data.get('short_url', 'N/A')}")
    logger.info("")
    logger.info(f"CVE/Advisory Score: {cve_result['score']}/{cve_result['max_score']} ({cve_result['issues_count']} issues)")
    logger.info(f"Semantic Score: {semantic_result['score']}/{semantic_result['max_score']} ({semantic_result['violations_count']} violations)")
    logger.info(f"Runtime Score: {runtime_result['score']}/{runtime_result['max_score']} (Match: {runtime_result.get('domain_match', 'N/A')})")
    logger.info("")
    logger.info(f"[SCORE] TOTAL SCORE: {security_score['total_score']:.2f}/100")
    logger.info(f"[RISK] RISK LEVEL: {security_score['risk_level'].upper()}")
    logger.info(f"[VERDICT] VERDICT: {'SAFE' if security_score['is_safe'] else 'MALICIOUS'}")
    logger.info("=" * 70)
    
    # If runtime check detected domain mismatch, log details
    if runtime_result.get("domain_match") == False:
        logger.warning(f"[ALERT] DOMAIN MISMATCH DETECTED!")
        logger.warning(f"   Expected: {runtime_result.get('expected_domain', 'unknown')}")
        logger.warning(f"   Actual: {runtime_result.get('actual_domain', 'unknown')}")
    
    # Make decision
    if not security_score["is_safe"]:
        logger.error(f"[BLOCKED] BLOCKING MALICIOUS SERVICE!")
        logger.error(f"   Score: {security_score['total_score']:.2f} (threshold: {security_score['threshold']})")
        logger.error(f"   Critical Issues: {security_score['issues_summary']['critical']}")
        logger.error(f"   High Issues: {security_score['issues_summary']['high']}")
        
        return JSONResponse(
            status_code=403,
            content={
                "error": "Service blocked by security proxy",
                "reason": "Service failed security validation",
                "security_score": security_score,
                "message": "This service has been identified as potentially malicious and has been blocked."
            }
        )
    
    # Service is safe, return original response with security metadata
    logger.info("[ALLOWED] Service passed security validation")
    response_data["_security_validation"] = {
        "validated": True,
        "score": security_score["total_score"],
        "risk_level": security_score["risk_level"],
        "timestamp": security_score["timestamp"]
    }
    
    return response_data

@app.get("/{port}/{path:path}")
async def proxy_get(port: str, path: str):
    """Proxy GET requests to backend"""
    if port not in BACKENDS:
        raise HTTPException(status_code=404, detail="Backend not found")
    
    backend_url = BACKENDS[port]
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{backend_url}/{path}",
                timeout=30.0
            )
            response.raise_for_status()
            return response.json()
    except Exception as e:
        logger.error(f"Backend request failed: {e}")
        raise HTTPException(status_code=502, detail=f"Backend error: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    logger.info("Starting MCP Security Proxy...")
    logger.info("Proxy will intercept and validate all requests to backends")
    uvicorn.run(app, host="0.0.0.0", port=9000)