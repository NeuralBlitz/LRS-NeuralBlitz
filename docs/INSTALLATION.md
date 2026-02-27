# 📖 Installation Guide

**Complete Setup Instructions for OpenCode LRS**

---

## 🚀 **System Requirements**

### **Minimum Requirements**
- **Python**: 3.8+ (3.11+ recommended)
- **Memory**: 4GB RAM (8GB+ for advanced features)
- **Storage**: 2GB free space
- **Network**: Internet connection for AI model access
- **OS**: Windows 10+, macOS 10.15+, Ubuntu 18.04+

### **Recommended Requirements**
- **Python**: 3.11+ with latest pip
- **Memory**: 16GB+ RAM
- **Storage**: 20GB+ SSD
- **CPU**: 8+ cores for parallel processing
- **GPU**: NVIDIA GPU with CUDA (quantum/neural features)

### **Quantum Computing Requirements**
- **Qiskit**: IBM Quantum Experience account
- **Memory**: 32GB+ RAM for large quantum circuits
- **GPU**: Optional for accelerated quantum simulation

---

## 📥 **Installation Methods**

### **Method 1: Quick Install (Recommended)**
```bash
# Clone the repository
git clone https://github.com/NeuralBlitz/opencode-lrs
cd opencode-lrs

# Install with automatic dependency resolution
pip install -e .
pip install -e ./lrs_agents

# Setup configuration
python setup_lrs_integration.py

# Start the platform
python main.py
```

### **Method 2: Manual Install**
```bash
# Clone repository
git clone https://github.com/NeuralBlitz/opencode-lrs
cd opencode-lrs

# Create virtual environment
python -m venv opencode-env
source opencode-env/bin/activate  # On Windows: opencode-env\\Scripts\\activate

# Upgrade pip
pip install --upgrade pip

# Install core dependencies
pip install fastapi uvicorn pydantic
pip install numpy scipy matplotlib
pip install qiskit networkx
pip install pytest pytest-cov

# Install LRS-Agents
cd lrs_agents
pip install -e .
cd ..

# Verify installation
python -c "import lrs_agents; print('✅ LRS-Agents installed successfully')"
```

### **Method 3: Docker Install**
```bash
# Pull the Docker image
docker pull opencode-lrs/latest

# Run with default configuration
docker run -p 8000:8000 opencode-lrs/latest

# Or build from source
git clone https://github.com/NeuralBlitz/opencode-lrs
cd opencode-lrs
docker build -t opencode-lrs .
docker run -p 8000:8000 opencode-lrs
```

---

## 🔧 **Configuration Setup**

### **1. Environment Configuration**
Create `.env` file:
```bash
# AI Model Configuration
OPENAI_API_KEY=your_openai_api_key
ANTHROPIC_API_KEY=your_anthropic_api_key

# Database Configuration
DATABASE_URL=postgresql://user:pass@localhost/opencode_lrs
REDIS_URL=redis://localhost:6379

# Security Configuration
SECRET_KEY=your_secret_key_here
JWT_ALGORITHM=HS256
JWT_EXPIRE_HOURS=24

# Quantum Computing (Optional)
IBM_QUANTUM_TOKEN=your_ibm_quantum_token
QUANTUM_BACKEND=ibmq_qasm_simulator
```

### **2. Database Setup**
```bash
# PostgreSQL setup
sudo apt-get install postgresql postgresql-contrib
sudo -u postgres createdb opencode_lrs
sudo -u postgres createuser opencode_user
sudo -u postgres psql -c "ALTER USER opencode_user PASSWORD 'your_password';"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE opencode_lrs TO opencode_user;"

# Redis setup (optional, for caching)
sudo apt-get install redis-server
redis-server --daemonize yes
```

### **3. LRS-Agents Configuration**
```bash
# Run LRS integration setup
python setup_lrs_integration.py

# Verify configuration
python -c "
from lrs_agents.lrs import create_lrs_agent
agent = create_lrs_agent()
print('✅ LRS-Agents configured successfully')
"
```

---

## 🧪 **Verification & Testing**

### **1. Basic Verification**
```bash
# Test Python imports
python -c "
import lrs_agents
from main import app
print('✅ Core imports successful')
"

# Test API server startup
python main.py --port 8001 &
sleep 5
curl http://localhost:8001/docs
pkill -f main.py
```

### **2. Run Test Suite**
```bash
# Run all tests
cd lrs_agents
python -m pytest tests/ -v

# Run specific test categories
python -m pytest tests/test_free_energy.py -v
python -m pytest tests/test_precision.py -v
python -m pytest tests/test_integration_langgraph.py -v
```

### **3. Test Advanced Features**
```bash
# Test autonomous self-evolution
python autonomous_self_evolution_simplified.py

# Test quantum foundation
python quantum_foundation_demo.py

# Test neuro-symbiotic integration
python neuro_symbiotic_demo.py

# Test dimensional computing
python dimensional_computing_demo.py
```

---

## 🐛 **Troubleshooting**

### **Common Issues**

#### **Import Errors**
```bash
# If you get "No module named 'lrs_agents'"
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
export PYTHONPATH="${PYTHONPATH}:$(pwd)/lrs_agents"

# Or install in development mode
pip install -e ./lrs_agents
```

#### **Memory Issues**
```bash
# For quantum simulations, increase memory limits
export OMP_NUM_THREADS=1
export MKL_NUM_THREADS=1

# Use lighter configurations for systems with <8GB RAM
python main.py --lightweight-mode
```

#### **Database Connection Issues**
```bash
# Check PostgreSQL status
sudo systemctl status postgresql

# Test connection
psql -h localhost -U opencode_user -d opencode_lrs

# Reset database if needed
dropdb opencode_lrs && createdb opencode_lrs
```

