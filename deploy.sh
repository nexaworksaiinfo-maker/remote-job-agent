#!/usr/bin/env bash
# deploy.sh — One-command Remote Job Agent deployment from local machine
# Usage: GITHUB_PAT=your_token ./deploy.sh

set -euo pipefail

REPO="nexaworksaiinfo-maker/remote-job-agent"
BRANCH="master"
RENDER_DASHBOARD="https://dashboard.render.com/blueprints/new"

echo "🚀 Remote Job Agent — Full Deployment"
echo "======================================"

# Check GitHub PAT
if [[ -z "${GITHUB_PAT:-}" ]]; then
    echo "❌ GITHUB_PAT environment variable not set"
    echo "   Create a PAT at https://github.com/settings/tokens (repo scope)"
    echo "   Then run: GITHUB_PAT=your_token ./deploy.sh"
    exit 1
fi

# Check git
if ! command -v git &> /dev/null; then
    echo "❌ git not installed"
    exit 1
fi

# Check docker
if ! command -v docker &> /dev/null; then
    echo "❌ docker not installed"
    exit 1
fi

# Clone or update repo
if [[ -d "remote-job-agent" ]]; then
    echo "📁 Updating existing repo..."
    cd remote-job-agent
    git fetch origin
else
    echo "📁 Cloning repo..."
    git clone "https://${GITHUB_PAT}@github.com/${REPO}.git"
    cd remote-job-agent
fi

# Ensure we're on master
git checkout "${BRANCH}"
git pull origin "${BRANCH}"

# Copy latest files from this container if needed
# (Assuming you have the files locally or use the container's files)

# Push to GitHub
echo "📤 Pushing to GitHub..."
git push origin "${BRANCH}"

echo ""
echo "✅ Code pushed to GitHub!"
echo ""
echo "🌐 Next: Deploy via Render Blueprint"
echo "   1. Open: ${RENDER_DASHBOARD}"
echo "   2. Connect repo: ${REPO}"
echo "   3. Click 'Apply' — creates 9 services"
echo ""
echo "🔐 After deploy, add SMTP_PASSWORD secret in Render Dashboard:"
echo "   • remote-job-agent-api → Environment → SMTP_PASSWORD = 'stzu bnch rauc ymxf' (Secret)"
echo "   • remote-job-agent-notifications → Environment → SMTP_PASSWORD = 'stzu bnch rauc ymxf' (Secret)"
echo ""
echo "⏳ Wait for Ollama to pull models (5-10 min first deploy)"
echo ""
echo "📊 Monitor:"
echo "   • Flower: https://remote-job-agent-flower.onrender.com"
echo "   • API: https://remote-job-agent-api.onrender.com/docs"
echo "   • Telegram: Bot alerts automatically"
echo ""
echo "🎯 Trigger first cycle (after all services healthy):"
echo "   curl -X POST https://remote-job-agent-api.onrender.com/api/v1/scrape/trigger"
echo "   curl -X POST https://remote-job-agent-api.onrender.com/api/v1/match/trigger"
echo "   curl -X POST https://remote-job-agent-api.onrender.com/api/v1/apply/trigger"
echo ""
echo "✅ Deployment initiated! Check Render dashboard for progress."