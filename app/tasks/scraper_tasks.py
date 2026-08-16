"""Celery tasks for job scraping."""

from celery import shared_task
from datetime import datetime, timedelta
from typing import List, Dict, Any
import asyncio

from app.core.celery import celery_app
from app.core.database import get_db_context
from app.models.job import Job, Company, JobSource, JobStatus
from app.services.scrapers import search_all_sources, get_scraper, JobSource as ScraperSource


@shared_task(bind=True, max_retries=3)
def scrape_linkedin(self):
    """Scrape LinkedIn jobs."""
    return asyncio.run(_scrape_source(ScraperSource.LINKEDIN, ["software engineer", "backend engineer", "full stack engineer", "python developer", "devops engineer", "machine learning engineer"]))


@shared_task(bind=True, max_retries=3)
def scrape_indeed(self):
    """Scrape Indeed jobs."""
    return asyncio.run(_scrape_source(ScraperSource.INDEED, ["software engineer", "backend engineer", "python developer", "remote developer"]))


@shared_task(bind=True, max_retries=3)
def scrape_remoteok(self):
    """Scrape RemoteOK jobs."""
    return asyncio.run(_scrape_source(ScraperSource.REMOTEOK, ["software engineer", "backend", "python", "devops", "machine learning"]))


@shared_task(bind=True, max_retries=3)
def scrape_weworkremotely(self):
    """Scrape WeWorkRemotely jobs."""
    return asyncio.run(_scrape_source(ScraperSource.WEWORKREMOTELY, ["software engineer", "backend", "python", "devops", "full stack"]))


@shared_task(bind=True, max_retries=3)
def scrape_yc_jobs(self):
    """Scrape Y Combinator jobs."""
    return asyncio.run(_scrape_source(ScraperSource.YC_JOBS, ["software engineer", "backend", "python", "devops", "machine learning"]))


async def _scrape_source(source: ScraperSource, queries: List[str]) -> Dict[str, Any]:
    """Scrape jobs from a single source."""
    from app.services.scrapers import get_scraper

    total_found = 0
    total_saved = 0
    errors = []

    async with get_db_context() as db:
        scraper = await get_scraper(source)

        for query in queries:
            try:
                jobs = await scraper.search_jobs(query, "Remote")
                total_found += len(jobs)

                for job_data in jobs:
                    saved = await _save_job(db, job_data)
                    if saved:
                        total_saved += 1

            except Exception as e:
                errors.append(f"{query}: {str(e)}")

            # Rate limit between queries
            await asyncio.sleep(5)

        await db.commit()

    # Close scraper if it has browser
    if hasattr(scraper, 'close'):
        await scraper.close()

    return {
        "source": source.value,
        "queries": len(queries),
        "jobs_found": total_found,
        "jobs_saved": total_saved,
        "errors": errors,
        "timestamp": datetime.utcnow().isoformat(),
    }


