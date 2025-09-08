#!/bin/bash
# Key File Comparison Script for ZenGlow Project
# Compares critical configuration and application files

echo "=== ZenGlow Key File Differences Analysis ==="
echo "Analysis Date: $(date)"
echo ""

# Function to compare files if both exist
compare_files() {
    local root_file="$1"
    local nested_file="$2"
    local file_description="$3"
    
    echo "--- $file_description differences ---"
    
    if [ -f "$root_file" ] && [ -f "$nested_file" ]; then
        echo "Both files exist, comparing..."
        echo "Root file size: $(wc -l < "$root_file") lines"
        echo "Nested file size: $(wc -l < "$nested_file") lines"
        echo ""
        diff "$root_file" "$nested_file" || echo "Files are identical"
    elif [ -f "$root_file" ] && [ ! -f "$nested_file" ]; then
        echo "❌ Only root file exists: $root_file"
        echo "File size: $(wc -l < "$root_file") lines"
    elif [ ! -f "$root_file" ] && [ -f "$nested_file" ]; then
        echo "❌ Only nested file exists: $nested_file"
        echo "File size: $(wc -l < "$nested_file") lines"
    else
        echo "❌ Neither file exists"
    fi
    echo ""
}

# Check if nested directory exists
if [ ! -d "./ZenGlow" ]; then
    echo "⚠️  No nested ZenGlow directory found for comparison"
    echo "📝 Analyzing root project files only"
    echo ""
    
    echo "=== Root Project File Analysis ==="
    
    # Analyze root files
    echo "--- Root package.json analysis ---"
    if [ -f "package.json" ]; then
        echo "✅ package.json exists ($(wc -l < package.json) lines)"
        echo "Key dependencies:"
        grep -A 5 -B 1 '"dependencies"' package.json 2>/dev/null || echo "No dependencies section found"
    else
        echo "❌ package.json missing"
    fi
    echo ""
    
    echo "--- Root App.js analysis ---"
    if [ -f "App.js" ]; then
        echo "✅ App.js exists ($(wc -l < App.js) lines)"
        echo "First 5 lines:"
        head -5 App.js
    elif [ -f "App.tsx" ]; then
        echo "✅ App.tsx exists ($(wc -l < App.tsx) lines)"
        echo "First 5 lines:"
        head -5 App.tsx
    else
        echo "❌ No main App file found"
    fi
    echo ""
    
    echo "--- Root configuration files ---"
    for config_file in tsconfig.json babel.config.js metro.config.js app.json eas.json; do
        if [ -f "$config_file" ]; then
            echo "✅ $config_file exists ($(wc -l < "$config_file") lines)"
        else
            echo "❌ $config_file missing"
        fi
    done
    
    exit 0
fi

# Compare package.json files
compare_files "package.json" "ZenGlow/package.json" "package.json"

# Compare main App files
compare_files "App.js" "ZenGlow/App.js" "App.js"
compare_files "App.tsx" "ZenGlow/App.tsx" "App.tsx"

# Compare TypeScript configuration
compare_files "tsconfig.json" "ZenGlow/tsconfig.json" "tsconfig.json"

# Compare Babel configuration
compare_files "babel.config.js" "ZenGlow/babel.config.js" "babel.config.js"
compare_files ".babelrc" "ZenGlow/.babelrc" ".babelrc"

# Compare Metro configuration
compare_files "metro.config.js" "ZenGlow/metro.config.js" "metro.config.js"

# Compare Expo configurations
compare_files "app.json" "ZenGlow/app.json" "app.json"
compare_files "eas.json" "ZenGlow/eas.json" "eas.json"

# Compare ESLint configurations
compare_files ".eslintrc.json" "ZenGlow/.eslintrc.json" ".eslintrc.json"
compare_files "eslint.config.js" "ZenGlow/eslint.config.js" "eslint.config.js"
compare_files "eslint.config.cjs" "ZenGlow/eslint.config.cjs" "eslint.config.cjs"

# Compare Prettier configuration
compare_files ".prettierrc" "ZenGlow/.prettierrc" ".prettierrc"

# Compare gitignore
compare_files ".gitignore" "ZenGlow/.gitignore" ".gitignore"

echo "=== Key File Comparison Complete ==="
echo "Report generated: $(date)"