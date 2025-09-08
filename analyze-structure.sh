#!/bin/bash
# Structure Analysis Script for ZenGlow Project
# Pre-Cleanup Analysis Tool

echo "=== ZenGlow Project Structure Analysis ==="
echo "Analysis Date: $(date)"
echo "Analysis Location: $(pwd)"
echo ""

# Check if nested ZenGlow directory exists
if [ -d "./ZenGlow" ]; then
    echo "✅ Nested ZenGlow directory found at: ./ZenGlow"
    NESTED_EXISTS=true
else
    echo "❌ No nested ZenGlow directory found"
    echo "📝 This suggests cleanup may have already been performed"
    NESTED_EXISTS=false
fi

echo ""
echo "=== Root Directory Analysis ==="
echo "Root files modified in last 7 days:"
find . -maxdepth 2 -newermt "$(date -d '7 days ago' +%Y-%m-%d)" -not -path "./ZenGlow/*" -not -path "./.git/*" -type f | sort

echo ""
echo "=== File Count Analysis ==="
echo "Root JS/TS files: $(find . -maxdepth 3 -name "*.js" -o -name "*.ts" -o -name "*.tsx" -o -name "*.jsx" | grep -v "./ZenGlow/" | grep -v "./node_modules/" | wc -l)"
echo "Root JSON config files: $(find . -maxdepth 2 -name "*.json" | grep -v "./ZenGlow/" | grep -v "./node_modules/" | wc -l)"
echo "Root component files: $(find ./components -name "*.tsx" -o -name "*.ts" 2>/dev/null | wc -l)"

if [ "$NESTED_EXISTS" = true ]; then
    echo ""
    echo "=== Nested Directory Analysis ==="
    echo "Nested files modified in last 7 days:"
    find ./ZenGlow -newermt "$(date -d '7 days ago' +%Y-%m-%d)" -not -path "./.git/*" -type f | sort
    
    echo ""
    echo "Nested JS/TS files: $(find ./ZenGlow -name "*.js" -o -name "*.ts" -o -name "*.tsx" -o -name "*.jsx" | grep -v "./node_modules/" | wc -l)"
    echo "Nested JSON config files: $(find ./ZenGlow -name "*.json" | grep -v "./node_modules/" | wc -l)"
    echo "Nested component files: $(find ./ZenGlow -name "*.tsx" -o -name "*.ts" 2>/dev/null | wc -l)"
fi

echo ""
echo "=== Configuration File Analysis ==="
echo "Root configuration files:"
ls -la *.json *.js *.ts 2>/dev/null | grep -E "\.(json|js|ts|config\.|rc\.|eslint)" | head -10

if [ "$NESTED_EXISTS" = true ]; then
    echo ""
    echo "Nested configuration files:"
    ls -la ./ZenGlow/*.json ./ZenGlow/*.js ./ZenGlow/*.ts 2>/dev/null | grep -E "\.(json|js|ts|config\.|rc\.|eslint)" | head -10
fi

echo ""
echo "=== Package.json Comparison ==="
if [ -f "package.json" ]; then
    echo "Root package.json size: $(wc -l < package.json) lines"
    echo "Root package.json exists: ✅"
else
    echo "Root package.json: ❌ Missing"
fi

if [ "$NESTED_EXISTS" = true ] && [ -f "ZenGlow/package.json" ]; then
    echo "Nested package.json size: $(wc -l < ZenGlow/package.json) lines" 
    echo "Nested package.json exists: ✅"
elif [ "$NESTED_EXISTS" = true ]; then
    echo "Nested package.json: ❌ Missing"
fi

echo ""
echo "=== Directory Structure Overview ==="
echo "Root directory structure (2 levels):"
tree -L 2 -I 'node_modules|.git|ZenGlow' . 2>/dev/null || find . -maxdepth 2 -type d | grep -v -E '(node_modules|\.git|ZenGlow)' | sort

if [ "$NESTED_EXISTS" = true ]; then
    echo ""
    echo "Nested directory structure (2 levels):"
    tree -L 2 -I 'node_modules|.git' ./ZenGlow 2>/dev/null || find ./ZenGlow -maxdepth 2 -type d | grep -v -E '(node_modules|\.git)' | sort
fi

echo ""
echo "=== Analysis Complete ==="
echo "Report generated: $(date)"