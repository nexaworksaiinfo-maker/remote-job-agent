"""Company and employer models."""

from datetime import datetime
from typing import List, Optional
from sqlalchemy import String, Text, Integer, DateTime, ForeignKey, Index, Boolean, JSON, ARRAY, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, IDMixin


class Company(Base, TimestampMixin, IDMixin):
    """Company/Employer information."""

    __tablename__ = "companies"

    # Basic info
    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    display_name: Mapped[Optional[str]] = mapped_column(String(255))
    slug: Mapped[Optional[str]] = mapped_column(String(255), unique=True, index=True)

    # Description
    tagline: Mapped[Optional[str]] = mapped_column(String(500))
    description: Mapped[Optional[str]] = mapped_column(Text)
    mission: Mapped[Optional[str]] = mapped_column(Text)

    # Details
    industry: Mapped[Optional[str]] = mapped_column(String(255), index=True)
    sub_industry: Mapped[Optional[str]] = mapped_column(String(255))
    company_size: Mapped[Optional[str]] = mapped_column(String(100))  # 1-10, 11-50, 51-200, 201-500, 501-1000, 1001-5000, 5001-10000, 10000+
    company_size_min: Mapped[Optional[int]] = mapped_column(Integer)
    company_size_max: Mapped[Optional[int]] = mapped_column(Integer)
    company_type: Mapped[Optional[str]] = mapped_column(String(100))  # startup, public, private, non-profit, government, agency

    # Location
    headquarters: Mapped[Optional[str]] = mapped_column(String(500))
    locations: Mapped[List[str]] = mapped_column(ARRAY(String), default=list)
    remote_policy: Mapped[Optional[str]] = mapped_column(String(100))  # fully_remote, hybrid, office_required, remote_friendly

    # Contact
    website: Mapped[Optional[str]] = mapped_column(String(500))
    careers_url: Mapped[Optional[str]] = mapped_column(String(500))
    email: Mapped[Optional[str]] = mapped_column(String(255))
    phone: Mapped[Optional[str]] = mapped_column(String(100))
    linkedin_url: Mapped[Optional[str]] = mapped_column(String(500))
    twitter_url: Mapped[Optional[str]] = mapped_column(String(500))
    github_url: Mapped[Optional[str]] = mapped_column(String(500))
    glassdoor_url: Mapped[Optional[str]] = mapped_column(String(500))
    angellist_url: Mapped[Optional[str]] = mapped_column(String(500))
    crunchbase_url: Mapped[Optional[str]] = mapped_column(String(500))

    # Branding
    logo_url: Mapped[Optional[str]] = mapped_column(String(500))
    banner_url: Mapped[Optional[str]] = mapped_column(String(500))
    primary_color: Mapped[Optional[str]] = mapped_column(String(7))  # Hex color

    # Tech
    tech_stack: Mapped[List[str]] = mapped_column(ARRAY(String), default=list)
    engineering_blog_url: Mapped[Optional[str]] = mapped_column(String(500))

    # Culture
    values: Mapped[List[str]] = mapped_column(ARRAY(String), default=list)
    perks: Mapped[List[str]] = mapped_column(ARRAY(String), default=list)
    diversity_score: Mapped[Optional[float]] = mapped_column(Numeric(3, 2))
    culture_score: Mapped[Optional[float]] = mapped_column(Numeric(3, 2))
    work_life_balance_score: Mapped[Optional[float]] = mapped_column(Numeric(3, 2))
    compensation_score: Mapped[Optional[float]] = mapped_column(Numeric(3, 2))
    career_growth_score: Mapped[Optional[float]] = mapped_column(Numeric(3, 2))

    # Financial
    funding_stage: Mapped[Optional[str]] = mapped_column(String(100))  # pre_seed, seed, series_a, series_b, series_c, series_d, ipo, acquired
    total_funding: Mapped[Optional[int]] = mapped_column(Integer)
    last_funding_amount: Mapped[Optional[int]] = mapped_column(Integer)
    last_funding_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    investors: Mapped[List[str]] = mapped_column(ARRAY(String), default=list)
    revenue_range: Mapped[Optional[str]] = mapped_column(String(100))
    valuation: Mapped[Optional[int]] = mapped_column(Integer)
    is_profitable: Mapped[Optional[bool]] = mapped_column(Boolean)

    # Hiring
    is_hiring: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    open_positions_count: Mapped[int] = mapped_column(Integer, default=0)
    hiring_contact: Mapped[Optional[str]] = mapped_column(String(255))
    hiring_email: Mapped[Optional[str]] = mapped_column(String(255))
    sponsorship_available: Mapped[bool] = mapped_column(Boolean, default=False)
    remote_ok: Mapped[bool] = mapped_column(Boolean, default=True)

    # Reviews/Stats
    glassdoor_rating: Mapped[Optional[float]] = mapped_column(Numeric(3, 2))
    glassdoor_reviews_count: Mapped[int] = mapped_column(Integer, default=0)
    glassdoor_recommend_to_friend: Mapped[Optional[int]] = mapped_column(Integer)  # Percentage
    glassdoor_ceo_approval: Mapped[Optional[int]] = mapped_column(Integer)  # Percentage
    indeed_rating: Mapped[Optional[float]] = mapped_column(Numeric(3, 2))
    comparably_rating: Mapped[Optional[float]] = mapped_column(Numeric(3, 2))

    # Internal
    notes: Mapped[Optional[str]] = mapped_column(Text)
    tags: Mapped[List[str]] = mapped_column(ARRAY(String), default=list)
    is_blacklisted: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    blacklist_reason: Mapped[Optional[str]] = mapped_column(Text)
    priority: Mapped[int] = mapped_column(Integer, default=0)  # 0=normal, 1=preferred, 2=high priority, -1=avoid

    # Raw data
    raw_data: Mapped[dict] = mapped_column(JSON, default=dict)

    # Relationships
    jobs: Mapped[List["Job"]] = relationship("Job", back_populates="company", lazy="dynamic")
    applications: Mapped[List["Application"]] = relationship("Application", back_populates="company", lazy="dynamic")

    def __repr__(self) -> str:
        return f"<Company(id={self.id}, name='{self.name}', size='{self.company_size}')>"


