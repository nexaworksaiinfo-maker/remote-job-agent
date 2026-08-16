"""Job and Application models."""

import enum
from datetime import datetime
from decimal import Decimal
from typing import List, Optional
from sqlalchemy import String, Text, Integer, DateTime, ForeignKey, Index, Enum, Boolean, Numeric, JSON, ARRAY, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, IDMixin


class JobSource(str, enum.Enum):
    """Job source platforms."""
    LINKEDIN = "linkedin"
    INDEED = "indeed"
    REMOTEOK = "remoteok"
    WEWORKREMOTELY = "weworkremotely"
    WELLFOUND = "wellfound"
    YC_JOBS = "yc_jobs"
    OTTA = "otta"
    GLASSDOOR = "glassdoor"
    BUILTIN = "builtin"
    COMPANY_DIRECT = "company_direct"
    REFERRAL = "referral"
    OTHER = "other"


class JobType(str, enum.Enum):
    """Job employment type."""
    FULL_TIME = "full_time"
    PART_TIME = "part_time"
    CONTRACT = "contract"
    FREELANCE = "freelance"
    INTERNSHIP = "internship"
    TEMPORARY = "temporary"


class ExperienceLevel(str, enum.Enum):
    """Experience level required."""
    ENTRY = "entry"
    JUNIOR = "junior"
    MID = "mid"
    SENIOR = "senior"
    LEAD = "lead"
    PRINCIPAL = "principal"
    DIRECTOR = "director"
    VP = "vp"
    C_LEVEL = "c_level"


class JobStatus(str, enum.Enum):
    """Job posting status."""
    ACTIVE = "active"
    EXPIRED = "expired"
    FILLED = "filled"
    CLOSED = "closed"
    PAUSED = "paused"


class ApplicationStatus(str, enum.Enum):
    """Application status pipeline."""
    DISCOVERED = "discovered"
    MATCHED = "matched"
    QUEUED = "queued"
    APPLYING = "applying"
    APPLIED = "applied"
    SCREENING = "screening"
    INTERVIEW = "interview"
    OFFER = "offer"
    REJECTED = "rejected"
    WITHDRAWN = "withdrawn"
    ARCHIVED = "archived"


class InterviewType(str, enum.Enum):
    """Interview types."""
    PHONE_SCREEN = "phone_screen"
    VIDEO_CALL = "video_call"
    TECHNICAL = "technical"
    SYSTEM_DESIGN = "system_design"
    BEHAVIORAL = "behavioral"
    TAKE_HOME = "take_home"
    ON_SITE = "on_site"
    FINAL = "final"
    OTHER = "other"


class Job(Base, TimestampMixin, IDMixin):
    """Job posting model."""

    __tablename__ = "jobs"

    # Source
    source: Mapped[JobSource] = mapped_column(Enum(JobSource), nullable=False, index=True)
    source_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    source_url: Mapped[str] = mapped_column(String(1000), nullable=False)

    # Company
    company_id: Mapped[Optional[int]] = mapped_column(ForeignKey("companies.id"), index=True)
    company_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)

    # Job details
    title: Mapped[str] = mapped_column(String(500), nullable=False, index=True)
    slug: Mapped[str] = mapped_column(String(500), index=True)
    description: Mapped[Optional[str]] = mapped_column(Text)
    description_html: Mapped[Optional[str]] = mapped_column(Text)
    requirements: Mapped[Optional[str]] = mapped_column(Text)
    responsibilities: Mapped[Optional[str]] = mapped_column(Text)
    nice_to_have: Mapped[Optional[str]] = mapped_column(Text)

    # Classification
    job_type: Mapped[JobType] = mapped_column(Enum(JobType), default=JobType.FULL_TIME, index=True)
    experience_level: Mapped[ExperienceLevel] = mapped_column(Enum(ExperienceLevel), default=ExperienceLevel.MID, index=True)
    status: Mapped[JobStatus] = mapped_column(Enum(JobStatus), default=JobStatus.ACTIVE, index=True)

    # Location
    location: Mapped[Optional[str]] = mapped_column(String(255), index=True)
    is_remote: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    remote_regions: Mapped[Optional[List[str]]] = mapped_column(ARRAY(String), default=list)
    timezone_requirement: Mapped[Optional[str]] = mapped_column(String(100))
    visa_sponsorship: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    relocation_assistance: Mapped[bool] = mapped_column(Boolean, default=False)

    # Compensation
    salary_min: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2))
    salary_max: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2))
    salary_currency: Mapped[str] = mapped_column(String(3), default="USD")
    salary_period: Mapped[str] = mapped_column(String(20), default="yearly")
    equity_min: Mapped[Optional[Decimal]] = mapped_column(Numeric(8, 4))
    equity_max: Mapped[Optional[Decimal]] = mapped_column(Numeric(8, 4))
    bonus_info: Mapped[Optional[str]] = mapped_column(Text)
    benefits: Mapped[Optional[List[str]]] = mapped_column(ARRAY(String), default=list)

    # Skills & Tech
    required_skills: Mapped[Optional[List[str]]] = mapped_column(ARRAY(String), default=list)
    preferred_skills: Mapped[Optional[List[str]]] = mapped_column(ARRAY(String), default=list)
    tech_stack: Mapped[Optional[List[str]]] = mapped_column(ARRAY(String), default=list)
    languages: Mapped[Optional[List[str]]] = mapped_column(ARRAY(String), default=list)

    # Metadata
    posted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), index=True)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    viewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    applied_count: Mapped[int] = mapped_column(Integer, default=0)
    match_score: Mapped[Optional[float]] = mapped_column(Numeric(5, 4))

    # Embedding for semantic search
    embedding: Mapped[Optional[List[float]]] = mapped_column(ARRAY(Numeric), nullable=True)

    # Raw data
    raw_data: Mapped[dict] = mapped_column(JSON, default=dict)

    # Relationships
    company: Mapped[Optional["Company"]] = relationship("Company", back_populates="jobs", lazy="selectin")
    applications: Mapped[List["Application"]] = relationship("Application", back_populates="job", lazy="dynamic")

    __table_args__ = (
        UniqueConstraint("source", "source_id", name="uq_job_source"),
        Index("ix_jobs_title_trgm", "title", postgresql_using="gin", postgresql_ops={"title": "gin_trgm_ops"}),
        Index("ix_jobs_company_source", "company_id", "source"),
        Index("ix_jobs_remote_level", "is_remote", "experience_level"),
        Index("ix_jobs_salary", "salary_min", "salary_max"),
    )

    def __repr__(self) -> str:
        return f"<Job(id={self.id}, title='{self.title}', company='{self.company_name}')>"


