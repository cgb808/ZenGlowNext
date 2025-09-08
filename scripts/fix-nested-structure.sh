#!/bin/bash
#
# This script corrects a nested project structure where the entire project
# content is inside a subdirectory (e.g., 'ZenGlow/ZenGlow').
# It safely moves all content from the inner directory to the project root.

set -e # Exit immediately if a command exits with a non-zero status.

INNER_DIR="ZenGlow"

echo "🔍 Checking for nested project structure..."

# 1. Check if the inner directory exists and is not empty
if [ ! -d "$INNER_DIR" ] || [ -z "$(ls -A $INNER_DIR)" ]; then
  echo "✅ Project structure appears correct. No nested '$INNER_DIR' directory found."
  exit 0
fi

echo "⚠️ Nested '$INNER_DIR' directory found. Attempting to fix the structure..."

# 2. Use rsync to merge the inner directory into the root.
# 'rsync -a' archives (preserves permissions, etc.) and recurses.
# The trailing slash on "$INNER_DIR/" is crucial - it means "copy the contents of the directory".
echo "   -> Merging contents of '$INNER_DIR/' into the project root..."
rsync -a --remove-source-files "$INNER_DIR/" .

# 3. Clean up the now-empty inner directory
echo "   -> Cleaning up..."
rm -rf "$INNER_DIR"

echo "✅ Project structure has been corrected successfully!"
echo "➡️ Please run 'git status' to review the changes and then commit them."