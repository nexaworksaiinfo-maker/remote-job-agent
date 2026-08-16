"""Celery tasks for job applications."""

from celery import shared_task
from datetime import datetime, timedelta
from typing import List, Dict, Any
import asyncio

from app.core.celery import celery_app
from app.core.database import get_db_context
from app.models.job import Application, ApplicationStatus, Job
from app.models.profile import Profile
from app.services.applier import AutoApplier


@shared_task(bind=True, max_retries=3)
def process_application_queue(self):
    """Process queued applications."""
    return asyncio.run(_process_application_queue())


async def _process_application_queue() -> Dict[str, Any]:
    """Process applications with QUEUED status."""
    processed = 0
    succeeded = 0
    failed = 0
    errors = []

    async with get_db_context() as db:
        # Get queued applications (limit to max concurrent)
        from sqlalchemy import select
        from app.core.config import settings

        applications = await db.execute(
            select(Application).where(
                Application.status == ApplicationStatus.QUEUED
            ).order_by(Application.created_at).limit(settings.MAX_CONCURRENT_APPLICATIONS)
        )
        applications = applications.scalars().all()

        if not applications:
            return {"processed": 0, "message": "No applications in queue"}

        applier = AutoApplier()

        for app in applications:
            try:
                # Update status to APPLYING
                app.status = ApplicationStatus.APPLYING
                app.auto_apply_attempt += 1
                await db.commit()

                # Get job and profile
                job = await db.get(Job, app.job_id)
                profile = await db.get(Profile, app.profile_id)

                if not job or not profile:
                    app.status = ApplicationStatus.FAILED
                    app.auto_apply_error = "Job or profile not found"
                    failed += 1
                    continue

                # Apply based on source
                result = None
                if job.source.value == "linkedin":
                    result = await applier.apply_linkedin(job, profile, app)
                elif job.source.value == "indeed":
                    result = await applier.apply_indeed(job, profile, app)
                else:
                    result = await applier.apply_generic(job, profile, app)

                # Update application with result
                if result.success:
                    app.status = ApplicationStatus.APPLIED
                    app.applied_at = datetime.utcnow()
                    app.application_id = result.application_id
                    app.was_auto_applied = True
                    app.screenshot_path = result.screenshot_path
                    succeeded += 1
                else:
                    app.auto_apply_error = result.error
                    app.screenshot_path = result.screenshot_path

                    # Retry logic
                    if app.auto_apply_attempt < settings.MAX_RETRIES and settings.RETRY_FAILED_APPLICATIONS:
                        app.status = ApplicationStatus.QUEUED
                    else:
                        app.status = ApplicationStatus.FAILED
                    failed += 1

                app.steps_completed = result.steps_completed
                processed += 1
                await db.commit()

            except Exception as e:
                app.status = ApplicationStatus.FAILED
                app.auto_apply_error = str(e)
                failed += 1
                errors.append(f"App {app.id}: {str(e)}")
                await db.commit()

        await applier.close()

    return {
        "processed": processed,
        "succeeded": succeeded,
        "failed": failed,
        "errors": errors,
        "timestamp": datetime.utcnow().isoformat(),
    }


@shared_task(bind=True, max_retries=3)
def retry_failed_applications(self):
    """Retry failed applications."""
    return asyncio.run(_retry_failed_applications())


async def _retry_failed_applications() -> Dict[str, Any]:
    """Retry applications that failed but are within retry limit."""
    async with get_db_context() as db:
        from sqlalchemy import select
        from app.core.config import settings

        apps = await db.execute(
            select(Application).where(
                Application.status == ApplicationStatus.FAILED,
                Application.auto_apply_attempt < settings.MAX_RETRIES,
            )
        )
        apps = apps.scalars().all()

        count = 0
        for app in apps:
            app.status = ApplicationStatus.QUEUED
            app.auto_apply_error = None
            count += 1

        await db.commit()

        # Re-queue processing
        if count > 0:
            process_application_queue.delay()

        return {"requeued": count}


@shared_task(bind=True, max_retries=3)
def apply_to_job(self, application_id: int):
    """Apply to a specific job by application ID."""
    return asyncio.run(_apply_to_job(application_id))