async def _save_job(db, job_data: Dict[str, Any]) -> bool:
    """Save or update job in database."""
    from sqlalchemy import select

    source = job_data["source"]
    source_id = job_data["source_id"]

    # Check if exists
    existing = await db.execute(
        select(Job).where(
            Job.source == source,
            Job.source_id == source_id,
        )
    )
    job = existing.scalar_one_or_none()

    # Get or create company
    company = None
    if job_data.get("company_name"):
        company_result = await db.execute(
            select(Company).where(Company.name == job_data["company_name"])
        )
        company = company_result.scalar_one_or_none()

        if not company:
            company = Company(
                name=job_data["company_name"],
                domain=_extract_domain(job_data.get("source_url", "")),
                description=job_data.get("company_description"),
                website=job_data.get("company_website"),
                linkedin_url=job_data.get("company_linkedin"),
            )
            db.add(company)
            await db.flush()

    if job:
        # Update existing
        job.title = job_data.get("title", job.title)
        job.description = job_data.get("description", job.description)
        job.requirements = job_data.get("requirements", job.requirements)
        job.location = job_data.get("location", job.location)
        job.is_remote = job_data.get("is_remote", job.is_remote)
        job.salary_min = job_data.get("salary_min", job.salary_min)
        job.salary_max = job_data.get("salary_max", job.salary_max)
        job.salary_currency = job_data.get("salary_currency", job.salary_currency)
        job.salary_period = job_data.get("salary_period", job.salary_period)
        job.required_skills = job_data.get("required_skills", job.required_skills)
        job.preferred_skills = job_data.get("preferred_skills", job.preferred_skills)
        job.tech_stack = job_data.get("tech_stack", job.tech_stack)
        job.experience_level = job_data.get("experience_level", job.experience_level)
        job.job_type = job_data.get("job_type", job.job_type)
        job.visa_sponsorship = job_data.get("visa_sponsorship", job.visa_sponsorship)
        job.relocation_assistance = job_data.get("relocation_assistance", job.relocation_assistance)
        job.posted_at = job_data.get("posted_at", job.posted_at)
        job.last_seen_at = datetime.utcnow()
        job.status = JobStatus.ACTIVE
        job.raw_data = job_data.get("raw_data", job.raw_data)
        job.company_id = company.id if company else job.company_id
        return False  # Updated, not new
    else:
        # Create new
        job = Job(
            source=source,
            source_id=source_id,
            source_url=job_data.get("source_url", ""),
            company_id=company.id if company else None,
            company_name=job_data.get("company_name", ""),
            title=job_data.get("title", ""),
            description=job_data.get("description"),
            requirements=job_data.get("requirements"),
            location=job_data.get("location"),
            is_remote=job_data.get("is_remote", True),
            remote_regions=job_data.get("remote_regions"),
            salary_min=job_data.get("salary_min"),
            salary_max=job_data.get("salary_max"),
            salary_currency=job_data.get("salary_currency", "USD"),
            salary_period=job_data.get("salary_period", "yearly"),
            required_skills=job_data.get("required_skills", []),
            preferred_skills=job_data.get("preferred_skills", []),
            tech_stack=job_data.get("tech_stack", []),
            experience_level=job_data.get("experience_level"),
            job_type=job_data.get("job_type"),
            visa_sponsorship=job_data.get("visa_sponsorship", False),
            relocation_assistance=job_data.get("relocation_assistance", False),
            posted_at=job_data.get("posted_at"),
            status=JobStatus.ACTIVE,
            raw_data=job_data.get("raw_data", {}),
        )
        db.add(job)
        return True  # New job


def _extract_domain(url: str) -> str:
    """Extract domain from URL."""
    from urllib.parse import urlparse
    try:
        parsed = urlparse(url)
        return parsed.netloc.replace("www.", "")
    except Exception:
        return ""


@shared_task(bind=True, max_retries=3)
def scrape_all_sources(self):
    """Scrape all sources - master task."""
    results = {}
    sources = [
        (scrape_remoteok, "remoteok"),
        (scrape_weworkremotely, "weworkremotely"),
        (scrape_yc_jobs, "yc_jobs"),
    ]

    for task_func, name in sources:
        try:
            result = task_func.delay()
            results[name] = {"task_id": result.id, "status": "queued"}
        except Exception as e:
            results[name] = {"error": str(e)}

    return results


@shared_task(bind=True, max_retries=3)
def enrich_job_details(self, job_ids: List[int]):
    """Enrich job details by fetching full descriptions."""
    return asyncio.run(_enrich_job_details(job_ids))


async def _enrich_job_details(job_ids: List[int]) -> Dict[str, Any]:
    """Fetch full job details for jobs missing descriptions."""
    from sqlalchemy import select

    updated = 0
    errors = []

    async with get_db_context() as db:
        jobs = await db.execute(
            select(Job).where(Job.id.in_(job_ids))
        )
        jobs = jobs.scalars().all()

        for job in jobs:
            try:
                scraper = await get_scraper(job.source)
                if hasattr(scraper, 'parse_job_detail'):
                    details = await scraper.parse_job_detail(job.source_url)
                    if details:
                        job.description = details.get("description", job.description)
                        job.requirements = details.get("requirements", job.requirements)
                        updated += 1

                await asyncio.sleep(2)  # Rate limit

            except Exception as e:
                errors.append(f"Job {job.id}: {str(e)}")

        await db.commit()

    return {"updated": updated, "errors": errors}