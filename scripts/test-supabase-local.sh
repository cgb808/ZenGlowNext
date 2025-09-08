#!/bin/bash

# ZenGlow Local Supabase Test Script
# This script validates the local Supabase setup

set -e

echo "🧘‍♀️ ZenGlow Local Supabase Setup Validation"
echo "==============================================="

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "❌ .env file not found. Please copy .env.example to .env and configure it."
    exit 1
fi

echo "✅ .env file found"

# Check if Docker is available
if ! command -v docker &> /dev/null; then
    echo "❌ Docker not found. Please install Docker to use local Supabase."
    exit 1
fi

echo "✅ Docker is available"

# Check if Docker Compose is available
if ! command -v docker &> /dev/null || ! docker compose version &> /dev/null; then
    echo "❌ Docker Compose not available. Please install Docker Compose."
    exit 1
fi

echo "✅ Docker Compose is available"

# Validate docker-compose.yml
echo "🔍 Validating docker-compose configuration..."
if docker compose config > /dev/null 2>&1; then
    echo "✅ docker-compose.yml is valid"
else
    echo "❌ docker-compose.yml has configuration errors"
    exit 1
fi

# Check if required files exist
required_files=(
    "supabase/kong.yml"
    "Docs/supabase-local.md"
    ".env.example"
)

for file in "${required_files[@]}"; do
    if [ -f "$file" ]; then
        echo "✅ Required file exists: $file"
    else
        echo "❌ Missing required file: $file"
        exit 1
    fi
done

# Check if services are running (optional)
echo "🔍 Checking if Supabase services are running..."
if docker compose ps | grep -q "supabase-db.*Up"; then
    echo "✅ Supabase database is running"
    
    if docker compose ps | grep -q "supabase-kong.*Up"; then
        echo "✅ Supabase API gateway is running"
        
        # Test API endpoint
        if curl -s http://localhost:8000 > /dev/null 2>&1; then
            echo "✅ Supabase API gateway is accessible"
        else
            echo "⚠️  Supabase API gateway is not responding (this is normal if services just started)"
        fi
    else
        echo "ℹ️  Supabase services are not running (start with: docker compose up -d)"
    fi
else
    echo "ℹ️  Supabase services are not running (start with: docker compose up -d)"
fi

echo ""
echo "🎉 Local Supabase setup validation complete!"
echo ""
echo "Next steps:"
echo "1. Start services: docker compose up -d"
echo "2. Check status: docker compose ps"
echo "3. View logs: docker compose logs supabase-kong"
echo "4. Read the guide: Docs/supabase-local.md"