async def _apply_to_job(application_id: int) -> Dict[str, Any]:
    """Apply to single job."""
    async with get_db_context() as db:
        from sqlalchemy import select

        app = await db.get(Application, application_id)
        if not app:
            return {"error": "Application not found"}

        job = await db.get(Job, app.job_id)
        profile = await db.get(Profile, app.profile_id)

        if not job or not profile:
            return {"error": "Job or profile not found"}

        app.status = ApplicationStatus.APPLYING
        app.auto_apply_attempt += 1
        await db.commit()

        applier = AutoApplier()

        try:
            if job.source.value == "linkedin":
                result = await applier.apply_linkedin(job, profile, app)
            elif job.source.value == "indeed":
                result = await applier.apply_indeed(job, profile, app)
            else:
                result = await applier.apply_generic(job, profile, app)

            if result.success:
                app.status = ApplicationStatus.APPLIED
                app.applied_at = datetime.utcnow()
                app.application_id = result.application_id
                app.was_auto_applied = True
            else:
                app.auto_apply_error = result.error

            app.steps_completed = result.steps_completed
            app.screenshot_path = result.screenshot_path
            await db.commit()

            return {
                "application_id": application_id,
                "success": result.success,
                "error": result.error,
            }
        except Exception as e:
            app.status = ApplicationStatus.FAILED
            app.auto_apply_error = str(e)
            await db.commit()
            return {"error": str(e)}
        finally:
            await applier.close()


@shared_task(bind=True, max_retries=3)
def follow_up_applications(self):
    """Send follow-ups for applications without response."""
    return asyncio.run(_follow_up_applications())


async def _follow_up_applications() -> Dict[str, Any]:
    """Send follow-up emails for applications."""
    sent = 0
    errors = []

    async with get_db_context() as db:
        from sqlalchemy import select
        from app.models.job import FollowUp
        from app.services.notification import NotificationService

        # Find applications needing follow-up
        apps = await db.execute(
            select(Application).where(
                Application.status.in_([
                    ApplicationStatus.APPLIED,
                    ApplicationStatus.SCREENING,
                ]),
                Application.next_follow_up_at.isnot(None),
                Application.next_follow_up_at <= datetime.utcnow(),
            ).limit(50)
        )
        apps = apps.scalars().all()

        notification = NotificationService(db)

        for app in apps:
            try:
                job = await db.get(Job, app.job_id)
                profile = await db.get(Profile, app.profile_id)

                if job and profile and profile.email:
                    # Generate follow-up email
                    subject, body = _generate_follow_up(job, profile, app)

                    # Send
                    await notification.send_email(
                        to=profile.email,
                        subject=subject,
                        body=body,
                    )

                    # Log follow-up
                    follow_up = FollowUp(
                        application_id=app.id,
                        type="email",
                        channel="email",
                        direction="sent",
                        subject=subject,
                        body=body,
                        to_email=profile.email,
                        was_automated=True,
                        trigger="scheduled_follow_up",
                        sent_at=datetime.utcnow(),
                    )
                    db.add(follow_up)

                    # Update next follow-up
                    app.follow_up_count += 1
                    app.last_follow_up_at = datetime.utcnow()
                    app.next_follow_up_at = datetime.utcnow() + timedelta(days=7)
                    sent += 1

            except Exception as e:
                errors.append(f"App {app.id}: {str(e)}")

        await db.commit()

    return {"follow_ups_sent": sent, "errors": errors}


def _generate_follow_up(job: Job, profile: Profile, app: Application) -> tuple:
    """Generate follow-up email content."""
    subject = f"Following up: {job.title} at {job.company_name}"

    body = f"""
Hi there,

I recently applied for the {job.title} position at {job.company_name} on {app.applied_at.strftime('%B %d, %Y') if app.applied_at else 'recently'}.

I remain very interested in this opportunity and wanted to express my continued enthusiasm. With my background in {', '.join(profile.skills[:3]) if profile.skills else 'relevant technologies'}, I believe I could contribute significantly to your team.

If you need any additional information from my side, please don't hesitate to reach out. I'm happy to provide references, code samples, or schedule a brief call at your convenience.

Thank you for your time and consideration.

Best regards,
{profile.full_name or profile.name}
{profile.email}
{profile.linkedin_url or ''}
"""
    return subject, body


@shared_task(bind=True, max_retries=3)
def check_application_status(self):
    """Check status of applied applications via email/scraping."""
    return asyncio.run(_check_application_status())


async def _check_application_status() -> Dict[str, Any]:
    """Check for application updates."""
    updated = 0
    responses = 0

    async with get_db_context() as db:
        from sqlalchemy import select

        # Check applications that haven't had a response
        apps = await db.execute(
            select(Application).where(
                Application.status.in_([
                    ApplicationStatus.APPLIED,
                    ApplicationStatus.SCREENING,
                ]),
                Application.response_received == False,
            ).limit(100)
        )
        apps = apps.scalars().all()

        for app in apps:
            # In production, this would check email, LinkedIn, or company portal
            # For now, we'll just mark as checked
            app.last_checked_at = datetime.utcnow()
            updated += 1

        await db.commit()

    return {"checked": updated, "new_responses": responses}