class CompanyReview(Base, TimestampMixin, IDMixin):
    """Company reviews from employees."""

    __tablename__ = "company_reviews"

    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), nullable=False, index=True)
    source: Mapped[str] = mapped_column(String(50), nullable=False)  # glassdoor, indeed, comparably, blind, levels_fyi

    # Review content
    title: Mapped[Optional[str]] = mapped_column(String(255))
    pros: Mapped[Optional[str]] = mapped_column(Text)
    cons: Mapped[Optional[str]] = mapped_column(Text)
    advice_to_mgmt: Mapped[Optional[str]] = mapped_column(Text)

    # Ratings
    overall_rating: Mapped[float] = mapped_column(Numeric(3, 2))
    work_life_balance: Mapped[Optional[float]] = mapped_column(Numeric(3, 2))
    culture_values: Mapped[Optional[float]] = mapped_column(Numeric(3, 2))
    diversity_inclusion: Mapped[Optional[float]] = mapped_column(Numeric(3, 2))
    career_opportunities: Mapped[Optional[float]] = mapped_column(Numeric(3, 2))
    compensation_benefits: Mapped[Optional[float]] = mapped_column(Numeric(3, 2))
    senior_management: Mapped[Optional[float]] = mapped_column(Numeric(3, 2))

    # Reviewer info
    job_title: Mapped[Optional[str]] = mapped_column(String(255))
    department: Mapped[Optional[str]] = mapped_column(String(255))
    location: Mapped[Optional[str]] = mapped_column(String(255))
    employment_status: Mapped[Optional[str]] = mapped_column(String(50))  # current, former
    employment_type: Mapped[Optional[str]] = mapped_column(String(50))  # full_time, part_time, contract, intern
    years_at_company: Mapped[Optional[str]] = mapped_column(String(50))

    # Metadata
    review_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    review_id: Mapped[Optional[str]] = mapped_column(String(255))  # External ID
    helpful_count: Mapped[int] = mapped_column(Integer, default=0)
    language: Mapped[str] = mapped_column(String(10), default="en")

    # Relationships
    company: Mapped["Company"] = relationship(lazy="selectin")

    __table_args__ = (
        Index("ix_company_reviews_company_source", "company_id", "source"),
        Index("ix_company_reviews_rating", "overall_rating"),
    )

    def __repr__(self) -> str:
        return f"<CompanyReview(company_id={self.company_id}, source='{self.source}', rating={self.overall_rating})>"


class CompanySalary(Base, TimestampMixin, IDMixin):
    """Company salary data."""

    __tablename__ = "company_salaries"

    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), nullable=False, index=True)
    source: Mapped[str] = mapped_column(String(50), nullable=False)  # levels_fyi, glassdoor, indeed, payscale, h1b

    # Role
    job_title: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    level: Mapped[Optional[str]] = mapped_column(String(100))  # entry, mid, senior, staff, principal, director, vp
    location: Mapped[Optional[str]] = mapped_column(String(255))
    years_experience: Mapped[Optional[str]] = mapped_column(String(50))

    # Compensation
    base_salary_min: Mapped[Optional[int]] = mapped_column(Integer)
    base_salary_max: Mapped[Optional[int]] = mapped_column(Integer)
    base_salary_median: Mapped[Optional[int]] = mapped_column(Integer)
    total_comp_min: Mapped[Optional[int]] = mapped_column(Integer)
    total_comp_max: Mapped[Optional[int]] = mapped_column(Integer)
    total_comp_median: Mapped[Optional[int]] = mapped_column(Integer)
    stock_grant: Mapped[Optional[int]] = mapped_column(Integer)
    bonus: Mapped[Optional[int]] = mapped_column(Integer)
    currency: Mapped[str] = mapped_column(String(3), default="USD")

    # Metadata
    sample_size: Mapped[int] = mapped_column(Integer, default=1)
    reported_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    data_year: Mapped[Optional[int]] = mapped_column(Integer)

    # Relationships
    company: Mapped["Company"] = relationship(lazy="selectin")

    __table_args__ = (
        Index("ix_company_salaries_company_title", "company_id", "job_title"),
        Index("ix_company_salaries_level", "level"),
    )

    def __repr__(self) -> str:
        return f"<CompanySalary(company_id={self.company_id}, title='{self.job_title}', median={self.base_salary_median})>"