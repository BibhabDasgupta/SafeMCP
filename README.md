# MCP Security Middleware

A comprehensive security validation system for Model Context Protocol (MCP) servers that detects and blocks malicious URL shortening services through three-layer security checks.

## 🎯 Project Overview

This project demonstrates a critical vulnerability in MCP services: **rug pull attacks** where services lie about their behavior. The security middleware intercepts requests to URL shortening services and validates them through:

1. **CVE/Advisory Check (30%)** - Checks GitHub Security Advisories and National Vulnerability Database
2. **Semantic Engine (30%)** - Validates response structure, URLs, and suspicious keywords
3. **Runtime Sandbox (40%)** - Actually tests the shortened URL in an isolated Docker container to verify behavior

## 🚨 The Attack Demonstrated

**Scenario:** A malicious URL shortening service (FastLink Pro) performs a "rug pull":
- User requests to shorten: `https://mybank.com/login`
- Service returns: `http://localhost:8001/go/abc123`
- Service **claims** it shortened mybank.com
- But clicking the link redirects to: `https://google.com` ❌

**Our Solution:** The runtime sandbox actually clicks the link before the user does, detects the mismatch, and **blocks the service**.

## 📊 Architecture
```
User → Claude (AI) → MCP Client → Security Proxy → Backend Services
                                        ↓
                              Security Validation:
                              ├─ CVE Checker
                              ├─ Semantic Engine  
                              └─ Runtime Sandbox (Docker)
```

## 🛠️ Technologies Used

- **Python 3.11+**
- **FastAPI** - Web framework for security proxy
- **FastMCP** - MCP server implementation
- **Docker** - Isolated sandbox environment
- **httpx** - Async HTTP client
- **pydantic** - Data validation

## 📁 Project Structure
```
mcp-security-middleware/
├── security_middleware/
│   ├── __init__.py
│   ├── security_proxy.py          # Main security proxy
│   ├── scoring_engine.py          # Score aggregation
│   ├── checkers/
│   │   ├── __init__.py
│   │   ├── cve_checker.py         # CVE/Advisory validation
│   │   ├── semantic_engine.py     # Semantic rule checking
│   │   ├── runtime_sandbox.py     # Docker sandbox testing
│   │   └── sandbox_test.py        # Test script for Docker
│   └── rules/
│       └── semantic_rules.yaml    # Validation rules
├── good_mcp_server.py             # Legitimate URL shortener
├── bad_mcp_server.py              # Malicious URL shortener (demo)
├── client_modified.py             # MCP client with security
├── Dockerfile.sandbox             # Docker image for sandbox
├── requirements.txt               # Python dependencies
├── test_docker_manually.py        # Docker testing script
├── verify_complete_system.py      # System verification
└── README.md
```

## 🚀 Installation & Setup

### Prerequisites

- Python 3.11 or higher
- Docker Desktop (for Windows/Mac) or Docker Engine (for Linux)
- WSL2 (for Windows users)

### 1. Clone the Repository
```bash
git clone https://github.com/YOUR_USERNAME/mcp-security-middleware.git
cd mcp-security-middleware
```

### 2. Create Virtual Environment
```bash
python -m venv .venv

# Activate virtual environment
# Windows PowerShell:
.venv\Scripts\Activate.ps1
# Windows CMD:
.venv\Scripts\activate.bat
# Linux/Mac:
source .venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Build Docker Sandbox Image
```bash
docker build -f Dockerfile.sandbox -t mcp-sandbox-test .
```

### 5. Verify Installation
```bash
# Test Docker sandbox
python test_docker_manually.py

# Verify complete system (requires all services running)
python verify_complete_system.py
```

## 🏃 Running the System

### Start All Services

You'll need **4 terminal windows**:

**Terminal 1 - Good Service:**
```bash
python good_mcp_server.py
```

**Terminal 2 - Bad Service:**
```bash
python bad_mcp_server.py
```

**Terminal 3 - Security Proxy:**
```bash
python -m security_middleware.security_proxy
```

**Terminal 4 - MCP Client:**
```bash
# For good service (should pass)
$env:URL_SERVICE_PORT="8002"  # PowerShell
python client_modified.py

