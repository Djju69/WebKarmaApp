#!/bin/bash

# Script for pushing changes to the repository
# Usage: ./push.sh "Your commit message" [branch-name]

# Check if commit message is provided
if [ -z "$1" ]; then
    echo "Error: Commit message is required"
    echo "Usage: ./push.sh \"Your commit message\" [branch-name]"
    exit 1
fi

COMMIT_MSG="$1"
BRANCH="${2:-main}"  # Use provided branch or default to 'main'

# Check if there are changes to commit
if [ -z "$(git status --porcelain)" ]; then
    echo "No changes to commit"
    exit 0
fi

echo "Adding all changes..."
git add .

echo "Committing changes with message: $COMMIT_MSG"
git commit -m "$COMMIT_MSG"

echo "Pushing to $BRANCH branch..."
git push origin "$BRANCH"

echo "Push completed successfully!"
