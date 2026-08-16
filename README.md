# Remote Job Agent

A fully automated system for finding, matching, and applying to remote jobs. Runs continuously in the background, scraping job boards, matching against your profiles, and auto-applying with AI-generated cover letters.

## Features

- **Multi-source scraping**: LinkedIn, Indeed, RemoteOK, WeWorkRemotely, Wellfound, YC Jobs, Glassdoor
- **Semantic matching**: Uses embeddings (OpenAI or local) to match jobs to your profile
- **Auto-application**: Playwright-based browser automation for LinkedIn Easy Apply, Indeed, and generic ATS systems
- **Profile management**: Multiple profiles for different roles (Backend, ML, DevOps, etc.)
- **Application tracking**: Full pipeline (Discovered → Matched → Queued → Applied → Screening → Interview → Offer)
- **Notifications**: Telegram, Discord, Email alerts for matches, interviews, offers
- **Interview scheduling**: Cal.com / Google Calendar integration
- **Admin dashboard**: FastAPI + React dashboard for monitoring
- **Scheduled tasks**: Celery Beat for continuous operation

## Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Scrapers      │────▶│    Matcher      │────▶│    Applier      │
│  (Celery)       │     │  (Embeddings)   │     │  (Playwright)   │
└─────────────────┘     └─────────────────┘     └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────────────────────────────────────────────────────┐
│                    PostgreSQL + Redis                            │
│  Jobs │ Companies │ Profiles │ Applications │ Interviews │ Logs  │
└─────────────────────────────────────────────────────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Notifications │     │   Dashboard     │     │   Scheduler     │
│ (Telegram/Email)│     │   (FastAPI)     │     │  (Celery Beat)  │
└─────────────────┘     └─────────────────┘     └─────────────────┘
```

## Quick Start

### Prerequisites
- Docker & Docker Compose
- OpenAI API key
- LinkedIn credentials (for scraping/applying)

### Configuration

```bash
cd /opt/data/remote-job-agent
cp .env.example .env
# Edit .env with your credentials
```

Required environment variables:
```env
OPENAI_API_KEY=sk-...
LINKEDIN_EMAIL=your@email.com
LINKEDIN_PASSWORD=your-password
SECRET_KEY=your-32-char-secret-key
```

Optional (for notifications):
```env
TELEGRAM_BOT_TOKEN=...
TELEGRAM_CHAT_ID=...
SMTP_HOST=smtp.gmail.com
SMTP_USERNAME=...
SMTP_PASSWORD=...
```

### Deploy

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Check health
curl http://localhost:8000/health
```

### Access Points

| Service | URL |
|---------|-----|
| API | http://localhost:8000 |
| API Docs | http://localhost:8000/docs |
| Flower (Celery Monitor) | http://localhost:5555 |
| Health Check | http://localhost:8000/health |

## Usage

### 1. Create Profiles

```bash
# Via API
curl -X POST http://localhost:8000/api/v1/profiles \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Senior Backend Engineer",
    "role": "Backend Engineer",
    "seniority": "Senior",
    "skills": ["Python", "FastAPI", "PostgreSQL", "Redis", "Docker", "AWS", "Kubernetes"],
    "experience_years": 7,
    "salary_min": 150000,
    "salary_max": 250000,
    "locations": ["Remote", "US", "EU"],
    "resume_path": "resumes/backend_senior.pdf",
    "cover_letter_template": "templates/cover_letter_backend.j2",
    "auto_apply": true,
    "min_match_score": 0.7
  }'
```

### 2. Trigger Manual Scrape

```bash
# Scrape all sources
curl -X POST http://localhost:8000/api/v1/tasks/scrape-all \
  -H "Authorization: Bearer YOUR_TOKEN"

# Scrape specific source
curl -X POST http://localhost:8000/api/v1/tasks/scrape \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"source": "linkedin", "queries": ["python developer", "backend engineer"]}'
```

### 3. Trigger Matching

```bash
curl -X POST http://localhost:8000/api/v1/tasks/match \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### 4. Process Application Queue

```bash
curl -X POST http://localhost:8000/api/v1/tasks/process-queue \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### 5. Monitor via Dashboard

Open http://localhost:8000/docs for interactive API documentation.

## Scheduled Tasks (Celery Beat)

| Task | Schedule | Queue |
|------|----------|-------|
| Scrape LinkedIn | Every 2 hours | scrapers |
| Scrape Indeed | Every 2 hours | scrapers |
| Scrape RemoteOK | Every 4 hours | scrapers |
| Scrape WeWorkRemotely | Every 4 hours | scrapers |
| Scrape YC Jobs | Every 6 hours | scrapers |
| Match Jobs | Every hour | matcher |
| Process Applications | Every 30 min (9-18) | applier |
| Send Notifications | Every 15 min | notifications |
| Interview Reminders | Hourly | notifications |
| Cleanup Old Jobs | Daily 3 AM | maintenance |
| Update Company Data | Daily 3:30 AM | maintenance |
| Daily Report | Daily 6 AM | maintenance |
| Backup Database | Daily 2 AM | maintenance |

