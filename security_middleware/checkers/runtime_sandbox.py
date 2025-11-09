#!/usr/bin/env python3
import logging
import json
import asyncio
from typing import Dict
from urllib.parse import urlparse

# Try to import docker
try:
    import docker
    DOCKER_AVAILABLE = True
except ImportError:
    DOCKER_AVAILABLE = False

logger = logging.getLogger("runtime_sandbox")

class RuntimeSandbox:
    """Test URL redirects in isolated Docker container"""
    
    def __init__(self):
        # CRITICAL: Set max_score FIRST before any early returns!
        self.max_score = 40
        self.docker_client = None
        self.image_name = "mcp-sandbox-test"
        
        if not DOCKER_AVAILABLE:
            logger.warning("Docker package not installed - runtime sandbox testing will be skipped")
            logger.warning("Install docker package with: pip install docker")
            return
        
        try:
            self.docker_client = docker.from_env()
            logger.info("Docker client initialized successfully")
            
            # Check if image exists
            try:
                self.docker_client.images.get(self.image_name)
                logger.info(f"Docker image '{self.image_name}' found and ready")
            except docker.errors.ImageNotFound:
                logger.warning(f"Docker image '{self.image_name}' not found")
                logger.warning("Build it with: docker build -f Dockerfile.sandbox -t mcp-sandbox-test .")
                self.docker_client = None
            except Exception as e:
                logger.warning(f"Cannot access Docker images: {e}")
                self.docker_client = None
                
        except docker.errors.DockerException as e:
            logger.error(f"Docker initialization failed: {e}")
            logger.error("Make sure Docker Desktop is running")
            self.docker_client = None
        except Exception as e:
            logger.error(f"Unexpected error initializing Docker: {e}")
            self.docker_client = None
    
    async def test_redirect(
        self,
        response_data: Dict,
        request_data: Dict
    ) -> Dict:
        """
        Test URL redirect in sandbox
        """
        logger.info("Starting runtime sandbox test...")
        
        # If Docker is not available, use fallback heuristic check
        if not self.docker_client:
            logger.warning("Docker not available, using fallback heuristic check")
            return await self._fallback_heuristic_check(response_data, request_data)
        
        short_url = response_data.get("short_url")
        expected_url = request_data.get("url")
        
        if not short_url or not expected_url:
            logger.error("Missing URLs for sandbox testing")
            return {
                "score": 0,
                "max_score": self.max_score,
                "redirect_tested": False,
                "domain_match": False,
                "issues": [{"description": "Missing URLs for testing", "severity": "high"}]
            }
        
        # Run test in Docker container
        try:
            test_result = await self._run_docker_test(short_url, expected_url)
            
            score = self.max_score
            issues = []
            
            # Check if test succeeded
            if not test_result.get("success"):
                error_msg = test_result.get('error', 'Unknown error')
                issues.append({
                    "description": f"Redirect test failed: {error_msg}",
                    "severity": "high"
                })
                score -= 20
                
                # If test failed, return early
                result = {
                    "score": score,
                    "max_score": self.max_score,
                    "redirect_tested": False,
                    "domain_match": False,
                    "issues": issues,
                    "issues_count": len(issues),
                    "error": error_msg
                }
                logger.warning(f"Sandbox test failed: {error_msg}")
                return result
            
            # Test succeeded, check domain match
            domain_match = test_result.get("domain_match", False)
            
            if not domain_match:
                actual_domain = test_result.get("actual_domain", "unknown")
                expected_domain = test_result.get("expected_domain", "unknown")
                
                issues.append({
                    "description": f"Domain mismatch: expected '{expected_domain}', got '{actual_domain}'",
                    "severity": "critical"
                })
                score -= 20
            
            score = max(0, score)
            
            result = {
                "score": score,
                "max_score": self.max_score,
                "redirect_tested": True,
                "domain_match": domain_match,
                "redirect_url": test_result.get("redirect_url"),
                "expected_domain": test_result.get("expected_domain"),
                "actual_domain": test_result.get("actual_domain"),
                "issues": issues,
                "issues_count": len(issues)
            }
            
            logger.info(f"Sandbox test complete: Score={score}/40, Match={domain_match}")
            return result
            
        except Exception as e:
            logger.error(f"Sandbox test error: {e}")
            return {
                "score": 0,
                "max_score": self.max_score,
                "redirect_tested": False,
                "domain_match": False,
                "issues": [{"description": f"Test error: {str(e)}", "severity": "critical"}],
                "error": str(e)
            }
    
    async def _fallback_heuristic_check(
        self,
        response_data: Dict,
        request_data: Dict
    ) -> Dict:
        """Fallback heuristic check when Docker is unavailable"""
        logger.info("Running fallback heuristic check (no Docker)")
        
        short_url = response_data.get("short_url", "")
        expected_url = request_data.get("url", "")
        service_name = response_data.get("service", "").lower()
        
        score = self.max_score // 2
        issues = []
        
        issues.append({
            "description": "Docker unavailable - using simplified check",
            "severity": "warning"
        })
        
        try:
            if "8001" in short_url:
                issues.append({
                    "description": "Service uses suspicious port 8001",
                    "severity": "high"
                })
                score -= 10
            
            suspicious_names = ["fastlink pro", "professional", "enterprise"]
            for suspicious in suspicious_names:
                if suspicious in service_name:
                    issues.append({
                        "description": f"Service name contains suspicious keyword: '{suspicious}'",
                        "severity": "medium"
                    })
                    score -= 5
                    break
            
            score = max(0, score)
            
            result = {
                "score": score,
                "max_score": self.max_score,
                "redirect_tested": False,
                "domain_match": None,
                "expected_domain": urlparse(expected_url).netloc if expected_url else "unknown",
                "actual_domain": "unknown (Docker unavailable)",
                "issues": issues,
                "issues_count": len(issues)
            }
            
            logger.info(f"Fallback check complete: Score={score}/40")
            return result
            
        except Exception as e:
            logger.error(f"Fallback check error: {e}")
            return {
                "score": 0,
                "max_score": self.max_score,
                "redirect_tested": False,
                "domain_match": None,
                "issues": [{"description": f"Fallback check error: {str(e)}", "severity": "high"}],
                "error": str(e)
            }
    
    async def _run_docker_test(self, short_url: str, expected_url: str) -> Dict:
        """Run redirect test inside Docker container"""
        test_input = json.dumps({
            "short_url": short_url,
            "expected_url": expected_url
        })
        
        try:
            logger.info(f"Testing redirect: {short_url} -> {expected_url}")
            
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                self._run_docker_container_sync,
                test_input
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Docker test execution failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def _run_docker_container_sync(self, test_input: str) -> Dict:
        """Synchronous Docker container execution - Windows compatible"""
        container = None
        try:
            input_data = json.loads(test_input)
            short_url = input_data.get("short_url", "")
            expected_url = input_data.get("expected_url", "")
            
            short_url_escaped = short_url.replace('"', '\\"').replace("'", "\\'")
            expected_url_escaped = expected_url.replace('"', '\\"').replace("'", "\\'")
            
            # Create container (NO remove parameter!)
            container = self.docker_client.containers.create(
                self.image_name,
                stdin_open=True,
                tty=False,
                detach=True,
                mem_limit="128m",
                cpu_quota=50000
            )
            
            logger.info(f"Container created: {container.id[:12]}")
            
            container.start()
            
            python_code = f"""
import sys
import json
sys.path.insert(0, '/sandbox')
from test import test_redirect

result = test_redirect("{short_url_escaped}", "{expected_url_escaped}")
print(json.dumps(result))
sys.stdout.flush()
"""
            
            exec_result = container.exec_run(
                cmd=["python", "-c", python_code],
                stdout=True,
                stderr=True,
                demux=False
            )
            
            output = exec_result.output.decode('utf-8').strip()
            
            try:
                result_data = json.loads(output)
                logger.info(f"Container test completed successfully")
                return result_data
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse container output: {output}")
                return {
                    "success": False,
                    "error": f"Invalid JSON output: {str(e)}"
                }
            
        except docker.errors.ContainerError as e:
            logger.error(f"Container execution error: {e}")
            return {
                "success": False,
                "error": f"Container error: {str(e)}"
            }
        except docker.errors.ImageNotFound:
            logger.error(f"Docker image '{self.image_name}' not found")
            return {
                "success": False,
                "error": "Docker image not found"
            }
        except Exception as e:
            logger.error(f"Docker container execution failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }
        finally:
            # Always clean up container
            if container:
                try:
                    container.stop(timeout=2)
                    container.remove()
                    logger.debug(f"Container {container.id[:12]} cleaned up")
                except Exception as e:
                    logger.warning(f"Failed to clean up container: {e}")