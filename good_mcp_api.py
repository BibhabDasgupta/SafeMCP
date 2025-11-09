#!/usr/bin/env python3
import logging
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from typing import Dict
from datetime import datetime
import random
import string
from pydantic import BaseModel
import uvicorn
import time
import validators

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("good_service.log"), logging.StreamHandler()],
)
logger = logging.getLogger("good_service")

app = FastAPI(
    title="GoodLink - Legitimate URL Shortening Service",
    description="A trustworthy URL shortening service that works as expected",
    version="1.0.0",
)

# Request tracking
request_counter = 0
SERVER_BASE = "http://localhost:8002"

@app.middleware("http")
async def log_requests(request: Request, call_next):
    global request_counter
    request_counter += 1
    
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    
    logger.info(f"Request: {request.method} {request.url.path} - {response.status_code} ({process_time:.3f}s)")
    return response

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Models
class ShortenRequest(BaseModel):
    url: str

# Storage for legitimate URL mappings
good_links = {}

def generate_short_code():
    """Generate a simple, clean short code"""
    return ''.join(random.choices(string.ascii_letters + string.digits, k=6))

@app.get("/")
async def root():
    return {
        "service": "GoodLink - Legitimate URL Shortening",
        "status": "operational",
        "description": "Trustworthy URL shortening that redirects to original URLs",
        "guarantee": "Every shortened URL redirects to the original URL provided"
    }

@app.post("/shorten")
async def shorten_url(request: ShortenRequest):
    """Create a legitimate shortened URL that redirects to the original"""
    global request_counter
    
    original_url = request.url.strip()
    
    # Validate the URL
    if not validators.url(original_url):
        logger.warning(f"Invalid URL provided: {original_url}")
        raise HTTPException(status_code=400, detail="Invalid URL provided")
    
    # Generate a unique short code
    attempts = 0
    while attempts < 10:
        short_code = generate_short_code()
        if short_code not in good_links:
            break
        attempts += 1
    else:
        raise HTTPException(status_code=500, detail="Unable to generate unique short code")
    
    # Create the shortened URL that we control
    short_url = f"{SERVER_BASE}/go/{short_code}"
    
    # Store the legitimate mapping
    good_links[short_code] = {
        "original_url": original_url,
        "short_url": short_url,
        "created": datetime.now().isoformat(),
        "clicks": 0
    }
    
    logger.info(f"GOOD SHORTENING: {original_url} -> {short_url}")
    logger.info(f"This will redirect to the ORIGINAL URL as expected")
    
    return {
        "success": True,
        "original_url": original_url,
        "short_url": short_url,
        "short_code": short_code,
        "clicks": 0,
        "message": f"URL shortened to: {short_url}",
        "service": "GoodLink"
    }

@app.get("/go/{short_code}")
async def redirect_to_original(short_code: str):
    """Redirect to the original URL - this is how it should work!"""
    
    if short_code not in good_links:
        logger.warning(f"Short code not found: {short_code}")
        raise HTTPException(status_code=404, detail="Shortened URL not found")
    
    link_data = good_links[short_code]
    original_url = link_data["original_url"]
    
    # Update click statistics
    good_links[short_code]["clicks"] += 1
    
    # Log the GOOD redirect
    logger.info(f"GOOD REDIRECT: {short_code} -> {original_url}")
    logger.info(f"User gets EXACTLY what they expect: {original_url}")
    logger.info(f"Click #{good_links[short_code]['clicks']} on good link {short_code}")
    
    # Return proper redirect to the ORIGINAL URL
    return RedirectResponse(url=original_url, status_code=302)

@app.get("/stats")
async def get_statistics():
    """Get service statistics"""
    total_clicks = sum(link["clicks"] for link in good_links.values())
    
    return {
        "service": "GoodLink - Legitimate Service",
        "total_urls_shortened": len(good_links),
        "total_redirects_performed": total_clicks,
        "service_integrity": {
            "redirects_to_original": "100%",
            "malicious_redirects": "0%",
            "user_trust": "maintained"
        },
        "guarantee": "All links redirect to original URLs only"
    }

if __name__ == "__main__":
    logger.info("Starting GoodLink - Legitimate URL Shortening Service")
    logger.info("This service operates EXACTLY as users expect:")
    logger.info("  - Validates URLs before shortening")
    logger.info("  - Redirects to the ORIGINAL URL only")
    logger.info("  - No deception, no surprises")
    logger.info("Running on http://localhost:8002")
    uvicorn.run(app, host="0.0.0.0", port=8002)