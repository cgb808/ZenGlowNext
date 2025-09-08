#!/bin/bash
"""
Model Quantization Setup for Codespace
Installs dependencies and validates the quantization environment
"""

set -e

echo "🚀 Setting up Model Quantization for Codespace"
echo "=============================================="

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check Python version
echo "🐍 Checking Python installation..."
if command_exists python3; then
    PYTHON_VERSION=$(python3 --version)
    echo "✅ Found: $PYTHON_VERSION"
else
    echo "❌ Python 3 not found"
    exit 1
fi

# Check pip
if command_exists pip3; then
    echo "✅ pip3 is available"
elif command_exists pip; then
    echo "✅ pip is available"
else
    echo "❌ pip not found"
    exit 1
fi

# Install quantization dependencies
echo ""
echo "📦 Installing quantization dependencies..."
echo "This may take a few minutes..."

# Create a virtual environment if requested
if [[ "$1" == "--venv" ]]; then
    echo "🔧 Creating virtual environment..."
    python3 -m venv quantization_env
    source quantization_env/bin/activate
    echo "✅ Virtual environment activated"
fi

# Upgrade pip first
pip install --upgrade pip

# Install core dependencies
echo "Installing core ML libraries..."
pip install torch>=2.0.0 --index-url https://download.pytorch.org/whl/cpu

echo "Installing transformers and quantization libraries..."
pip install transformers>=4.35.0 accelerate>=0.24.0 peft>=0.6.0

echo "Installing bitsandbytes..."
pip install bitsandbytes>=0.41.0

echo "Installing GGUF support..."
pip install llama-cpp-python>=0.2.0 ctransformers>=0.2.0

echo "Installing utilities..."
pip install numpy pandas psutil GPUtil pytest jupyter ipykernel

echo "✅ Dependencies installed successfully!"

# Validate installation
echo ""
echo "🔍 Validating installation..."

python3 -c "
import sys
print(f'Python: {sys.version}')

try:
    import torch
    print(f'✅ PyTorch: {torch.__version__}')
except ImportError as e:
    print(f'❌ PyTorch: {e}')

try:
    import transformers
    print(f'✅ Transformers: {transformers.__version__}')
except ImportError as e:
    print(f'❌ Transformers: {e}')

try:
    import peft
    print(f'✅ PEFT: {peft.__version__}')
except ImportError as e:
    print(f'❌ PEFT: {e}')

try:
    import bitsandbytes
    print('✅ BitsAndBytes: Available')
except ImportError as e:
    print(f'❌ BitsAndBytes: {e}')

try:
    import llama_cpp
    print('✅ llama-cpp-python: Available')
except ImportError as e:
    print(f'❌ llama-cpp-python: {e}')

print('\\n🎉 Validation complete!')
"

echo ""
echo "🎯 Next steps:"
echo "1. Run QLoRA quantization test:"
echo "   python3 ai-workspace/quantization/qlora_quantization.py"
echo ""
echo "2. Run GGUF quantization test:"
echo "   python3 ai-workspace/quantization/gguf_quantization.py"
echo ""
echo "3. Check the results in quantization_results.json and gguf_results.json"
echo ""
echo "🎉 Model quantization setup complete!"