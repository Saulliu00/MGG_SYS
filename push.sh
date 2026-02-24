#!/bin/bash

echo "=========================================="
echo "Pushing Enterprise Hardening Roadmap to GitHub"
echo "=========================================="
echo ""
echo "Repository: https://github.com/Saulliu00/MGG_SYS"
echo "Branch: master"
echo ""
echo "You will be prompted for your GitHub credentials:"
echo "  Username: Saulliu00"
echo "  Password: Use your GitHub Personal Access Token"
echo ""
echo "Don't have a token? Generate one at:"
echo "  https://github.com/settings/tokens"
echo ""
echo "=========================================="
echo ""

cd /home/saul/.openclaw/workspace/MGG_SYS

# Show what will be pushed
echo "Files to be pushed:"
git show --name-only --oneline HEAD
echo ""

# Push to GitHub
git push origin master

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ SUCCESS! Document pushed to GitHub"
    echo ""
    echo "View it at:"
    echo "https://github.com/Saulliu00/MGG_SYS/blob/master/ENTERPRISE_HARDENING_ROADMAP.md"
else
    echo ""
    echo "❌ Push failed. Please check your credentials and try again."
    echo ""
    echo "Troubleshooting:"
    echo "1. Make sure you're using a Personal Access Token (not password)"
    echo "2. Token must have 'repo' scope"
    echo "3. Generate token at: https://github.com/settings/tokens"
fi
