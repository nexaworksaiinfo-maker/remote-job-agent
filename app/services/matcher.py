"""Job matching service using embeddings and semantic search."""

import asyncio
import json
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass

from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from sqlalchemy import select, and_, or_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db_context
from app.models.job import Job, JobSource, JobStatus
from app.models.profile import Profile
from app.services.llm_client import llm_client


@dataclass
class MatchResult:
    """Job match result."""
    job_id: int
    score: float
    matched_skills: List[str]
    missing_skills: List[str]
    experience_match: bool
    salary_match: bool
    location_match: bool
    reason: str


class JobMatcher:
    """Semantic job matching using embeddings."""

    def __init__(self):
        self.embedding_model = None
        self.openai_client = None
        self._init_models()

    def _init_models(self):
        """Initialize embedding models."""
        # Use sentence-transformers for local embeddings (faster, free) - PRIMARY
        try:
            if settings.USE_OLLAMA_FOR_EMBEDDINGS:
                # Use Ollama for embeddings
                import ollama
                self.ollama_client = ollama.Client(host=settings.OLLAMA_BASE_URL.replace('/v1', ''))
                self.ollama_embedding_model = settings.OLLAMA_EMBEDDING_MODEL
            else:
                # Use sentence-transformers locally
                self.embedding_model = SentenceTransformer("all-MiniLM-L6-v2")
        except Exception as e:
            print(f"Warning: Could not initialize local embeddings: {e}")
            self.embedding_model = None
            self.ollama_client = None
        
        # OpenAI fallback (optional)
        try:
            if settings.OPENAI_API_KEY:
                import openai
                self.openai_client = openai.AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        except Exception as e:
            print(f"Warning: Could not initialize OpenAI fallback: {e}")
            self.openai_client = None

    async def get_embedding(self, text: str) -> List[float]:
        """Get embedding for text."""
        # Try Ollama first (if enabled)
        if settings.USE_OLLAMA_FOR_EMBEDDINGS and self.ollama_client:
            try:
                response = self.ollama_client.embeddings(
                    model=self.ollama_embedding_model,
                    prompt=text[:8000]
                )
                return response["embedding"]
            except Exception as e:
                print(f"Ollama embedding failed: {e}")
        
        # Try local sentence-transformers
        if self.embedding_model:
            embedding = self.embedding_model.encode(text)
            return embedding.tolist()
        
        # Fallback to OpenAI
        elif self.openai_client:
            response = await self.openai_client.embeddings.create(
                model=settings.OPENAI_EMBEDDING_MODEL,
                input=text[:8000],
            )
            return response.data[0].embedding
        
        # Return zero vector as fallback
        return [0.0] * 1536

    async def get_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """Get embeddings for multiple texts."""
        # Try Ollama first (if enabled)
        if settings.USE_OLLAMA_FOR_EMBEDDINGS and self.ollama_client:
            try:
                results = []
                for text in texts:
                    response = self.ollama_client.embeddings(
                        model=self.ollama_embedding_model,
                        prompt=text[:8000]
                    )
                    results.append(response["embedding"])
                return results
            except Exception as e:
                print(f"Ollama batch embedding failed: {e}")
        
        # Try local sentence-transformers
        if self.embedding_model:
            embeddings = self.embedding_model.encode(texts, batch_size=32, show_progress_bar=False)
            return embeddings.tolist()
        
        # Fallback to OpenAI
        elif self.openai_client:
            results = []
            for i in range(0, len(texts), 100):
                batch = texts[i:i+100]
                response = await self.openai_client.embeddings.create(
                    model=settings.OPENAI_EMBEDDING_MODEL,
                    input=batch,
                )
                results.extend([d.embedding for d in response.data])
            return results
        
        return [[0.0] * 1536] * len(texts)

    def _build_job_text(self, job: Job) -> str:
        """Build searchable text from job."""
        parts = [
            job.title,
            job.company_name,
            job.description or "",
            job.requirements or "",
            " ".join(job.required_skills or []),
            " ".join(job.preferred_skills or []),
            " ".join(job.tech_stack or []),
            job.location or "",
        ]
        return " ".join(filter(None, parts))

    def _build_profile_text(self, profile: Profile) -> str:
        """Build searchable text from profile."""
        parts = [
            profile.headline or "",
            profile.summary or "",
            profile.current_title or "",
            " ".join(profile.skills or []),
            " ".join(profile.preferred_roles or []),
            profile.location or "",
        ]
        return " ".join(filter(None, parts))

    async def calculate_match_score(
        self,
        profile: Profile,
        job: Job,
        profile_embedding: List[float] = None,
        job_embedding: List[float] = None,
    ) -> MatchResult:
        """Calculate match score between profile and job."""

        # Get embeddings if not provided
        if profile_embedding is None:
            profile_text = self._build_profile_text(profile)
            profile_embedding = await self.get_embedding(profile_text)

        if job_embedding is None:
            job_text = self._build_job_text(job)
            job_embedding = await self.get_embedding(job_text)

        # Semantic similarity (cosine similarity)
        profile_vec = np.array(profile_embedding).reshape(1, -1)
        job_vec = np.array(job_embedding).reshape(1, -1)
        semantic_score = float(cosine_similarity(profile_vec, job_vec)[0][0])

        # Skill matching
        profile_skills = set(s.lower() for s in (profile.skills or []))
        job_required_skills = set(s.lower() for s in (job.required_skills or []))
        job_preferred_skills = set(s.lower() for s in (job.preferred_skills or []))

        matched_required = profile_skills & job_required_skills
        matched_preferred = profile_skills & job_preferred_skills
        missing_required = job_required_skills - profile_skills

        skill_score = 0.0
        if job_required_skills:
            skill_score += len(matched_required) / len(job_required_skills) * 0.7
        if job_preferred_skills:
            skill_score += len(matched_preferred) / len(job_preferred_skills) * 0.3

        # Experience matching
        profile_years = profile.years_experience or 0
        job_exp_map = {
            "entry": 0, "junior": 1, "mid": 3, "senior": 5,
            "lead": 7, "principal": 10, "director": 12, "vp": 15, "c_level": 15
        }
        job_exp_required = job_exp_map.get(job.experience_level.value, 3)
        experience_match = profile_years >= job_exp_required
        exp_score = 1.0 if experience_match else max(0.3, profile_years / job_exp_required)

        # Salary matching
        salary_match = True
        salary_score = 1.0
        if profile.salary_min and job.salary_max:
            if job.salary_max < profile.salary_min:
                salary_match = False
                salary_score = 0.5
        elif profile.salary_max and job.salary_min:
            if job.salary_min > profile.salary_max * 1.5:
                salary_score = 0.7

        # Location matching
        location_match = True
        loc_score = 1.0
        if profile.location and job.location:
            profile_loc = profile.location.lower()
            job_loc = job.location.lower()
            if profile.willingness_to_relocate:
                loc_score = 1.0
            elif job.is_remote:
                loc_score = 1.0
            elif any(loc in job_loc for loc in profile_loc.split(",")):
                loc_score = 1.0
            elif any(loc in profile_loc for loc in job_loc.split(",")):
                loc_score = 0.8
            else:
                loc_score = 0.5
                location_match = False

        # Visa sponsorship
        visa_score = 1.0
        if profile.visa_status == "need_sponsorship" and not job.visa_sponsorship:
            visa_score = 0.3

        # Weighted final score
        weights = {
            "semantic": settings.SEMANTIC_WEIGHT,
            "skill": settings.SKILL_WEIGHT,
            "experience": settings.EXPERIENCE_WEIGHT,
            "salary": settings.SALARY_WEIGHT,
        }

        # Normalize weights
        total_weight = sum(weights.values())
        weights = {k: v/total_weight for k, v in weights.items()}

        final_score = (
            semantic_score * weights["semantic"] +
            skill_score * weights["skill"] +
            exp_score * weights["experience"] +
            salary_score * weights["salary"]
        ) * visa_score * loc_score

        # Build reason
        reasons = []
        if semantic_score > 0.8:
            reasons.append("Strong semantic match")
        if len(matched_required) > 0:
            reasons.append(f"Matched {len(matched_required)} required skills")
        if missing_required:
            reasons.append(f"Missing: {', '.join(list(missing_required)[:3])}")
        if not experience_match:
            reasons.append(f"Experience gap: have {profile_years}yr, need {job_exp_required}yr")
        if not salary_match:
            reasons.append("Salary below expectations")
        if not location_match:
            reasons.append("Location mismatch")

        return MatchResult(
            job_id=job.id,
            score=min(1.0, max(0.0, final_score)),
            matched_skills=list(matched_required) + list(matched_preferred),
            missing_skills=list(missing_required),
            experience_match=experience_match,
            salary_match=salary_match,
            location_match=location_match,
            reason="; ".join(reasons) if reasons else "Good match",
        )

    async def match_profile_to_jobs(
        self,
        profile: Profile,
        jobs: List[Job],
        min_score: float = None,
        limit: int = 50,
    ) -> List[MatchResult]:
        """Match a profile against multiple jobs."""
        min_score = min_score or settings.MATCH_THRESHOLD

        # Build profile embedding once
        profile_text = self._build_profile_text(profile)
        profile_embedding = await self.get_embedding(profile_text)

        # Build job texts
        job_texts = [self._build_job_text(job) for job in jobs]

        # Get job embeddings in batch
        job_embeddings = await self.get_embeddings_batch(job_texts)

        # Calculate matches
        results = []
        for job, job_emb in zip(jobs, job_embeddings):
            match = await self.calculate_match_score(
                profile, job, profile_embedding, job_emb
            )
            if match.score >= min_score:
                results.append(match)

        # Sort by score descending
        results.sort(key=lambda x: x.score, reverse=True)
        return results[:limit]

    async def match_all_profiles(
        self,
        profiles: List[Profile],
        jobs: List[Job],
        min_score: float = None,
    ) -> Dict[int, List[MatchResult]]:
        """Match all profiles to all jobs."""
        results = {}
        for profile in profiles:
            matches = await self.match_profile_to_jobs(profile, jobs, min_score)
            if matches:
                results[profile.id] = matches
        return results