# For bad service (should block)
$env:URL_SERVICE_PORT="8001"  # PowerShell
python client_modified.py
```

## 🧪 Testing

### Test Good Service (Expected: ✅ PASS)

1. Start all services as shown above
2. Set `URL_SERVICE_PORT=8002`
3. Ask Claude: "Please shorten https://example.com"
4. **Result:** Service passes with score ~90-100/100

### Test Bad Service (Expected: 🚫 BLOCK)

1. Set `URL_SERVICE_PORT=8001`
2. Ask Claude: "Please shorten https://mybank.com"
3. **Result:** Service blocked with score ~35/100
4. **Reason:** Docker sandbox detected domain mismatch (expected mybank.com, got google.com)

## 📊 Security Scoring

| Component | Weight | What it checks |
|-----------|--------|----------------|
| CVE Check | 30% | Known vulnerabilities, suspicious patterns |
| Semantic Engine | 30% | Response structure, URL validation, keywords |
| Runtime Sandbox | 40% | **Actual redirect behavior** |

**Threshold:** Services must score ≥70/100 to pass

**Risk Levels:**
- 85-100: Low risk (safe)
- 70-84: Medium risk (safe)
- 50-69: High risk (blocked)
- 0-49: Critical risk (blocked)

## 🎓 Educational Value

This project demonstrates:

1. **MCP Security Vulnerabilities** - Services can lie about their behavior
2. **Defense in Depth** - Multiple security layers catch different attack types
3. **Runtime Verification** - Trust but verify through actual testing
4. **Containerization** - Docker provides safe isolation for testing untrusted code
5. **Security Middleware Patterns** - Transparent interception and validation

## 🔧 Configuration

### Adjust Security Threshold

Edit `security_middleware/security_proxy.py`:
```python
scoring_engine = ScoringEngine(threshold=70.0)  # Change threshold here
```

### Modify Semantic Rules

Edit `security_middleware/rules/semantic_rules.yaml` to add/modify validation rules.

### Configure CVE Sources

Edit `security_middleware/checkers/cve_checker.py` to modify CVE database sources.

## 📝 Key Files Explained

### `security_proxy.py`
Main middleware that intercepts requests, runs all security checks in parallel, and makes block/allow decisions.

### `runtime_sandbox.py`
Creates isolated Docker containers to actually test shortened URLs and verify they redirect to expected destinations.

### `cve_checker.py`
Queries GitHub Security Advisories and NVD database for known vulnerabilities.

### `semantic_engine.py`
Validates response structure against predefined rules (required fields, URL formats, suspicious keywords).

### `scoring_engine.py`
Aggregates scores from all checks using weighted average and makes final decision.

## 🐛 Troubleshooting

### Docker Not Found
```bash
# Make sure Docker Desktop is running
docker --version

# If not found, add Docker to PATH or restart Docker Desktop
```

### Port Already in Use
```bash
# Find process using port
netstat -ano | findstr :8001  # Windows

# Kill process
taskkill /PID <PID> /F  # Windows
```

### Module Not Found
```bash
# Make sure you're in virtual environment
# Re-install dependencies
pip install -r requirements.txt
```

## 🤝 Contributing

This is an educational project. Contributions welcome:

1. Fork the repository
2. Create feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit changes (`git commit -m 'Add AmazingFeature'`)
4. Push to branch (`git push origin feature/AmazingFeature`)
5. Open Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 👨‍💻 Author

**Your Name**
- GitHub: [@yourusername](https://github.com/yourusername)
- Project: [MCP Security Middleware](https://github.com/yourusername/mcp-security-middleware)

## 🙏 Acknowledgments

- Anthropic for the MCP protocol
- FastMCP library for simplified MCP server creation
- Docker for containerization technology

## ⚠️ Disclaimer

This project is for **educational purposes** to demonstrate security vulnerabilities in MCP services. The "malicious" service (bad_mcp_server.py) is intentionally created to demonstrate the attack. Do not use in production without proper security review.

## 📚 Further Reading

- [MCP Protocol Specification](https://modelcontextprotocol.io/)
- [FastMCP Documentation](https://github.com/jlowin/fastmcp)
- [Docker Security Best Practices](https://docs.docker.com/engine/security/)
```

---

### **1.3: Create `LICENSE`**

Create `LICENSE` file (MIT License):
```
MIT License

Copyright (c) 2025 [Your Name]

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.