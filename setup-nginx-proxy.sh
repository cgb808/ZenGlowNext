#!/bin/bash

# ZenGlow Nginx Setup Script
# This script builds and runs nginx with proxy configuration

set -e

echo "🧘‍♀️ ZenGlow Nginx Proxy Server Setup"
echo "=================================="

# Check if we're in the right directory
if [ ! -f "docker-compose.yml" ]; then
    echo "❌ Error: Please run this script from the ZenGlow root directory"
    exit 1
fi

# Create sample images for testing
echo "📁 Creating sample images directory..."
mkdir -p nginx/sample-images
cd nginx/sample-images

# Download or create sample images (using placeholder service)
if command -v curl &> /dev/null; then
    echo "📥 Downloading sample images..."
    curl -s -o zenglow-logo.png "https://via.placeholder.com/300x200/667eea/ffffff?text=ZenGlow+Logo"
    curl -s -o meditation.jpg "https://via.placeholder.com/400x300/764ba2/ffffff?text=Meditation"
    curl -s -o wellness.gif "https://via.placeholder.com/200x200/22c55e/ffffff?text=Wellness"
else
    echo "📝 Creating placeholder image files..."
    echo "ZenGlow Logo Placeholder" > zenglow-logo.png
    echo "Meditation Image Placeholder" > meditation.jpg
    echo "Wellness GIF Placeholder" > wellness.gif
fi

cd ../..

# Build nginx container
echo "🔨 Building nginx container..."
docker-compose build nginx

# Start the services
echo "🚀 Starting ZenGlow services..."
docker-compose up -d

# Wait for services to be ready
echo "⏳ Waiting for services to start..."
sleep 10

# Check service status
echo "🔍 Checking service status..."
docker-compose ps

# Test the proxy server
echo "🧪 Testing proxy server..."
echo ""
echo "Testing proxy server (port 80 -> 8080):"
if command -v curl &> /dev/null; then
    echo "HTTP Response:"
    curl -s -w "Status: %{http_code}\n" http://localhost/ | head -5
    echo ""
    
    echo "Health check:"
    curl -s http://localhost/health
    echo ""
    
    echo "Testing image serving:"
    curl -s -I http://localhost/zenglow-logo.png | grep -E "HTTP|Content-Type"
else
    echo "Install curl to test the proxy server automatically"
    echo "Manual test URLs:"
    echo "  - Main page: http://localhost/"
    echo "  - Health check: http://localhost/health"
    echo "  - Sample image: http://localhost/zenglow-logo.png"
fi

echo ""
echo "✅ ZenGlow Nginx Proxy Server Setup Complete!"
echo ""
echo "📋 Configuration Summary:"
echo "  - Main server: http://localhost:80"
echo "  - Proxied server: http://localhost:8080"
echo "  - Images served from: /data/images"
echo "  - Proxy passes requests to: http://localhost:8080/"
echo "  - Image requests (*.gif, *.jpg, *.png) served directly"
echo ""
echo "📁 Directory Structure:"
echo "  - /data/up1/ - Proxied server content"
echo "  - /data/images/ - Direct image serving"
echo ""
echo "🔧 Useful Commands:"
echo "  - View logs: docker-compose logs nginx"
echo "  - Restart nginx: docker-compose restart nginx"
echo "  - Stop services: docker-compose down"
echo "  - Rebuild: docker-compose build nginx"