class JobMatcherService:
    """High-level job matching service with database integration."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.matcher = JobMatcher()

    async def find_matches_for_profile(
        self,
        profile_id: int,
        min_score: float = None,
        limit: int = 50,
        days_back: int = 7,
    ) -> List[MatchResult]:
        """Find job matches for a profile."""
        # Get profile
        profile = await self.db.get(Profile, profile_id)
        if not profile:
            return []

        # Get recent active jobs
        cutoff = datetime.utcnow() - timedelta(days=days_back)
        query = select(Job).where(
            and_(
                Job.status == JobStatus.ACTIVE,
                Job.posted_at >= cutoff,
                Job.is_remote == True,  # Remote-first
            )
        ).order_by(Job.posted_at.desc()).limit(500)

        result = await self.db.execute(query)
        jobs = result.scalars().all()

        # Filter by profile preferences
        filtered_jobs = self._filter_jobs_by_preferences(profile, jobs)

        # Match
        return await self.matcher.match_profile_to_jobs(
            profile, filtered_jobs, min_score, limit
        )

    def _filter_jobs_by_preferences(self, profile: Profile, jobs: List[Job]) -> List[Job]:
        """Pre-filter jobs by hard preferences."""
        filtered = []
        for job in jobs:
            # Skip blacklisted companies
            if profile.blocked_companies and job.company_name in profile.blocked_companies:
                continue

            # Skip if salary too low
            if profile.salary_min and job.salary_max and job.salary_max < profile.salary_min:
                continue

            # Skip if visa needed but not offered
            if profile.visa_status == "need_sponsorship" and not job.visa_sponsorship:
                continue

            # Skip if experience level too high
            exp_order = ["entry", "junior", "mid", "senior", "lead", "principal", "director", "vp", "c_level"]
            profile_idx = exp_order.index(profile.target_level.value) if profile.target_level else 2
            job_idx = exp_order.index(job.experience_level.value)
            if job_idx > profile_idx + 1:  # Allow 1 level up
                continue

            # Location
            if not job.is_remote and profile.location:
                if not any(loc in job.location.lower() for loc in profile.location.lower().split(",")):
                    if not profile.willingness_to_relocate:
                        continue

            filtered.append(job)

        return filtered

    async def queue_applications(
        self,
        profile_id: int,
        matches: List[MatchResult],
        max_applications: int = None,
    ) -> int:
        """Queue matched jobs for application."""
        max_applications = max_applications or settings.MAX_DAILY_APPLICATIONS

        # Check daily limit
        from app.models.job import Application, ApplicationStatus
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        today_count = await self.db.scalar(
            select(func.count(Application.id)).where(
                and_(
                    Application.profile_id == profile_id,
                    Application.status.in_([ApplicationStatus.APPLIED, ApplicationStatus.QUEUED]),
                    Application.applied_at >= today_start,
                )
            )
        )

        remaining = max_applications - (today_count or 0)
        if remaining <= 0:
            return 0

        # Queue top matches
        queued = 0
        for match in matches[:remaining]:
            # Check if already applied
            existing = await self.db.scalar(
                select(Application).where(
                    and_(
                        Application.profile_id == profile_id,
                        Application.job_id == match.job_id,
                    )
                )
            )
            if existing:
                continue

            # Create application record
            application = Application(
                profile_id=profile_id,
                job_id=match.job_id,
                status=ApplicationStatus.QUEUED,
                match_score=match.score,
                matched_skills=match.matched_skills,
                missing_skills=match.missing_skills,
            )
            self.db.add(application)
            queued += 1

        await self.db.commit()
        return queued

    async def get_match_statistics(self, profile_id: int) -> Dict[str, Any]:
        """Get matching statistics for profile."""
        from app.models.job import Application, ApplicationStatus

        # Total applications
        total = await self.db.scalar(
            select(func.count(Application.id)).where(Application.profile_id == profile_id)
        )

        # By status
        status_counts = {}
        for status in ApplicationStatus:
            count = await self.db.scalar(
                select(func.count(Application.id)).where(
                    and_(
                        Application.profile_id == profile_id,
                        Application.status == status,
                    )
                )
            )
            status_counts[status.value] = count or 0

        # Response rate
        applied = status_counts.get("applied", 0) + status_counts.get("screening", 0) + \
                  status_counts.get("interview", 0) + status_counts.get("offer", 0)
        responded = status_counts.get("screening", 0) + status_counts.get("interview", 0) + \
                    status_counts.get("offer", 0) + status_counts.get("rejected", 0)

        response_rate = responded / applied if applied > 0 else 0

        # Average match score
        avg_score = await self.db.scalar(
            select(func.avg(Application.match_score)).where(
                and_(
                    Application.profile_id == profile_id,
                    Application.match_score.isnot(None),
                )
            )
        )

        return {
            "total_applications": total or 0,
            "by_status": status_counts,
            "response_rate": round(response_rate * 100, 1),
            "average_match_score": round(float(avg_score or 0) * 100, 1),
            "interviews": status_counts.get("interview", 0),
            "offers": status_counts.get("offer", 0),
        }