class Application(Base, TimestampMixin, IDMixin):
    """Job application model."""

    __tablename__ = "applications"

    # Core references
    job_id: Mapped[int] = mapped_column(ForeignKey("jobs.id"), nullable=False, index=True)
    company_id: Mapped[Optional[int]] = mapped_column(ForeignKey("companies.id"), index=True)
    profile_id: Mapped[int] = mapped_column(ForeignKey("profiles.id"), nullable=False, index=True)

    # Status pipeline
    status: Mapped[ApplicationStatus] = mapped_column(Enum(ApplicationStatus), default=ApplicationStatus.DISCOVERED, index=True)
    previous_status: Mapped[Optional[ApplicationStatus]] = mapped_column(Enum(ApplicationStatus))

    # Application details
    cover_letter: Mapped[Optional[str]] = mapped_column(Text)
    resume_path: Mapped[Optional[str]] = mapped_column(String(500))
    custom_answers: Mapped[dict] = mapped_column(JSON, default=dict)  # Question -> Answer
    referral_source: Mapped[Optional[str]] = mapped_column(String(255))
    referral_contact: Mapped[Optional[str]] = mapped_column(String(255))

    # Tracking
    applied_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    application_id: Mapped[Optional[str]] = mapped_column(String(255), index=True)  # External application ID
    application_url: Mapped[Optional[str]] = mapped_column(String(1000))
    confirmation_email: Mapped[Optional[str]] = mapped_column(String(255))

    # Response tracking
    response_received: Mapped[bool] = mapped_column(Boolean, default=False)
    first_response_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    last_response_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    response_type: Mapped[Optional[str]] = mapped_column(String(100))  # auto_reply, human, rejection, interview_invite

    # Interview tracking
    interviews_count: Mapped[int] = mapped_column(Integer, default=0)
    last_interview_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    next_interview_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    # Outcome
    rejection_reason: Mapped[Optional[str]] = mapped_column(Text)
    offer_details: Mapped[Optional[dict]] = mapped_column(JSON)
    offer_received_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    offer_accepted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    start_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    # Follow-up
    follow_up_count: Mapped[int] = mapped_column(Integer, default=0)
    last_follow_up_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    next_follow_up_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    # Automation
    was_auto_applied: Mapped[bool] = mapped_column(Boolean, default=False)
    auto_apply_attempt: Mapped[int] = mapped_column(Integer, default=0)
    auto_apply_error: Mapped[Optional[str]] = mapped_column(Text)
    screenshot_path: Mapped[Optional[str]] = mapped_column(String(500))

    # Notes
    notes: Mapped[Optional[str]] = mapped_column(Text)
    tags: Mapped[List[str]] = mapped_column(ARRAY(String), default=list)

    # Raw data
    raw_data: Mapped[dict] = mapped_column(JSON, default=dict)

    # Relationships
    job: Mapped["Job"] = relationship("Job", back_populates="applications", lazy="selectin")
    company: Mapped[Optional["Company"]] = relationship("Company", back_populates="applications", lazy="selectin")
    profile: Mapped["Profile"] = relationship("Profile", back_populates="applications", lazy="selectin")
    interviews: Mapped[List["Interview"]] = relationship("Interview", back_populates="application", lazy="dynamic")
    follow_ups: Mapped[List["FollowUp"]] = relationship("FollowUp", back_populates="application", lazy="dynamic")

    __table_args__ = (
        Index("ix_applications_profile_status", "profile_id", "status"),
        Index("ix_applications_company_status", "company_id", "status"),
        Index("ix_applications_dates", "applied_at", "first_response_at"),
    )

    def __repr__(self) -> str:
        return f"<Application(id={self.id}, job_id={self.job_id}, status='{self.status}')>"