## Configuration

### Matching Weights

Adjust in `.env`:
```env
SEMANTIC_WEIGHT=0.5      # Embedding similarity
SKILL_WEIGHT=0.3         # Skill overlap
EXPERIENCE_WEIGHT=0.15   # Years of experience
SALARY_WEIGHT=0.05       # Salary alignment
MATCH_THRESHOLD=0.65     # Minimum score to queue
```

### Application Limits

```env
MAX_DAILY_APPLICATIONS=20
MAX_CONCURRENT_APPLICATIONS=3
APPLICATION_TIMEOUT=120
MAX_RETRIES=3
```

### Browser Settings

```env
PLAYWRIGHT_HEADLESS=true
PLAYWRIGHT_SLOW_MO=100
REQUEST_DELAY_MIN=2.0
REQUEST_DELAY_MAX=5.0
ROTATE_USER_AGENTS=true
```

## Project Structure

```
/opt/data/remote-job-agent/
├── app/
│   ├── api/              # FastAPI routes
│   ├── core/             # Config, DB, Celery
│   ├── models/           # SQLAlchemy models
│   ├── schemas/          # Pydantic schemas
│   ├── services/         # Business logic
│   │   ├── scrapers.py   # Job board scrapers
│   │   ├── matcher.py    # Semantic matching
│   │   ├── applier.py    # Auto-application
│   │   └── notification.py
│   ├── tasks/            # Celery tasks
│   └── main.py           # FastAPI app
├── config/               # Profile templates
├── resumes/              # Resume files
├── alembic/              # DB migrations
├── docker-compose.yml
├── Dockerfile
├── pyproject.toml
└── .env.example
```

## Profiles

Create multiple profiles for different target roles:

```yaml
# config/profiles.yaml
profiles:
  - name: "Senior Backend Engineer"
    role: "Backend Engineer"
    seniority: "Senior"
    skills: ["Python", "FastAPI", "PostgreSQL", "Redis", "Docker", "AWS", "Kubernetes"]
    experience_years: 7
    salary_min: 150000
    salary_max: 250000
    locations: ["Remote", "US", "EU"]
    visa_sponsorship: false
    resume_path: "resumes/backend_senior.pdf"
    cover_letter_template: "templates/cover_letter_backend.j2"

  - name: "ML Engineer"
    role: "Machine Learning Engineer"
    seniority: "Senior"
    skills: ["Python", "PyTorch", "TensorFlow", "MLOps", "Kubernetes", "GCP"]
    experience_years: 5
    salary_min: 160000
    salary_max: 280000
    locations: ["Remote", "US"]
    resume_path: "resumes/ml_engineer.pdf"
```

## Anti-Detection

The system includes several anti-detection measures:

- Random user agents from real browser pool
- Human-like mouse movements and typing delays
- Persistent browser context with cookies/storage
- Request rate limiting with random delays
- Proxy rotation support (configure `PROXY_LIST`)
- Stealth JavaScript injection

## Legal & Compliance

⚠️ **Important**: This tool automates job applications. Use responsibly:

- Respect each platform's Terms of Service
- Don't exceed reasonable rate limits
- Only apply to jobs you're genuinely qualified for
- Review applications before submission when possible
- Some companies prohibit automated applications
- LinkedIn's ToS restricts scraping - use at your own risk

## Monitoring

### Flower Dashboard
http://localhost:5555 - Monitor Celery tasks, workers, queues

### Health Checks
```bash
# API health
curl http://localhost:8000/health

# Database
docker-compose exec api python -c "from app.core.database import engine; print('DB OK')"

# Redis
docker-compose exec redis redis-cli ping
```

### Logs
```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f api
docker-compose logs -f worker-scrapers
docker-compose logs -f worker-applier
```

## Deployment

### Railway/Render/Fly.io

1. Connect repository
2. Set environment variables
3. Deploy - services auto-scale

### VPS with Docker

```bash
# On server
git clone <repo>
cd remote-job-agent
cp .env.example .env
# Edit .env
docker-compose up -d

# Setup nginx reverse proxy (optional)
# Configure SSL with Let's Encrypt
```

## Troubleshooting

### LinkedIn Login Fails
- Check credentials in `.env`
- LinkedIn may require 2FA - disable or use app password
- Try manual login once to establish session

### Applications Stuck in QUEUED
- Check worker-applier logs: `docker-compose logs worker-applier`
- Verify browser automation works: `docker-compose exec api playwright install`
- Check daily limit not exceeded

### No Jobs Found
- Verify scrapers run: check Flower dashboard
- Check job source APIs haven't changed
- Adjust search queries in tasks

### High Memory Usage
- Reduce `CELERY_WORKER_PREFETCH_MULTIPLIER`
- Limit concurrent browser instances
- Use `PLAYWRIGHT_HEADLESS=true`

## License

MIT License - See LICENSE file

## Support

- Issues: GitHub Issues
- Docs: `/docs` endpoint
- Monitoring: Flower at `:5555`