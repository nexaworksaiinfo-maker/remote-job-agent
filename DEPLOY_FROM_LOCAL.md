# Remote Job Agent — Deploy from Your Local Machine

## Prerequisites
- GitHub Personal Access Token (PAT) with `repo` scope
- Docker installed locally
- Render account (already have resources created)

## Step 1: Clone & Push to GitHub

```bash
# On your LOCAL machine
git clone https://github.com/nexaworksaiinfo-maker/remote-job-agent.git
cd remote-job-agent

# If repo is empty, copy files from this container
# Option A: Use scp from container (if accessible)
# Option B: Use the deployment package below

# Set up GitHub authentication
git remote set-url origin https://YOUR_GITHUB_PAT@github.com/nexaworksaiinfo-maker/remote-job-agent.git

# Push
git push origin master
```

## Step 2: Deploy via Render Blueprint

1. Go to: **https://dashboard.render.com/blueprints/new**
2. Connect your GitHub repo: `nexaworksaiinfo-maker/remote-job-agent`
3. Render will auto-detect `render.yaml` and show 9 services
4. Click **"Apply"** — this creates all services

## Step 3: Add SMTP_PASSWORD Secret

In Render Dashboard → each service → Environment:
- **remote-job-agent-api** → Add `SMTP_PASSWORD` = `stzu bnch rauc ymxf` (mark as Secret)
- **remote-job-agent-notifications** → Add `SMTP_PASSWORD` = `stzu bnch rauc ymxf` (mark as Secret)

## Step 4: Verify Deployment

Watch logs for:
- PostgreSQL/Redis: "ready to accept connections"
- Ollama: "pulled llama3.1:70b" and "pulled nomic-embed-text" (takes 5-10 min first deploy)
- API: "Uvicorn running on http://0.0.0.0:8000"
- Workers: "celery@worker ready"
- Beat: "celery beat starting"

## Step 5: Trigger First Cycle

```bash
# Wait for all services healthy, then:
curl -X POST https://remote-job-agent-api.onrender.com/api/v1/scrape/trigger
curl -X POST https://remote-job-agent-api.onrender.com/api/v1/match/trigger
curl -X POST https://remote-job-agent-api.onrender.com/api/v1/apply/trigger
```

Or wait for Celery Beat (06:00 UTC daily).

## Step 6: Monitor

- **Flower**: https://remote-job-agent-flower.onrender.com (celery monitoring)
- **API Docs**: https://remote-job-agent-api.onrender.com/docs
- **Telegram**: Bot sends alerts for each stage

---

## Alternative: Use the deploy.sh script locally

```bash
chmod +x deploy.sh
./deploy.sh
```

This script does everything above automatically (requires GitHub PAT as env var `GITHUB_PAT`).