class Interview(Base, TimestampMixin, IDMixin):
    """Interview model."""

    __tablename__ = "interviews"

    application_id: Mapped[int] = mapped_column(ForeignKey("applications.id"), nullable=False, index=True)
    company_id: Mapped[Optional[int]] = mapped_column(ForeignKey("companies.id"), index=True)

    # Interview details
    type: Mapped[InterviewType] = mapped_column(Enum(InterviewType), default=InterviewType.VIDEO_CALL)
    title: Mapped[Optional[str]] = mapped_column(String(255))
    description: Mapped[Optional[str]] = mapped_column(Text)

    # Scheduling
    scheduled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    duration_minutes: Mapped[int] = mapped_column(Integer, default=60)
    timezone: Mapped[str] = mapped_column(String(50), default="UTC")
    meeting_url: Mapped[Optional[str]] = mapped_column(String(500))
    meeting_id: Mapped[Optional[str]] = mapped_column(String(255))
    meeting_password: Mapped[Optional[str]] = mapped_column(String(100))
    calendar_event_id: Mapped[Optional[str]] = mapped_column(String(255))

    # Participants
    interviewers: Mapped[List[dict]] = mapped_column(JSON, default=list)  # [{name, email, role, linkedin}]
    attendees: Mapped[List[str]] = mapped_column(ARRAY(String), default=list)

    # Status
    status: Mapped[str] = mapped_column(String(50), default="scheduled")  # scheduled, completed, cancelled, rescheduled, no_show
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    outcome: Mapped[Optional[str]] = mapped_column(String(100))  # pass, fail, pending, advance

    # Feedback
    feedback: Mapped[Optional[str]] = mapped_column(Text)
    rating: Mapped[Optional[int]] = mapped_column(Integer)  # 1-5
    strengths: Mapped[List[str]] = mapped_column(ARRAY(String), default=list)
    weaknesses: Mapped[List[str]] = mapped_column(ARRAY(String), default=list)

    # Preparation
    prep_notes: Mapped[Optional[str]] = mapped_column(Text)
    prep_materials: Mapped[List[str]] = mapped_column(ARRAY(String), default=list)
    questions_to_ask: Mapped[List[str]] = mapped_column(ARRAY(String), default=list)

    # Recording
    recording_url: Mapped[Optional[str]] = mapped_column(String(500))
    transcript: Mapped[Optional[str]] = mapped_column(Text)

    # Relationships
    application: Mapped["Application"] = relationship("Application", back_populates="interviews", lazy="selectin")
    company: Mapped[Optional["Company"]] = relationship(lazy="selectin")

    __table_args__ = (
        Index("ix_interviews_application_scheduled", "application_id", "scheduled_at"),
        Index("ix_interviews_status", "status"),
    )

    def __repr__(self) -> str:
        return f"<Interview(id={self.id}, app_id={self.application_id}, type='{self.type}')>"


class FollowUp(Base, TimestampMixin, IDMixin):
    """Follow-up tracking model."""

    __tablename__ = "follow_ups"

    application_id: Mapped[int] = mapped_column(ForeignKey("applications.id"), nullable=False, index=True)

    # Follow-up details
    type: Mapped[str] = mapped_column(String(50))  # email, linkedin, phone, referral
    channel: Mapped[str] = mapped_column(String(50))  # email, linkedin_message, phone_call, referral_intro
    direction: Mapped[str] = mapped_column(String(20))  # sent, received

    # Content
    subject: Mapped[Optional[str]] = mapped_column(String(255))
    body: Mapped[Optional[str]] = mapped_column(Text)
    template_used: Mapped[Optional[str]] = mapped_column(String(100))

    # Recipient
    to_email: Mapped[Optional[str]] = mapped_column(String(255))
    to_name: Mapped[Optional[str]] = mapped_column(String(255))
    to_linkedin: Mapped[Optional[str]] = mapped_column(String(500))

    # Status
    status: Mapped[str] = mapped_column(String(50), default="sent")  # sent, delivered, opened, replied, bounced
    sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    delivered_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    opened_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    replied_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    # Automation
    was_automated: Mapped[bool] = mapped_column(Boolean, default=False)
    trigger: Mapped[Optional[str]] = mapped_column(String(100))  # manual, scheduled, interview_follow_up, no_response

    # Relationships
    application: Mapped["Application"] = relationship("Application", back_populates="follow_ups", lazy="selectin")

    __table_args__ = (
        Index("ix_follow_ups_application_sent", "application_id", "sent_at"),
    )

    def __repr__(self) -> str:
        return f"<FollowUp(id={self.id}, app_id={self.application_id}, type='{self.type}')>"