#!/bin/bash
# Fix git pull conflicts by stashing local changes

echo "=== Fixing Git Pull Conflict ==="
echo ""

cd /phonix/backend

# Stash local changes
echo "Stashing local changes..."
git stash

# Pull latest changes
echo ""
echo "Pulling latest changes..."
git pull origin master

# Show stashed changes
echo ""
echo "Local changes have been stashed. To see them:"
echo "  git stash list"
echo ""
echo "To apply stashed changes later:"
echo "  git stash pop"
echo ""

echo "=== Git Conflict Fixed ==="
