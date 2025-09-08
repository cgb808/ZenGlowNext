#!/bin/bash

# ZenDexer TensorFlow Lite Training Setup Script

echo "🎯 ZenDexer TensorFlow Lite Training Setup"
echo "=" "========================================="

# Create virtual environment for training
if [ ! -d "training/venv" ]; then
    echo "📦 Creating training virtual environment..."
    cd training
    python3 -m venv venv
    source venv/bin/activate
    pip install --upgrade pip
    pip install -r requirements.txt
    cd ..
else
    echo "✅ Training environment already exists"
fi

# Create placeholder data directories
echo "📁 Setting up data directories..."
mkdir -p data/raw
mkdir -p data/processed  
mkdir -p data/synthetic

# Create placeholder model directories
echo "📁 Setting up model directories..."
mkdir -p models/trained
mkdir -p models/tflite
mkdir -p models/artifacts

# Create placeholder evaluation directories
echo "📁 Setting up evaluation directories..."
mkdir -p evaluation/metrics
mkdir -p evaluation/tests

# Create placeholder deployment directories  
echo "📁 Setting up deployment directories..."
mkdir -p deployment/android
mkdir -p deployment/ios
mkdir -p deployment/testing

echo "✅ TensorFlow Lite training environment setup complete!"
echo ""
echo "📋 Next steps:"
echo "1. Add your training data to data/raw/"
echo "2. Activate training environment: source training/venv/bin/activate"
echo "3. Run training: python training/train_model.py"
echo "4. Test models in evaluation/"
echo "5. Deploy optimized models to devices"
