#!/usr/bin/env python3
"""Manual test of Docker sandbox - Windows compatible"""
import docker
import json
import time

def test_docker_sandbox():
    print("Testing Docker sandbox manually (Windows)...")
    
    try:
        # Initialize Docker client
        client = docker.from_env()
        print("✓ Docker client initialized")
        
        # Check if image exists
        try:
            image = client.images.get("mcp-sandbox-test")
            print(f"✓ Docker image found: {image.tags}")
        except docker.errors.ImageNotFound:
            print("✗ Docker image 'mcp-sandbox-test' not found!")
            print("  Build it with: docker build -f Dockerfile.sandbox -t mcp-sandbox-test .")
            return
        
        # Prepare test input
        test_data = {
            "short_url": "https://httpbin.org/redirect-to?url=https://google.com",
            "expected_url": "https://google.com"
        }
        test_input = json.dumps(test_data)
        
        print(f"\nTest input: {test_input}")
        print("\nRunning container with exec approach...")
        
        # Create container (don't start yet)
        container = client.containers.create(
            "mcp-sandbox-test",
            stdin_open=True,
            tty=False,
            detach=True
        )
        
        print(f"✓ Container created: {container.id[:12]}")
        
        # Start container
        container.start()
        print("✓ Container started")
        
        # Give container a moment to be ready
        time.sleep(0.5)
        
        # Execute command with input via exec
        exec_result = container.exec_run(
            cmd=["python", "-c", f"""
import sys
import json
input_data = {test_input}
sys.path.insert(0, '/sandbox')
from test import test_redirect
result = test_redirect(input_data['short_url'], input_data['expected_url'])
print(json.dumps(result))
"""],
            stdout=True,
            stderr=True
        )
        
        print("✓ Command executed in container")
        
        # Get output
        output = exec_result.output.decode('utf-8')
        exit_code = exec_result.exit_code
        
        print(f"✓ Exit code: {exit_code}")
        print(f"\nContainer output:\n{output}")
        
        # Clean up
        container.stop(timeout=1)
        container.remove()
        print("✓ Container cleaned up")
        
        # Parse result
        try:
            result_data = json.loads(output.strip())
            print("\n=== PARSED RESULT ===")
            print(f"Success: {result_data.get('success')}")
            print(f"Redirect URL: {result_data.get('redirect_url')}")
            print(f"Expected Domain: {result_data.get('expected_domain')}")
            print(f"Actual Domain: {result_data.get('actual_domain')}")
            print(f"Domain Match: {result_data.get('domain_match')}")
            
            if result_data.get('error'):
                print(f"Error: {result_data.get('error')}")
            
            print("\n✓✓✓ Docker sandbox is working correctly! ✓✓✓")
            
        except json.JSONDecodeError as e:
            print(f"\n✗ Failed to parse output as JSON: {e}")
            print(f"Raw output: {output}")
            
    except docker.errors.DockerException as e:
        print(f"\n✗ Docker error: {e}")
        print("\nMake sure Docker Desktop is running!")
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_docker_sandbox()