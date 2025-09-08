#!/bin/bash

# This script scans the project for redundant and unused files based on
# the guidelines in ZenGlow/Docs/housekeeping-tasks.md. It can either
# generate a list of files for review or delete them directly if run
# with the --delete flag.

set -e

DELETE_MODE=false
if [ "$1" == "--delete" ]; then
    DELETE_MODE=true
fi

PROJECT_ROOT=$(git rev-parse --show-toplevel)
cd "$PROJECT_ROOT"

echo "🔍 Scanning for redundant and unused files in: $PROJECT_ROOT"
echo "==========================================================="

# Create a file to store the results
OUTPUT_FILE="cleanup_candidates.txt"
> "$OUTPUT_FILE" # Clear the file if it exists

if [ "$DELETE_MODE" = true ]; then
    echo "Finding and preparing to delete files..."
else
    echo "Finding candidates for deletion. Results will be saved to $OUTPUT_FILE"
fi

# 1. Find orphaned/redundant sidecar files
echo "🔎 Searching for redundant .sidecar.yaml files..."
find . -type f -name "*.sidecar.yaml.sidecar.yaml*" -print >> "$OUTPUT_FILE"

# 2. Find IDE/Tooling artifacts (.idea directory)
echo "🔎 Searching for JetBrains .idea directory..."
if [ -d ".idea" ]; then
    echo ".idea/" >> "$OUTPUT_FILE"
fi

# 3. Find other common clutter that might have been committed by mistake
echo "🔎 Searching for other common clutter (e.g., .DS_Store, .orig files)..."
find . -type f -name ".DS_Store" -print >> "$OUTPUT_FILE"
find . -type f -name "*.orig.*" -print >> "$OUTPUT_FILE"

# 4. Find temporary backup directories
echo "🔎 Searching for temporary backup directories (e.g., *-backup-YYYYMMDD_HHMMSS)..."
find . -type d -name "*-backup-????????_??????*" -print >> "$OUTPUT_FILE"

# Count all candidates found so far
CANDIDATE_COUNT=$(wc -l < "$OUTPUT_FILE" | tr -d '[:space:]')

if [ "$CANDIDATE_COUNT" -gt 0 ]; then
    if [ "$DELETE_MODE" = true ]; then
        echo ""
        echo "Found $CANDIDATE_COUNT items to delete. Deleting now..."
        # Use sudo for deletion to handle files owned by root (e.g., from Docker)
        cat "$OUTPUT_FILE" | xargs -I {} sudo rm -rf "{}"
        echo "✅ Deletion complete."
        rm "$OUTPUT_FILE"
    else
        echo ""
        echo "✅ Scan complete. Found $CANDIDATE_COUNT potential files/directories to delete."
        echo "Please review the list in '$OUTPUT_FILE' carefully before deleting anything."
        echo ""
        echo "To review the list, run: cat $OUTPUT_FILE"
        echo "To delete all listed files, run this script again with the --delete flag:"
        echo "   sudo bash scripts/find-unused-files.sh --delete"
    fi
else
    echo "✅ Scan complete. No obvious redundant or unused files were found based on the current rules."
    rm "$OUTPUT_FILE"
fi

echo "==========================================================="
