#!/bin/bash

# ZenDexer Wearables Local Test Script

echo "🎯 ZenDexer Wearables Integration - Local Test"
echo "=" ================================================

# Check if Python virtual environment exists
if [ ! -d "venv" ]; then
    echo "📦 Creating Python virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "🔄 Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "📥 Installing dependencies..."
pip install -r wearables/requirements.txt

# Start SmolLM2 predictor in background
echo "🧠 Starting SmolLM2 predictor..."
python smollm2_predictor.py &
PREDICTOR_PID=$!

# Wait for predictor to start
echo "⏳ Waiting for predictor to start..."
sleep 5

# Test predictor health
echo "🔍 Testing predictor health..."
curl -f http://localhost:8002/health || echo "⚠️  Predictor not responding"

# Run wearables edge model test
echo "📱 Testing wearables edge model..."
cd wearables
python edge_model.py

# Cleanup
echo "🧹 Cleaning up..."
kill $PREDICTOR_PID 2>/dev/null || true

echo "✅ Local test completed!"
echo "Check the output above for any errors or warnings."