#### **Port Conflicts**
```bash
# Check what's using port 8000
lsof -i :8000

# Use different port
python main.py --port 8001
```

### **Platform-Specific Issues**

#### **Windows**
```bash
# Use Windows-style paths in .env
DATABASE_URL=postgresql://user:pass@localhost/opencode_lrs

# Activate virtual environment
opencode-env\\Scripts\\activate

# Use PowerShell if Command Prompt has issues
powershell -ExecutionPolicy Bypass -File setup.ps1
```

#### **macOS**
```bash
# Install Xcode command line tools
xcode-select --install

# Use Homebrew for dependencies
brew install postgresql redis python3

# Fix OpenMP issues
export CC=gcc-omp
export CXX=g++-omp
```

#### **Linux**
```bash
# Install system dependencies
sudo apt-get update
sudo apt-get install python3-dev python3-pip
sudo apt-get install postgresql redis-server
sudo apt-get install libopenblas-dev liblapack-dev

# Fix permission issues
sudo chown -R $USER:$USER ~/.local
```

---

## 🔧 **Advanced Configuration**

### **Performance Optimization**
```bash
# Enable parallel processing
export OMP_NUM_THREADS=4
export MKL_NUM_THREADS=4

# GPU acceleration (if available)
export CUDA_VISIBLE_DEVICES=0
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
```

### **Development Setup**
```bash
# Install development dependencies
pip install -e ".[dev]"

# Setup pre-commit hooks
pre-commit install

# Enable development mode
export OPENCODE_ENV=development
export DEBUG=true
```

### **Enterprise Setup**
```bash
# Install enterprise dependencies
pip install -e ".[enterprise]"

# Setup monitoring
pip install prometheus-client grafana-api

# Configure security
pip install python-multipart python-jose[cryptography]
```

---

## 📊 **Performance Tuning**

### **Memory Optimization**
```python
# In your configuration
CONFIG = {
    "memory_optimization": {
        "batch_size": 1000,
        "max_history": 10000,
        "cache_size": 500,
        "lightweight_mode": True  # For <8GB RAM
    }
}
```

### **CPU Optimization**
```python
# Parallel processing configuration
CONFIG = {
    "parallel_processing": {
        "num_workers": 4,  # Number of CPU cores
        "chunk_size": 100,
        "use_multiprocessing": True
    }
}
```

### **Quantum Optimization**
```python
# Quantum simulation settings
CONFIG = {
    "quantum": {
        "backend": "qasm_simulator",
        "shots": 1000,
        "optimization_level": 2,
        "use_real_quantum": False  # Set to True with IBMQ account
    }
}
```

---

## 🌐 **Network Configuration**

### **Proxy Setup**
```bash
# Set proxy for downloads
export HTTP_PROXY=http://proxy.company.com:8080
export HTTPS_PROXY=https://proxy.company.com:8080

# Configure pip
pip install --proxy http://proxy.company.com:8080 package_name
```

### **Firewall Configuration**
```bash
# Open required ports
sudo ufw allow 8000/tcp  # Main API
sudo ufw allow 5432/tcp  # PostgreSQL
sudo ufw allow 6379/tcp  # Redis
sudo ufw allow 9000/tcp  # Integration bridge
```

---

## 📱 **IDE Integration**

### **VS Code Setup**
```json
// .vscode/settings.json
{
    "python.defaultInterpreterPath": "./opencode-env/bin/python",
    "python.linting.enabled": true,
    "python.linting.pylintEnabled": true,
    "python.formatting.provider": "black",
    "python.testing.pytestEnabled": true
}
```

### **JetBrains Setup**
```kotlin
// build.gradle.kts (for IntelliJ plugin development)
plugins {
    python("org.jetbrains.plugins.python")
}
dependencies {
    implementation("org.jetbrains:annotations:23.0.0")
}
```

---

## ✅ **Post-Installation Checklist**

### **Basic Functionality**
- [ ] Platform starts without errors: `python main.py`
- [ ] API documentation accessible: http://localhost:8000/docs
- [ ] Tests pass: `pytest tests/ -v`
- [ ] LRS-Agents imports work: `import lrs_agents`

### **Advanced Features**
- [ ] Quantum demos run: `python quantum_foundation_demo.py`
- [ ] Neuro-symbiotic demo works: `python neuro_symbiotic_demo.py`
- [ ] Self-evolution demo runs: `python autonomous_self_evolution_simplified.py`
- [ ] Dimensional computing works: `python dimensional_computing_demo.py`

### **Enterprise Features**
- [ ] Database connections work
- [ ] Redis caching operational
- [ ] JWT authentication functional
- [ ] Monitoring dashboard accessible

### **Performance Verification**
- [ ] Response time < 100ms for API calls
- [ ] Memory usage within limits
- [ ] CPU utilization reasonable
- [ ] Quantum simulations complete successfully

---

## 🎉 **Success!**

**🚀 Installation Complete!** You're now ready to experience the world's most advanced AI development platform.

### **Next Steps**
1. **Start the Platform**: `python main.py`
2. **Visit API Docs**: http://localhost:8000/docs
3. **Try Quick Demo**: `python lrs_agents/examples/quickstart.py`
4. **Explore Features**: Browse the comprehensive documentation

### **Get Help**
- **Documentation**: [docs.opencode-lrs.com](https://docs.opencode-lrs.com)
- **Community**: [Discord Server](https://discord.gg/opencode-lrs)
- **Issues**: [GitHub Issues](https://github.com/NeuralBlitz/opencode-lrs/issues)
- **Email**: support@opencode-lrs.com

---

**🌟 Welcome to the future of AI-assisted development! Your journey into advanced artificial intelligence starts now.**
