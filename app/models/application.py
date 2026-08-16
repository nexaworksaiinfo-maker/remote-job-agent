"""Application and Profile models."""

import enum
from datetime import datetime
from typing import List, Optional
from sqlalchemy import String, Text, Integer, DateTime, ForeignKey, Index, Enum, Boolean, JSON, ARRAY, UniqueConstraint, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, IDMixin


class ApplicationStatus(str, enum.Enum):
    """Application lifecycle status."""
    DISCOVERED = "discovered"
    MATCHED = "matched"
    QUEUED = "queued"
    APPLYING = "applying"
    APPLIED = "applied"
    SCREENING = "screening"
    PHONE_SCREEN = "phone_screen"
    TECHNICAL_INTERVIEW = "technical_interview"
    ONSITE_INTERVIEW = "onsite_interview"
    FINAL_INTERVIEW = "final_interview"
    OFFER = "offer"
    NEGOTIATING = "negotiating"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    WITHDRAWN = "withdrawn"
    GHOSTED = "ghosted"
    ARCHIVED = "archived"


class InterviewType(str, enum.Enum):
    """Interview types."""
    PHONE = "phone"
    VIDEO = "video"
    TECHNICAL = "technical"
    SYSTEM_DESIGN = "system_design"
    BEHAVIORAL = "behavioral"
    TAKE_HOME = "take_home"
    PAIR_PROGRAMMING = "pair_programming"
    WHITEBOARD = "whiteboard"
    PRESENTATION = "presentation"
    CULTURE_FIT = "culture_fit"
    FINAL = "final"
    OTHER = "other"


class Profile(Base, TimestampMixin, IDMixin):
    """User profile for different role targets."""

    __tablename__ = "profiles"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    seniority: Mapped[str] = mapped_column(String(100))
    headline: Mapped[Optional[str]] = mapped_column(String(500))
    summary: Mapped[Optional[str]] = mapped_column(Text)

    # Skills
    skills: Mapped[List[str]] = mapped_column(ARRAY(String), default=list)
    primary_skills: Mapped[List[str]] = mapped_column(ARRAY(String), default=list)
    secondary_skills: Mapped[List[str]] = mapped_column(ARRAY(String), default=list)
    learning_skills: Mapped[List[str]] = mapped_column(ARRAY(String), default=list)

    # Experience
    experience_years: Mapped[int] = mapped_column(Integer, default=0)
    experience_level: Mapped[str] = mapped_column(String(50))
    current_role: Mapped[Optional[str]] = mapped_column(String(255))
    current_company: Mapped[Optional[str]] = mapped_column(String(255))

    # Preferences
    job_types: Mapped[List[str]] = mapped_column(ARRAY(String), default=["full_time"])
    locations: Mapped[List[str]] = mapped_column(ARRAY(String), default=["Remote"])
    remote_regions: Mapped[List[str]] = mapped_column(ARRAY(String), default=["US", "EU", "Global"])
    timezone_preference: Mapped[Optional[str]] = mapped_column(String(100))
    visa_sponsorship_needed: Mapped[bool] = mapped_column(Boolean, default=False)
    relocation_open: Mapped[bool] = mapped_column(Boolean, default=False)

    # Compensation
    salary_min: Mapped[Optional[int]] = mapped_column(Integer)
    salary_max: Mapped[Optional[int]] = mapped_column(Integer)
    salary_currency: Mapped[str] = mapped_column(String(3), default="USD")
    equity_expectation: Mapped[Optional[str]] = mapped_column(String(100))

    # Documents
    resume_path: Mapped[Optional[str]] = mapped_column(String(500))
    resume_text: Mapped[Optional[str]] = mapped_column(Text)
    cover_letter_template: Mapped[Optional[str]] = mapped_column(Text)
    linkedin_profile: Mapped[Optional[str]] = mapped_column(String(500))
    github_profile: Mapped[Optional[str]] = mapped_column(String(500))
    portfolio_url: Mapped[Optional[str]] = mapped_column(String(500))

    # Settings
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)
    max_daily_applications: Mapped[int] = mapped_column(Integer, default=20)
    min_match_score: Mapped[float] = mapped_column(Numeric(3, 2), default=0.65)
    auto_apply: Mapped[bool] = mapped_column(Boolean, default=False)
    require_cover_letter: Mapped[bool] = mapped_column(Boolean, default=True)

    # Stats
    total_applications: Mapped[int] = mapped_column(Integer, default=0)
    interviews_count: Mapped[int] = mapped_column(Integer, default=0)
    offers_count: Mapped[int] = mapped_column(Integer, default=0)

    # Relationships
    applications: Mapped[List["Application"]] = relationship("Application", back_populates="profile", lazy="dynamic")
    templates: Mapped[List["CoverLetterTemplate"]] = relationship("CoverLetterTemplate", back_populates="profile", lazy="dynamic")

    def __repr__(self) -> str:
        return f"<Profile(id={self.id}, name='{self.name}', role='{self.role}')>"


