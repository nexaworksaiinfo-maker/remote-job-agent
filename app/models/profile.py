"""User profile and preferences models."""

import enum
from datetime import datetime
from typing import List, Optional
from sqlalchemy import String, Text, Integer, DateTime, ForeignKey, Index, Enum, Boolean, Numeric, JSON, ARRAY, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, IDMixin


class ProfileVisibility(str, enum.Enum):
    """Profile visibility settings."""
    PRIVATE = "private"
    RECRUITERS = "recruiters"
    PUBLIC = "public"


class NotificationChannel(str, enum.Enum):
    """Notification channels."""
    EMAIL = "email"
    TELEGRAM = "telegram"
    DISCORD = "discord"
    SLACK = "slack"
    PUSH = "push"
    IN_APP = "in_app"


class Profile(Base, TimestampMixin, IDMixin):
    """User job search profile."""

    __tablename__ = "profiles"

    # User reference
    user_id: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)  # Auth user ID
    email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)

    # Profile info
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    headline: Mapped[Optional[str]] = mapped_column(String(500))
    summary: Mapped[Optional[str]] = mapped_column(Text)
    location: Mapped[Optional[str]] = mapped_column(String(255))
    timezone: Mapped[str] = mapped_column(String(50), default="UTC")
    willingness_to_relocate: Mapped[bool] = mapped_column(Boolean, default=False)
    visa_status: Mapped[Optional[str]] = mapped_column(String(100))  # citizen, green_card, h1b, opt, cpt, need_sponsorship

    # Professional
    current_title: Mapped[Optional[str]] = mapped_column(String(255))
    current_company: Mapped[Optional[str]] = mapped_column(String(255))
    years_experience: Mapped[Optional[int]] = mapped_column(Integer)
    experience_level: Mapped[Optional[str]] = mapped_column(String(50))  # entry, junior, mid, senior, lead, principal, director+

    # Skills
    skills: Mapped[List[str]] = mapped_column(ARRAY(String), default=list)
    skills_detailed: Mapped[List[dict]] = mapped_column(JSON, default=list)  # [{name, level, years, category}]
    tech_stack: Mapped[List[str]] = mapped_column(ARRAY(String), default=list)
    languages: Mapped[List[str]] = mapped_column(ARRAY(String), default=list)
    certifications: Mapped[List[dict]] = mapped_column(JSON, default=list)

    # Job preferences
    desired_titles: Mapped[List[str]] = mapped_column(ARRAY(String), default=list)
    desired_roles: Mapped[List[str]] = mapped_column(ARRAY(String), default=list)  # backend, frontend, fullstack, devops, ml, data, mobile, etc.
    excluded_keywords: Mapped[List[str]] = mapped_column(ARRAY(String), default=list)
    excluded_companies: Mapped[List[str]] = mapped_column(ARRAY(String), default=list)
    preferred_industries: Mapped[List[str]] = mapped_column(ARRAY(String), default=list)
    excluded_industries: Mapped[List[str]] = mapped_column(ARRAY(String), default=list)

    # Compensation
    salary_min: Mapped[Optional[int]] = mapped_column(Integer)
    salary_max: Mapped[Optional[int]] = mapped_column(Integer)
    salary_currency: Mapped[str] = mapped_column(String(3), default="USD")
    equity_min: Mapped[Optional[float]] = mapped_column(Numeric(8, 4))
    equity_max: Mapped[Optional[float]] = mapped_column(Numeric(8, 4))
    negotiate_salary: Mapped[bool] = mapped_column(Boolean, default=True)

    # Work preferences
    job_types: Mapped[List[str]] = mapped_column(ARRAY(String), default=lambda: ["full_time"])
    remote_preference: Mapped[str] = mapped_column(String(50), default="remote_only")  # remote_only, hybrid, onsite_ok, any
    remote_regions: Mapped[List[str]] = mapped_column(ARRAY(String), default=list)  # us, eu, apac, latam, anywhere
    timezone_overlap_required: Mapped[Optional[str]] = mapped_column(String(100))  # e.g., "UTC-8 to UTC-5"
    travel_willingness: Mapped[int] = mapped_column(Integer, default=0)  # 0=none, 10=occasional, 50=regular, 100=any

    # Company preferences
    company_size_preference: Mapped[Optional[List[str]]] = mapped_column(ARRAY(String), default=list)  # startup, smb, enterprise
    company_stage_preference: Mapped[Optional[List[str]]] = mapped_column(ARRAY(String), default=list)  # seed, series_a, series_b, series_c, ipo, public
    required_benefits: Mapped[List[str]] = mapped_column(ARRAY(String), default=list)
    dealbreakers: Mapped[List[str]] = mapped_column(ARRAY(String), default=list)

    # Application settings
    auto_apply_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    auto_apply_max_per_day: Mapped[int] = mapped_column(Integer, default=10)
    auto_apply_min_match_score: Mapped[float] = mapped_column(Numeric(5, 4), default=0.75)
    require_cover_letter: Mapped[bool] = mapped_column(Boolean, default=True)
    custom_questions_enabled: Mapped[bool] = mapped_column(Boolean, default=True)

    # Documents
    resume_path: Mapped[Optional[str]] = mapped_column(String(500))
    resume_text: Mapped[Optional[str]] = mapped_column(Text)
    cover_letter_template: Mapped[Optional[str]] = mapped_column(Text)
    portfolio_url: Mapped[Optional[str]] = mapped_column(String(500))
    linkedin_url: Mapped[Optional[str]] = mapped_column(String(500))
    github_url: Mapped[Optional[str]] = mapped_column(String(500))
    website_url: Mapped[Optional[str]] = mapped_column(String(500))

    # Integrations
    linkedin_email: Mapped[Optional[str]] = mapped_column(String(255))
    linkedin_password_encrypted: Mapped[Optional[str]] = mapped_column(Text)
    indeed_api_key: Mapped[Optional[str]] = mapped_column(String(255))
    cal_com_api_key: Mapped[Optional[str]] = mapped_column(String(255))
    google_calendar_id: Mapped[Optional[str]] = mapped_column(String(255))

    # Notifications
    notification_channels: Mapped[List[str]] = mapped_column(ARRAY(String), default=lambda: ["email", "in_app"])
    notify_on_match: Mapped[bool] = mapped_column(Boolean, default=True)
    notify_on_application: Mapped[bool] = mapped_column(Boolean, default=True)
    notify_on_response: Mapped[bool] = mapped_column(Boolean, default=True)
    notify_on_interview: Mapped[bool] = mapped_column(Boolean, default=True)
    notify_daily_digest: Mapped[bool] = mapped_column(Boolean, default=True)
    notify_weekly_summary: Mapped[bool] = mapped_column(Boolean, default=True)
    daily_digest_time: Mapped[str] = mapped_column(String(5), default="09:00")

    # Privacy
    visibility: Mapped[ProfileVisibility] = mapped_column(Enum(ProfileVisibility), default=ProfileVisibility.PRIVATE)
    show_salary_expectations: Mapped[bool] = mapped_column(Boolean, default=False)
    allow_recruiter_contact: Mapped[bool] = mapped_column(Boolean, default=True)

    # Stats
    total_applications: Mapped[int] = mapped_column(Integer, default=0)
    total_interviews: Mapped[int] = mapped_column(Integer, default=0)
    total_offers: Mapped[int] = mapped_column(Integer, default=0)
    response_rate: Mapped[float] = mapped_column(Numeric(5, 4), default=0.0)
    interview_rate: Mapped[float] = mapped_column(Numeric(5, 4), default=0.0)
    offer_rate: Mapped[float] = mapped_column(Numeric(5, 4), default=0.0)

    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    is_searching: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    paused_until: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    last_active_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    # Raw data
    raw_data: Mapped[dict] = mapped_column(JSON, default=dict)

    # Relationships
    applications: Mapped[List["Application"]] = relationship("Application", back_populates="profile", lazy="dynamic")
    alerts: Mapped[List["JobAlert"]] = relationship("JobAlert", back_populates="profile", lazy="dynamic")

    __table_args__ = (
        Index("ix_profiles_user_active", "user_id", "is_active"),
        Index("ix_profiles_searching", "is_searching", "is_active"),
    )

    def __repr__(self) -> str:
        return f"<Profile(id={self.id}, name='{self.name}', email='{self.email}')>"


