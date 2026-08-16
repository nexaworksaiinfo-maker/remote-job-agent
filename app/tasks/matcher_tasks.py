"""Celery tasks for job matching."""

from celery import shared_task
from datetime import datetime, timedelta
from typing import List, Dict, Any
import asyncio

from app.core.celery import celery_app
from app.core.database import get_db_context
from app.models.profile import Profile
from app.models.job import Job, JobStatus
from app.services.matcher import JobMatcherService


@shared_task(bind=True, max_retries=3)
def match_all_profiles(self):
    """Match all active profiles against recent jobs."""
    return asyncio.run(_match_all_profiles())


async def _match_all_profiles() -> Dict[str, Any]:
    """Match all active profiles."""
    matched_total = 0
    profiles_processed = 0
    errors = []

    async with get_db_context() as db:
        # Get active profiles with auto_apply enabled
        profiles = await db.execute(
            Profile.__table__.select().where(
                Profile.is_active == True,
                Profile.auto_apply == True,
            )
        )
        profiles = profiles.scalars().all()

        matcher = JobMatcherService(db)

        for profile in profiles:
            try:
                matches = await matcher.find_matches_for_profile(profile.id)
                if matches:
                    queued = await matcher.queue_applications(profile.id, matches)
                    matched_total += queued
                profiles_processed += 1
            except Exception as e:
                errors.append(f"Profile {profile.id}: {str(e)}")

        await db.commit()

    return {
        "profiles_processed": profiles_processed,
        "applications_queued": matched_total,
        "errors": errors,
        "timestamp": datetime.utcnow().isoformat(),
    }


@shared_task(bind=True, max_retries=3)
def match_profile(self, profile_id: int, min_score: float = None, limit: int = 50):
    """Match a specific profile against jobs."""
    return asyncio.run(_match_profile(profile_id, min_score, limit))


async def _match_profile(profile_id: int, min_score: float = None, limit: int = 50) -> Dict[str, Any]:
    """Match single profile."""
    async with get_db_context() as db:
        profile = await db.get(Profile, profile_id)
        if not profile:
            return {"error": "Profile not found"}

        matcher = JobMatcherService(db)
        matches = await matcher.find_matches_for_profile(
            profile_id, min_score=min_score, limit=limit
        )

        return {
            "profile_id": profile_id,
            "matches_found": len(matches),
            "matches": [
                {
                    "job_id": m.job_id,
                    "score": m.score,
                    "reason": m.reason,
                    "matched_skills": m.matched_skills,
                    "missing_skills": m.missing_skills,
                }
                for m in matches
            ],
        }


@shared_task(bind=True, max_retries=3)
def generate_embeddings(self):
    """Generate embeddings for jobs and profiles missing them."""
    return asyncio.run(_generate_embeddings())


async def _generate_embeddings() -> Dict[str, Any]:
    """Generate embeddings for semantic search."""
    from app.services.matcher import JobMatcher

    matcher = JobMatcher()
    updated_jobs = 0
    updated_profiles = 0
    errors = []

    async with get_db_context() as db:
        # Jobs without embeddings
        jobs = await db.execute(
            Job.__table__.select().where(
                Job.embedding.is_(None),
                Job.status == JobStatus.ACTIVE,
            ).limit(100)
        )
        jobs = jobs.scalars().all()

        for job in jobs:
            try:
                text = matcher._build_job_text(job)
                embedding = await matcher.get_embedding(text)
                job.embedding = embedding
                updated_jobs += 1
            except Exception as e:
                errors.append(f"Job {job.id}: {str(e)}")

        # Profiles without embeddings
        profiles = await db.execute(
            Profile.__table__.select().where(
                Profile.embedding.is_(None),
                Profile.is_active == True,
            ).limit(50)
        )
        profiles = profiles.scalars().all()

        for profile in profiles:
            try:
                text = matcher._build_profile_text(profile)
                embedding = await matcher.get_embedding(text)
                profile.embedding = embedding
                updated_profiles += 1
            except Exception as e:
                errors.append(f"Profile {profile.id}: {str(e)}")

        await db.commit()

    return {
        "jobs_updated": updated_jobs,
        "profiles_updated": updated_profiles,
        "errors": errors,
    }


@shared_task(bind=True, max_retries=3)
def recalculate_match_scores(self, profile_id: int = None):
    """Recalculate match scores for existing applications."""
    return asyncio.run(_recalculate_match_scores(profile_id))


async def _recalculate_match_scores(profile_id: int = None) -> Dict[str, Any]:
    """Recalculate match scores for applications."""
    from sqlalchemy import select
    from app.models.job import Application, ApplicationStatus

    updated = 0

    async with get_db_context() as db:
        query = select(Application).where(
            Application.status.in_([
                ApplicationStatus.QUEUED,
                ApplicationStatus.MATCHED,
                ApplicationStatus.DISCOVERED,
            ])
        )
        if profile_id:
            query = query.where(Application.profile_id == profile_id)

        applications = await db.execute(query)
        applications = applications.scalars().all()

        matcher = JobMatcherService(db)

        for app in applications:
            profile = await db.get(Profile, app.profile_id)
            job = await db.get(Job, app.job_id)

            if profile and job:
                matches = await matcher.matcher.match_profile_to_jobs(profile, [job])
                if matches:
                    app.match_score = matches[0].score
                    app.matched_skills = matches[0].matched_skills
                    app.missing_skills = matches[0].missing_skills
                    updated += 1

        await db.commit()

    return {"updated": updated}