class Application(Base, TimestampMixin, IDMixin):
    """Job application tracking."""

    __tablename__ = "applications"

    # References
    job_id: Mapped[int] = mapped_column(ForeignKey("jobs.id"), nullable=False, index=True)
    profile_id: Mapped[int] = mapped_column(ForeignKey("profiles.id"), nullable=False, index=True)
    company_id: Mapped[Optional[int]] = mapped_column(ForeignKey("companies.id"), index=True)

    # Status
    status: Mapped[ApplicationStatus] = mapped_column(Enum(ApplicationStatus), default=ApplicationStatus.DISCOVERED, index=True)
    previous_status: Mapped[Optional[ApplicationStatus]] = mapped_column(Enum(ApplicationStatus))
    status_changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)

    # Match
    match_score: Mapped[Optional[float]] = mapped_column(Numeric(3, 2))
    match_details: Mapped[Optional[dict]] = mapped_column(JSON, default=dict)

    # Application details
    applied_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), index=True)
    applied_via: Mapped[Optional[str]] = mapped_column(String(100))  # linkedin, indeed, company_portal, email
    application_url: Mapped[Optional[str]] = mapped_column(String(1000))
    application_id: Mapped[Optional[str]] = mapped_column(String(255))  # External application ID
    confirmation_email: Mapped[Optional[str]] = mapped_column(String(255))

    # Documents used
    resume_used: Mapped[Optional[str]] = mapped_column(String(500))
    cover_letter_used: Mapped[Optional[str]] = mapped_column(Text)
    cover_letter_template_id: Mapped[Optional[int]] = mapped_column(ForeignKey("cover_letter_templates.id"))

    # Screening
    screening_score: Mapped[Optional[float]] = mapped_column(Numeric(3, 2))
    screening_notes: Mapped[Optional[str]] = mapped_column(Text)
    recruiter_name: Mapped[Optional[str]] = mapped_column(String(255))
    recruiter_email: Mapped[Optional[str]] = mapped_column(String(255))
    recruiter_linkedin: Mapped[Optional[str]] = mapped_column(String(500))

    # Interviews
    interviews: Mapped[List[dict]] = mapped_column(JSON, default=list)
    next_interview_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), index=True)
    next_interview_type: Mapped[Optional[InterviewType]] = mapped_column(Enum(InterviewType))
    next_interview_with: Mapped[Optional[str]] = mapped_column(String(255))
    next_interview_notes: Mapped[Optional[str]] = mapped_column(Text)

    # Offer
    offer_details: Mapped[Optional[dict]] = mapped_column(JSON, default=dict)
    offer_salary: Mapped[Optional[int]] = mapped_column(Integer)
    offer_equity: Mapped[Optional[str]] = mapped_column(String(100))
    offer_bonus: Mapped[Optional[int]] = mapped_column(Integer)
    offer_start_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    offer_expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    offer_response_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    # Rejection
    rejection_reason: Mapped[Optional[str]] = mapped_column(Text)
    rejection_stage: Mapped[Optional[str]] = mapped_column(String(100))
    rejection_feedback: Mapped[Optional[str]] = mapped_column(Text)

    # Tracking
    follow_up_count: Mapped[int] = mapped_column(Integer, default=0)
    last_follow_up_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    next_follow_up_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), index=True)
    is_ghosted: Mapped[bool] = mapped_column(Boolean, default=False)
    ghosted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    # Metadata
    notes: Mapped[Optional[str]] = mapped_column(Text)
    tags: Mapped[List[str]] = mapped_column(ARRAY(String), default=list)
    source_metadata: Mapped[dict] = mapped_column(JSON, default=dict)

    # Relationships
    job: Mapped["Job"] = relationship("Job", back_populates="applications", lazy="selectin")
    profile: Mapped["Profile"] = relationship("Profile", back_populates="applications", lazy="selectin")
    company: Mapped[Optional["Company"]] = relationship(lazy="selectin")
    cover_letter_template: Mapped[Optional["CoverLetterTemplate"]] = relationship(lazy="selectin")
    events: Mapped[List["ApplicationEvent"]] = relationship("ApplicationEvent", back_populates="application", lazy="dynamic", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_applications_status_date", "status", "applied_at"),
        Index("ix_applications_profile_status", "profile_id", "status"),
        Index("ix_applications_company_status", "company_id", "status"),
    )

    def __repr__(self) -> str:
        return f"<Application(id={self.id}, job_id={self.job_id}, status='{self.status}')>"