class JobAlert(Base, TimestampMixin, IDMixin):
    """Saved job search alerts."""

    __tablename__ = "job_alerts"

    profile_id: Mapped[int] = mapped_column(ForeignKey("profiles.id"), nullable=False, index=True)

    # Alert config
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)

    # Search criteria
    keywords: Mapped[List[str]] = mapped_column(ARRAY(String), default=list)
    locations: Mapped[List[str]] = mapped_column(ARRAY(String), default=list)
    remote_only: Mapped[bool] = mapped_column(Boolean, default=True)
    job_types: Mapped[List[str]] = mapped_column(ARRAY(String), default=list)
    experience_levels: Mapped[List[str]] = mapped_column(ARRAY(String), default=list)
    salary_min: Mapped[Optional[int]] = mapped_column(Integer)
    visa_sponsorship: Mapped[Optional[bool]] = mapped_column(Boolean)
    excluded_keywords: Mapped[List[str]] = mapped_column(ARRAY(String), default=list)
    excluded_companies: Mapped[List[str]] = mapped_column(ARRAY(String), default=list)
    company_sizes: Mapped[List[str]] = mapped_column(ARRAY(String), default=list)
    industries: Mapped[List[str]] = mapped_column(ARRAY(String), default=list)

    # Notification settings
    notify_channels: Mapped[List[str]] = mapped_column(ARRAY(String), default=lambda: ["email"])
    frequency: Mapped[str] = mapped_column(String(50), default="daily")  # instant, daily, weekly
    min_match_score: Mapped[float] = mapped_column(Numeric(5, 4), default=0.70)

    # Stats
    last_run_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    last_results_count: Mapped[int] = mapped_column(Integer, default=0)
    total_matches_found: Mapped[int] = mapped_column(Integer, default=0)
    total_notifications_sent: Mapped[int] = mapped_column(Integer, default=0)

    # Relationships
    profile: Mapped["Profile"] = relationship("Profile", back_populates="alerts", lazy="selectin")

    def __repr__(self) -> str:
        return f"<JobAlert(id={self.id}, name='{self.name}', profile_id={self.profile_id})>"


