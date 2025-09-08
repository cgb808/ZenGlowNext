#!/bin/bash
# Safety and Backup Script for ZenGlow Project
# Pre-cleanup safety verification and backup creation

echo "=== ZenGlow Safety & Backup Tool ==="
echo "Safety Check Date: $(date)"
echo ""

# Function to create backup
create_backup() {
    BACKUP_DIR="/tmp/zenglow-backup-$(date +%Y%m%d-%H%M%S)"
    echo "Creating safety backup at: $BACKUP_DIR"
    
    # Create backup directory
    mkdir -p "$BACKUP_DIR"
    
    # Copy critical files and directories
    echo "Backing up critical files..."
    cp package.json "$BACKUP_DIR/" 2>/dev/null || echo "❌ package.json not found"
    cp package-lock.json "$BACKUP_DIR/" 2>/dev/null || echo "❌ package-lock.json not found"
    cp -r components "$BACKUP_DIR/" 2>/dev/null || echo "❌ components directory not found"
    cp -r assets "$BACKUP_DIR/" 2>/dev/null || echo "❌ assets directory not found"
    cp -r src "$BACKUP_DIR/" 2>/dev/null || echo "❌ src directory not found"
    cp -r app "$BACKUP_DIR/" 2>/dev/null || echo "❌ app directory not found"
    
    # Copy configuration files
    echo "Backing up configuration files..."
    cp *.json "$BACKUP_DIR/" 2>/dev/null
    cp *.js "$BACKUP_DIR/" 2>/dev/null  
    cp *.ts "$BACKUP_DIR/" 2>/dev/null
    cp .env* "$BACKUP_DIR/" 2>/dev/null
    cp .eslint* "$BACKUP_DIR/" 2>/dev/null
    cp .prettier* "$BACKUP_DIR/" 2>/dev/null
    
    echo "✅ Backup created at: $BACKUP_DIR"
    echo "Backup size: $(du -sh "$BACKUP_DIR" | cut -f1)"
    return 0
}

# Function to verify project health
verify_project_health() {
    echo "=== Project Health Verification ==="
    
    # Check if this looks like a valid React Native/Expo project
    if [ -f "package.json" ] && grep -q "expo" package.json; then
        echo "✅ Valid Expo project detected"
    elif [ -f "package.json" ] && grep -q "react-native" package.json; then
        echo "✅ Valid React Native project detected"
    else
        echo "⚠️  Warning: May not be a standard React Native/Expo project"
    fi
    
    # Check for essential files
    echo ""
    echo "Essential files check:"
    [ -f "package.json" ] && echo "✅ package.json" || echo "❌ package.json missing"
    [ -f "App.js" ] || [ -f "App.tsx" ] && echo "✅ App file found" || echo "❌ No App file found"
    [ -d "components" ] && echo "✅ components directory" || echo "⚠️  components directory missing"
    [ -d "assets" ] && echo "✅ assets directory" || echo "⚠️  assets directory missing"
    
    # Check git status
    echo ""
    echo "Git repository status:"
    if git status >/dev/null 2>&1; then
        echo "✅ Valid git repository"
        UNCOMMITTED=$(git status --porcelain | wc -l)
        if [ "$UNCOMMITTED" -gt 0 ]; then
            echo "⚠️  $UNCOMMITTED uncommitted changes detected"
            echo "   Consider committing changes before cleanup"
        else
            echo "✅ No uncommitted changes"
        fi
    else
        echo "❌ Not a git repository or git error"
    fi
    
    # Check for nested ZenGlow directory (this should not exist based on analysis)
    echo ""
    echo "Nested structure check:"
    if [ -d "./ZenGlow" ]; then
        echo "🚨 CRITICAL: Nested ZenGlow directory found!"
        echo "   This contradicts the analysis findings"
        echo "   Manual review required before proceeding"
        return 1
    else
        echo "✅ No nested ZenGlow directory (expected based on analysis)"
    fi
    
    return 0
}

# Function to check for cleanup prerequisites
check_cleanup_prerequisites() {
    echo ""
    echo "=== Cleanup Prerequisites Check ==="
    
    # Check if npm/node is available
    if command -v npm >/dev/null 2>&1; then
        echo "✅ npm available ($(npm --version))"
    else
        echo "❌ npm not found - required for dependency management"
    fi
    
    if command -v node >/dev/null 2>&1; then
        echo "✅ node available ($(node --version))"
    else
        echo "❌ node not found - required for project"
    fi
    
    # Check available disk space
    AVAILABLE_SPACE=$(df . | awk 'NR==2 {print $4}')
    if [ "$AVAILABLE_SPACE" -gt 1000000 ]; then  # More than 1GB
        echo "✅ Sufficient disk space available"
    else
        echo "⚠️  Low disk space - consider cleaning up before proceeding"
    fi
    
    # Check if we can write to the directory
    if [ -w "." ]; then
        echo "✅ Write permissions available"
    else
        echo "❌ No write permissions - cleanup will fail"
        return 1
    fi
    
    return 0
}

# Function to generate rollback script
generate_rollback_script() {
    local backup_dir="$1"
    local rollback_script="rollback-$(date +%Y%m%d-%H%M%S).sh"
    
    cat > "$rollback_script" << EOF
#!/bin/bash
# Auto-generated rollback script
# Created: $(date)
# Backup location: $backup_dir

echo "Rolling back ZenGlow project changes..."
echo "WARNING: This will restore files from backup and may overwrite current changes"
read -p "Are you sure you want to proceed? (y/N): " -n 1 -r
echo
if [[ ! \$REPLY =~ ^[Yy]$ ]]; then
    echo "Rollback cancelled"
    exit 1
fi

if [ ! -d "$backup_dir" ]; then
    echo "❌ Backup directory not found: $backup_dir"
    exit 1
fi

echo "Restoring files from backup..."
cp -r "$backup_dir"/* . 2>/dev/null || echo "Some files may not have been restored"

echo "✅ Rollback complete"
echo "You may need to run 'npm install' to restore dependencies"
EOF

    chmod +x "$rollback_script"
    echo "✅ Rollback script created: $rollback_script"
}

# Main execution
echo "Starting safety verification..."

# Run project health check
if ! verify_project_health; then
    echo ""
    echo "🚨 SAFETY CHECK FAILED"
    echo "Please resolve issues before proceeding with cleanup"
    exit 1
fi

# Check prerequisites
if ! check_cleanup_prerequisites; then
    echo ""
    echo "🚨 PREREQUISITES CHECK FAILED" 
    echo "Please resolve issues before proceeding with cleanup"
    exit 1
fi

# Offer to create backup
echo ""
read -p "Create safety backup before cleanup? (Y/n): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Nn]$ ]]; then
    if create_backup; then
        BACKUP_CREATED=$(find /tmp -maxdepth 1 -name "zenglow-backup-*" -type d | sort | tail -1)
        generate_rollback_script "$BACKUP_CREATED"
    fi
fi

echo ""
echo "=== Safety Verification Complete ==="
echo "✅ Project appears safe for cleanup operations"
echo "📋 Recommended next steps:"
echo "   1. Resolve any unmet dependencies with 'npm install'"
echo "   2. Run project tests if available"
echo "   3. Proceed with cleanup operations"
echo ""
echo "Safety check completed: $(date)"