class ApplicationEvent(Base, TimestampMixin, IDMixin):
    """Application timeline events."""

    __tablename__ = "application_events"

    application_id: Mapped[int] = mapped_column(ForeignKey("applications.id"), nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)  # status_change, interview_scheduled, note_added, email_sent, etc.
    from_status: Mapped[Optional[ApplicationStatus]] = mapped_column(Enum(ApplicationStatus))
    to_status: Mapped[Optional[ApplicationStatus]] = mapped_column(Enum(ApplicationStatus))
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    metadata: Mapped[dict] = mapped_column(JSON, default=dict)
    is_system: Mapped[bool] = mapped_column(Boolean, default=False)  # System-generated vs manual

    # Relationships
    application: Mapped["Application"] = relationship("Application", back_populates="events", lazy="selectin")

    def __repr__(self) -> str:
        return f"<ApplicationEvent(id={self.id}, app_id={self.application_id}, type='{self.event_type}')>"


class CoverLetterTemplate(Base, TimestampMixin, IDMixin):
    """Cover letter templates per profile."""

    __tablename__ = "cover_letter_templates"

    profile_id: Mapped[int] = mapped_column(ForeignKey("profiles.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    template: Mapped[str] = mapped_column(Text, nullable=False)  # Jinja2 template
    variables: Mapped[List[str]] = mapped_column(ARRAY(String), default=list)  # Required variables
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)
    usage_count: Mapped[int] = mapped_column(Integer, default=0)
    success_rate: Mapped[Optional[float]] = mapped_column(Numeric(3, 2))

    # Relationships
    profile: Mapped["Profile"] = relationship("Profile", back_populates="templates", lazy="selectin")
    applications: Mapped[List["Application"]] = relationship("Application", back_populates="cover_letter_template", lazy="dynamic")

    def __repr__(self) -> str:
        return f"<CoverLetterTemplate(id={self.id}, name='{self.name}')>"


class SavedJob(Base, TimestampMixin, IDMixin):
    """User saved/bookmarked jobs."""

    __tablename__ = "saved_jobs"

    profile_id: Mapped[int] = mapped_column(ForeignKey("profiles.id"), nullable=False, index=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("jobs.id"), nullable=False, index=True)
    notes: Mapped[Optional[str]] = mapped_column(Text)
    tags: Mapped[List[str]] = mapped_column(ARRAY(String), default=list)
    priority: Mapped[int] = mapped_column(Integer, default=0)  # 0=low, 1=medium, 2=high

    # Relationships
    profile: Mapped["Profile"] = relationship(lazy="selectin")
    job: Mapped["Job"] = relationship(lazy="selectin")

    __table_args__ = (
        UniqueConstraint("profile_id", "job_id", name="uq_saved_job_profile_job"),
    )

    def __repr__(self) -> str:
        return f"<SavedJob(profile_id={self.profile_id}, job_id={self.job_id})>"