class ResumeVersion(Base, TimestampMixin, IDMixin):
    """Resume versioning for A/B testing."""

    __tablename__ = "resume_versions"

    profile_id: Mapped[int] = mapped_column(ForeignKey("profiles.id"), nullable=False, index=True)

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    file_hash: Mapped[str] = mapped_column(String(64), nullable=False)  # SHA256
    content_text: Mapped[Optional[str]] = mapped_column(Text)
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # A/B test stats
    applications_count: Mapped[int] = mapped_column(Integer, default=0)
    responses_count: Mapped[int] = mapped_column(Integer, default=0)
    interviews_count: Mapped[int] = mapped_column(Integer, default=0)
    offers_count: Mapped[int] = mapped_column(Integer, default=0)

    # Relationships
    profile: Mapped["Profile"] = relationship(lazy="selectin")

    def __repr__(self) -> str:
        return f"<ResumeVersion(id={self.id}, name='{self.name}', primary={self.is_primary})>"


class CoverLetterTemplate(Base, TimestampMixin, IDMixin):
    """Cover letter templates."""

    __tablename__ = "cover_letter_templates"

    profile_id: Mapped[int] = mapped_column(ForeignKey("profiles.id"), nullable=False, index=True)

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    role_category: Mapped[Optional[str]] = mapped_column(String(100))  # backend, frontend, ml, devops, etc.
    template: Mapped[str] = mapped_column(Text, nullable=False)  # Jinja2 template
    variables: Mapped[List[str]] = mapped_column(ARRAY(String), default=list)  # Required template variables
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Stats
    times_used: Mapped[int] = mapped_column(Integer, default=0)
    response_rate: Mapped[float] = mapped_column(Numeric(5, 4), default=0.0)

    # Relationships
    profile: Mapped["Profile"] = relationship(lazy="selectin")

    def __repr__(self) -> str:
        return f"<CoverLetterTemplate(id={self.id}, name='{self.name}', role='{self.role_category}')>"


class AnswerTemplate(Base, TimestampMixin, IDMixin):
    """Common application question answers."""

    __tablename__ = "answer_templates"

    profile_id: Mapped[int] = mapped_column(ForeignKey("profiles.id"), nullable=False, index=True)

    question_pattern: Mapped[str] = mapped_column(String(500), nullable=False)  # Regex pattern to match question
    answer: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[Optional[str]] = mapped_column(String(100))  # visa, salary, availability, experience, etc.
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    times_used: Mapped[int] = mapped_column(Integer, default=0)

    # Relationships
    profile: Mapped["Profile"] = relationship(lazy="selectin")

    def __repr__(self) -> str:
        return f"<AnswerTemplate(id={self.id}, pattern='{self.question_pattern[:50]}...')>"