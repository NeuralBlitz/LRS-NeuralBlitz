#!/bin/bash
# Raspberry Pi Deployment Script for NeuralBlitz Edge

set -e

echo "=========================================="
echo "NeuralBlitz Raspberry Pi Deployment"
echo "=========================================="

# Configuration
INSTALL_DIR="/opt/neuralblitz"
USER="pi"
MODEL_URL="https://models.neuralblitz.io/edge/mobilenet_v2_int8.tflite"

# Update system
echo "[1/7] Updating system packages..."
sudo apt update && sudo apt upgrade -y

# Install dependencies
echo "[2/7] Installing dependencies..."
sudo apt install -y \
    python3-pip \
    python3-venv \
    libatlas-base-dev \
    libopenblas-dev \
    libblas-dev \
    liblapack-dev \
    gfortran \
    htop \
    i2c-tools \
    libcamera-dev \
    python3-picamera2

# Create installation directory
echo "[3/7] Creating installation directory..."
sudo mkdir -p $INSTALL_DIR
sudo chown $USER:$USER $INSTALL_DIR

# Setup Python environment
echo "[4/7] Setting up Python environment..."
cd $INSTALL_DIR
python3 -m venv venv
source venv/bin/activate

# Install Python packages
echo "[5/7] Installing Python packages..."
pip install --upgrade pip wheel
pip install numpy==1.24.3
pip install tflite-runtime==2.13.0
pip install pillow==9.5.0
pip install psutil==5.9.5
pip install opencv-python-headless==4.8.0.74

# Download model
echo "[6/7] Downloading optimized model..."
mkdir -p models
if command -v wget &> /dev/null; then
    wget -q $MODEL_URL -O models/mobilenet_v2_int8.tflite || echo "Warning: Could not download model"
elif command -v curl &> /dev/null; then
    curl -sL $MODEL_URL -o models/mobilenet_v2_int8.tflite || echo "Warning: Could not download model"
else
    echo "Warning: Neither wget nor curl available. Please manually download the model."
fi

# Install inference engine
echo "[7/7] Installing inference engine..."
cat > raspberry_pi_inference.py << 'PYEOF'
#!/usr/bin/env python3
import os, time, json, logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import numpy as np
from PIL import Image

try:
    import tflite_runtime.interpreter as tflite
except ImportError:
    import tensorflow.lite as tflite

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('RaspberryPiInference')

@dataclass
class InferenceConfig:
    model_path: str
    input_shape: Tuple[int, ...] = (1, 224, 224, 3)
    num_threads: int = 4
    use_xnnpack: bool = True
    batch_size: int = 1
    warmup_runs: int = 10

class RaspberryPiInferenceEngine:
    def __init__(self, config: InferenceConfig):
        self.config = config
        self.interpreter = None
        self.input_details = None
        self.output_details = None
        self._initialized = False
        self.metrics = {
            'inference_times': [],
            'total_predictions': 0,
            'avg_latency_ms': 0.0,
            'throughput_fps': 0.0,
            'memory_mb': 0.0
        }
        
    def initialize(self) -> bool:
        try:
            logger.info(f"Loading model: {self.config.model_path}")
            self.interpreter = tflite.Interpreter(
                model_path=self.config.model_path,
                num_threads=self.config.num_threads
            )
            self.interpreter.allocate_tensors()
            self.input_details = self.interpreter.get_input_details()
            self.output_details = self.interpreter.get_output_details()
            self._initialized = True
            self._warmup()
            return True
        except Exception as e:
            logger.error(f"Failed to initialize: {e}")
            return False
    
    def _warmup(self):
        dummy_input = np.zeros(self.config.input_shape, dtype=np.float32)
        for _ in range(self.config.warmup_runs):
            self._infer_single(dummy_input)
    
    def _infer_single(self, input_data: np.ndarray) -> np.ndarray:
        self.interpreter.set_tensor(self.input_details[0]['index'], input_data)
        self.interpreter.invoke()
        return self.interpreter.get_tensor(self.output_details[0]['index'])
    
    def infer(self, input_data: np.ndarray) -> Tuple[np.ndarray, Dict]:
        start_time = time.perf_counter()
        output = self._infer_single(input_data)
        latency_ms = (time.perf_counter() - start_time) * 1000
        self.metrics['inference_times'].append(latency_ms)
        self.metrics['total_predictions'] += 1
        self.metrics['avg_latency_ms'] = np.mean(self.metrics['inference_times'][-100:])
        self.metrics['throughput_fps'] = 1000.0 / self.metrics['avg_latency_ms']
        return output, {'latency_ms': latency_ms, 'timestamp': time.time()}

if __name__ == "__main__":
    config = InferenceConfig(model_path="models/mobilenet_v2_int8.tflite")
    engine = RaspberryPiInferenceEngine(config)
    if engine.initialize():
        print("Engine initialized successfully")
        # Benchmark
        input_data = np.random.randn(1, 224, 224, 3).astype(np.float32)
        for _ in range(100):
            engine.infer(input_data)
        print(f"Avg latency: {engine.metrics['avg_latency_ms']:.2f} ms")
PYEOF

chmod +x raspberry_pi_inference.py

# Create systemd service
echo "Creating systemd service..."
sudo tee /etc/systemd/system/neuralblitz-edge.service > /dev/null << EOF
[Unit]
Description=NeuralBlitz Edge Inference Service
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$INSTALL_DIR
Environment="PATH=$INSTALL_DIR/venv/bin"
Environment="PYTHONPATH=$INSTALL_DIR"
Environment="TF_CPP_MIN_LOG_LEVEL=2"
ExecStart=$INSTALL_DIR/venv/bin/python $INSTALL_DIR/raspberry_pi_inference.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

# Enable service
sudo systemctl daemon-reload
sudo systemctl enable neuralblitz-edge.service

# Performance tuning
echo "Applying performance optimizations..."

# Disable swap to prevent SD card wear
if command -v dphys-swapfile &> /dev/null; then
    sudo dphys-swapfile swapoff || true
    sudo dphys-swapfile uninstall || true
    sudo update-rc.d dphys-swapfile remove || true
fi

# Set CPU governor to performance
echo 'GOVERNOR="performance"' | sudo tee /etc/default/cpufrequtils || true

# Enable I2C and camera
sudo raspi-config nonint do_i2c 0 2>/dev/null || true
sudo raspi-config nonint do_camera 0 2>/dev/null || true

# Create performance monitoring script
cat > $INSTALL_DIR/monitor.sh << 'EOF'
#!/bin/bash
echo "NeuralBlitz Edge Monitor"
echo "========================"
while true; do
    echo -e "\n$(date)"
    if command -v vcgencmd &> /dev/null; then
        echo "CPU Temp: $(vcgencmd measure_temp)"
    fi
    echo "CPU Usage: $(top -bn1 | grep "Cpu(s)" | awk '{print $2}' | cut -d'%' -f1)%"
    echo "Memory: $(free -h | grep Mem | awk '{print $3"/"$2}')"
    sleep 5
done
EOF
chmod +x $INSTALL_DIR/monitor.sh

echo ""
echo "=========================================="
echo "Deployment Complete!"
echo "=========================================="
echo "Installation directory: $INSTALL_DIR"
echo "Start service: sudo systemctl start neuralblitz-edge"
echo "View logs: sudo journalctl -u neuralblitz-edge -f"
echo "Monitor: $INSTALL_DIR/monitor.sh"
echo "=========================================="