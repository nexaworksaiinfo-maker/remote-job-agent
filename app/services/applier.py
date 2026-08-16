"""Auto-application service using Playwright."""

import asyncio
import os
import random
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from playwright.async_api import async_playwright, Browser, Page, BrowserContext, ElementHandle, TimeoutError as PlaywrightTimeoutError

from app.core.config import settings
from app.models.job import Job, Application, ApplicationStatus
from app.models.profile import Profile
from app.core.database import get_db_context


@dataclass
class ApplicationResult:
    """Result of an application attempt."""
    success: bool
    application_id: Optional[str] = None
    error: Optional[str] = None
    screenshot_path: Optional[str] = None
    steps_completed: List[str] = None


class AutoApplier:
    """Automated job application using browser automation."""

    def __init__(self):
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.playwright = None
        self.user_data_dir = Path(settings.PLAYWRIGHT_USER_DATA_DIR)
        self.user_data_dir.mkdir(parents=True, exist_ok=True)
        self.screenshots_dir = self.user_data_dir / "screenshots"
        self.screenshots_dir.mkdir(parents=True, exist_ok=True)

    async def _init_browser(self) -> None:
        """Initialize Playwright browser with stealth settings."""
        if self.browser:
            return

        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(
            headless=settings.PLAYWRIGHT_HEADLESS,
            slow_mo=settings.PLAYWRIGHT_SLOW_MO,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--disable-dev-shm-usage",
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-web-security",
                "--disable-features=IsolateOrigins,site-per-process",
            ],
        )

        # Create context with persistent user data
        self.context = await self.browser.new_context(
            user_agent=self._get_random_user_agent(),
            viewport={"width": 1920, "height": 1080},
            locale="en-US",
            timezone_id="America/New_York",
            permissions=["geolocation"],
            geolocation={"latitude": 37.7749, "longitude": -122.4194},
            color_scheme="light",
            reduced_motion="reduce",
            storage_state=str(self.user_data_dir / "storage_state.json") if (self.user_data_dir / "storage_state.json").exists() else None,
        )

        # Anti-detection scripts
        await self.context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
            window.chrome = {runtime: {}};
            Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
            Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']});
        """)

        # Add request interception for logging
        self.context.on("request", lambda req: None)
        self.context.on("response", lambda resp: None)

    def _get_random_user_agent(self) -> str:
        """Get random user agent."""
        agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
        ]
        return random.choice(agents)

    async def _random_delay(self, min_ms: int = 500, max_ms: int = 2000) -> None:
        """Random human-like delay."""
        delay = random.uniform(min_ms / 1000, max_ms / 1000)
        await asyncio.sleep(delay)

    async def _human_type(self, element: ElementHandle, text: str, delay_range: tuple = (50, 200)) -> None:
        """Type text with human-like delays."""
        await element.click()
        await self._random_delay(100, 300)
        for char in text:
            await element.type(char, delay=random.randint(*delay_range))
        await self._random_delay(100, 300)

    async def _safe_click(self, element: ElementHandle) -> bool:
        """Click element with human-like behavior."""
        try:
            box = await element.bounding_box()
            if box:
                # Move mouse to element with some randomness
                await self.page.mouse.move(
                    box["x"] + box["width"] / 2 + random.randint(-5, 5),
                    box["y"] + box["height"] / 2 + random.randint(-5, 5),
                    steps=random.randint(5, 15),
                )
                await self._random_delay(100, 300)
            await element.click()
            await self._random_delay(500, 1500)
            return True
        except Exception as e:
            print(f"Click failed: {e}")
            return False

    async def _take_screenshot(self, name: str) -> str:
        """Take screenshot for debugging."""
        path = self.screenshots_dir / f"{name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        await self.page.screenshot(path=str(path), full_page=True)
        return str(path)

    async def new_page(self) -> Page:
        """Create new page with default settings."""
        await self._init_browser()
        self.page = await self.context.new_page()
        self.page.set_default_timeout(settings.PLAYWRIGHT_TIMEOUT)
        return self.page

    async def close(self) -> None:
        """Close browser."""
        if self.context:
            # Save storage state
            await self.context.storage_state(path=str(self.user_data_dir / "storage_state.json"))
            await self.context.close()
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()

    async def apply_linkedin(self, job: Job, profile: Profile, application: Application) -> ApplicationResult:
        """Apply to LinkedIn job."""
        await self.new_page()
        steps = []

        try:
            # Navigate to job
            await self.page.goto(job.source_url, wait_until="networkidle")
            steps.append("navigated")
            await self._random_delay(2000, 4000)

            # Check if already applied
            already_applied = await self.page.locator('button:has-text("Applied")').count()
            if already_applied:
                return ApplicationResult(success=False, error="Already applied", steps_completed=steps)

            # Click Apply button
            apply_button = self.page.locator('button:has-text("Apply"), button:has-text("Easy Apply")').first
            if await apply_button.count() == 0:
                return ApplicationResult(success=False, error="No apply button found", steps_completed=steps)

            await self._safe_click(apply_button)
            steps.append("clicked_apply")
            await self._random_delay(2000, 4000)

            # Handle Easy Apply modal
            return await self._handle_linkedin_easy_apply(profile, application, steps)

        except Exception as e:
            screenshot = await self._take_screenshot(f"linkedin_error_{application.id}")
            return ApplicationResult(success=False, error=str(e), screenshot_path=screenshot, steps_completed=steps)
        finally:
            await self.page.close()

    async def _handle_linkedin_easy_apply(self, profile: Profile, application: Application, steps: List[str]) -> ApplicationResult:
        """Handle LinkedIn Easy Apply flow."""
        try:
            # Wait for modal
            modal = self.page.locator('div[data-test-modal], div.artdeco-modal').first
            await modal.wait_for(state="visible", timeout=10000)
            steps.append("modal_opened")

            # Fill phone if needed
            phone_input = self.page.locator('input[name="phoneNumber"], input[id*="phone"]').first
            if await phone_input.count() > 0 and profile.phone:
                await self._human_type(await phone_input.element_handle(), profile.phone)
                steps.append("filled_phone")

            # Upload resume
            resume_input = self.page.locator('input[type="file"][accept*="pdf"], input[type="file"][id*="resume"]').first
            if await resume_input.count() > 0 and profile.resume_path:
                await resume_input.set_input_files(profile.resume_path)
                steps.append("uploaded_resume")
                await self._random_delay(2000, 4000)

            # Next/Review buttons
            for _ in range(5):  # Max 5 steps
                # Check for submit button
                submit_btn = self.page.locator('button:has-text("Submit application"), button:has-text("Submit")').first
                if await submit_btn.count() > 0:
                    await self._safe_click(submit_btn)
                    steps.append("submitted")
                    break

                # Next/Continue/Review
                next_btn = self.page.locator('button:has-text("Next"), button:has-text("Continue"), button:has-text("Review")').first
                if await next_btn.count() > 0:
                    await self._safe_click(next_btn)
                    steps.append("next_step")
                    await self._random_delay(1500, 3000)
                    continue

                # Handle questions
                await self._handle_application_questions(profile, steps)
                await self._random_delay(1000, 2000)

            # Verify submission
            success_indicator = self.page.locator('text=Application submitted, text=Your application was sent, text=Applied').first
            if await success_indicator.count() > 0:
                # Get application ID if available
                app_id_elem = self.page.locator('[data-application-id], .application-id').first
                app_id = await app_id_elem.text_content() if await app_id_elem.count() > 0 else None

                return ApplicationResult(success=True, application_id=app_id, steps_completed=steps)

            # Check for errors
            error_elem = self.page.locator('.artdeco-inline-feedback--error, .error-message').first
            if await error_elem.count() > 0:
                error_text = await error_elem.text_content()
                return ApplicationResult(success=False, error=error_text, steps_completed=steps)

            return ApplicationResult(success=True, steps_completed=steps)

        except PlaywrightTimeoutError:
            screenshot = await self._take_screenshot(f"linkedin_timeout_{application.id}")
            return ApplicationResult(success=False, error="Timeout during application", screenshot_path=screenshot, steps_completed=steps)
        except Exception as e:
            screenshot = await self._take_screenshot(f"linkedin_error_{application.id}")
            return ApplicationResult(success=False, error=str(e), screenshot_path=screenshot, steps_completed=steps)

    async def _handle_application_questions(self, profile: Profile, steps: List[str]) -> None:
        """Handle common application questions."""
        # Find all question fields
        questions = await self.page.locator('div[data-test-form-element], .fb-dash-form-element').all()

        for question in questions:
            try:
                label = await question.locator('label, .fb-dash-form-element__label').first.text_content()
                if not label:
                    continue

                label_lower = label.lower()

                # Determine answer based on label
                answer = None
                if any(kw in label_lower for kw in ["year", "experience", "yoe"]):
                    answer = str(profile.years_experience)
                elif any(kw in label_lower for kw in ["salary", "compensation", "expected", "desired"]):
                    answer = str(profile.salary_min or profile.salary_max or "")
                elif any(kw in label_lower for kw in ["notice", "available", "start"]):
                    answer = "2 weeks"
                elif any(kw in label_lower for kw in ["visa", "sponsor", "authorization", "work author"]):
                    answer = "Yes" if profile.visa_sponsorship_needed else "No"
                elif any(kw in label_lower for kw in ["relocate", "relocation", "move"]):
                    answer = "Yes" if profile.willingness_to_relocate else "No"
                elif any(kw in label_lower for kw in ["linkedin", "profile"]):
                    answer = profile.linkedin_url or ""
                elif any(kw in label_lower for kw in ["github", "portfolio", "website"]):
                    answer = profile.github_url or profile.portfolio_url or ""
                elif any(kw in label_lower for kw in ["cover letter", "why", "interest", "motivation"]):
                    answer = profile.cover_letter_template or ""
                elif any(kw in label_lower for kw in ["phone", "mobile", "telephone"]):
                    answer = profile.phone or ""
                elif any(kw in label_lower for kw in ["email"]):
                    answer = profile.email or ""
                elif any(kw in label_lower for kw in ["name", "full name"]):
                    answer = profile.full_name or ""
                else:
                    # Try to find matching custom answer
                    for q, a in profile.custom_answers.items():
                        if q.lower() in label_lower:
                            answer = a
                            break

                if answer:
                    input_elem = question.locator('input, textarea, select').first
                    if await input_elem.count() > 0:
                        tag = await input_elem.evaluate("el => el.tagName.toLowerCase()")
                        if tag == "select":
                            await input_elem.select_option(label=answer)
                        else:
                            await self._human_type(await input_elem.element_handle(), answer)
                        steps.append(f"answered_{label_lower[:30]}")

            except Exception as e:
                print(f"Error handling question: {e}")
                continue

    async def apply_indeed(self, job: Job, profile: Profile, application: Application) -> ApplicationResult:
        """Apply to Indeed job."""
        await self.new_page()
        steps = []

        try:
            await self.page.goto(job.source_url, wait_until="networkidle")
            steps.append("navigated")
            await self._random_delay(2000, 4000)

            # Click apply button
            apply_btn = self.page.locator('button:has-text("Apply"), a:has-text("Apply")').first
            if await apply_btn.count() == 0:
                return ApplicationResult(success=False, error="No apply button", steps_completed=steps)

            await self._safe_click(apply_btn)
            steps.append("clicked_apply")
            await self._random_delay(2000, 4000)

            # Handle Indeed apply flow
            return await self._handle_indeed_apply(profile, application, steps)

        except Exception as e:
            screenshot = await self._take_screenshot(f"indeed_error_{application.id}")
            return ApplicationResult(success=False, error=str(e), screenshot_path=screenshot, steps_completed=steps)
        finally:
            await self.page.close()

    async def _handle_indeed_apply(self, profile: Profile, application: Application, steps: List[str]) -> ApplicationResult:
        """Handle Indeed application flow."""
        try:
            # Indeed often redirects to company site or has iframe
            # Wait for either
            await self.page.wait_for_load_state("networkidle")

            # Check if redirected
            if "indeed.com" not in self.page.url:
                # On company site - generic handler
                return await self._handle_generic_apply(profile, application, steps)

            # Look for Indeed apply form
            continue_btn = self.page.locator('button:has-text("Continue"), button:has-text("Continue with Indeed")').first
            if await continue_btn.count() > 0:
                await self._safe_click(continue_btn)
                steps.append("indeed_continue")
                await self._random_delay(2000, 4000)

            # Fill form
            await self._fill_generic_form(profile, steps)

            # Submit
            submit_btn = self.page.locator('button:has-text("Submit"), button:has-text("Apply"), button[type="submit"]').first
            if await submit_btn.count() > 0:
                await self._safe_click(submit_btn)
                steps.append("submitted")

            await self._random_delay(2000, 4000)

            # Check success
            if await self.page.locator('text=Application submitted, text=Applied, text=Thank you').count() > 0:
                return ApplicationResult(success=True, steps_completed=steps)

            return ApplicationResult(success=True, steps_completed=steps)

        except Exception as e:
            screenshot = await self._take_screenshot(f"indeed_error_{application.id}")
            return ApplicationResult(success=False, error=str(e), screenshot_path=screenshot, steps_completed=steps)

    async def _handle_generic_apply(self, profile: Profile, application: Application, steps: List[str]) -> ApplicationResult:
        """Generic application handler for company career sites."""
        try:
            # Common ATS systems: Greenhouse, Lever, Workday, Ashby, etc.
            await self._random_delay(2000, 4000)

            # Upload resume if file input
            file_inputs = await self.page.locator('input[type="file"]').all()
            for inp in file_inputs:
                accept = await inp.get_attribute("accept")
                if accept and ("pdf" in accept or "doc" in accept):
                    if profile.resume_path:
                        await inp.set_input_files(profile.resume_path)
                        steps.append("uploaded_resume")
                        await self._random_delay(1000, 2000)

            # Fill form fields
            await self._fill_generic_form(profile, steps)

            # Submit
            submit_selectors = [
                'button:has-text("Submit")',
                'button:has-text("Apply")',
                'button:has-text("Send")',
                'button[type="submit"]',
                'input[type="submit"]',
            ]
            for selector in submit_selectors:
                btn = self.page.locator(selector).first
                if await btn.count() > 0:
                    await self._safe_click(btn)
                    steps.append("submitted")
                    break

            await self._random_delay(2000, 4000)

            # Check success
            success_selectors = [
                'text=Thank you',
                'text=Application submitted',
                'text=Application received',
                'text=Successfully applied',
                '.success-message',
                '.confirmation',
            ]
            for selector in success_selectors:
                if await self.page.locator(selector).count() > 0:
                    return ApplicationResult(success=True, steps_completed=steps)

            return ApplicationResult(success=True, steps_completed=steps)

        except Exception as e:
            screenshot = await self._take_screenshot(f"generic_error_{application.id}")
            return ApplicationResult(success=False, error=str(e), screenshot_path=screenshot, steps_completed=steps)

    async def _fill_generic_form(self, profile: Profile, steps: List[str]) -> None:
        """Fill generic form fields."""
        field_mapping = {
            "first_name": ["input[name*='first'], input[id*='first'], input[placeholder*='first']"],
            "last_name": ["input[name*='last'], input[id*='last'], input[placeholder*='last']"],
            "email": ["input[type='email'], input[name*='email'], input[id*='email']"],
            "phone": ["input[type='tel'], input[name*='phone'], input[id*='phone']"],
            "linkedin": ["input[name*='linkedin'], input[id*='linkedin'], input[placeholder*='linkedin']"],
            "github": ["input[name*='github'], input[id*='github'], input[placeholder*='github']"],
            "portfolio": ["input[name*='portfolio'], input[id*='portfolio'], input[placeholder*='portfolio']"],
            "cover_letter": ["textarea[name*='cover'], textarea[id*='cover'], textarea[placeholder*='cover']"],
            "address": ["input[name*='address'], input[id*='address'], textarea[name*='address']"],
            "city": ["input[name*='city'], input[id*='city']"],
            "state": ["input[name*='state'], input[id*='state'], select[name*='state']"],
            "zip": ["input[name*='zip'], input[id*='zip'], input[name*='postal']"],
            "country": ["input[name*='country'], input[id*='country'], select[name*='country']"],
        }

        values = {
            "first_name": profile.first_name,
            "last_name": profile.last_name,
            "email": profile.email,
            "phone": profile.phone,
            "linkedin": profile.linkedin_url,
            "github": profile.github_url,
            "portfolio": profile.portfolio_url,
            "cover_letter": profile.cover_letter_template,
        }

        for field, selectors in field_mapping.items():
            value = values.get(field)
            if not value:
                continue

            for selector in selectors:
                elem = self.page.locator(selector).first
                if await elem.count() > 0:
                    try:
                        tag = await elem.evaluate("el => el.tagName.toLowerCase()")
                        if tag == "select":
                            await elem.select_option(label=value)
                        elif tag == "textarea":
                            await self._human_type(await elem.element_handle(), value)
                        else:
                            await elem.fill(value)
                        steps.append(f"filled_{field}")
                        break
                    except Exception:
                        continue


class ApplicationQueue:
    """Manage application queue with rate limiting."""

    def __init__(self):
        self.applier = AutoApplier()
        self.running = False
        self.daily_count = 0
        self.daily_reset_time = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

    async def process_queue(self, max_applications: int = None) -> Dict[str, int]:
        """Process queued applications."""
        max_applications = max_applications or settings.MAX_DAILY_APPLICATIONS

        async with get_db_context() as db:
            # Reset daily counter if new day
            now = datetime.utcnow()
            if now >= self.daily_reset_time + timedelta(days=1):
                self.daily_count = 0
                self.daily_reset_time = now.replace(hour=0, minute=0, second=0, microsecond=0)

            remaining = max_applications - self.daily_count
            if remaining <= 0:
                return {"processed": 0, "successful": 0, "failed": 0, "remaining_today": 0}

            # Get queued applications
            from sqlalchemy import select
            from app.models.job import Application, ApplicationStatus

            query = select(Application).where(
                and_(
                    Application.status == ApplicationStatus.QUEUED,
                    Application.auto_apply_attempt < settings.MAX_RETRIES,
                )
            ).order_by(Application.created_at).limit(remaining)

            result = await db.execute(query)
            applications = result.scalars().all()

            stats = {"processed": 0, "successful": 0, "failed": 0, "remaining_today": remaining}

            for app in applications:
                if self.daily_count >= max_applications:
                    break

                # Load job and profile
                job = await db.get(Job, app.job_id)
                profile = await db.get(Profile, app.profile_id)

                if not job or not profile:
                    app.status = ApplicationStatus.FAILED
                    app.auto_apply_error = "Job or profile not found"
                    stats["failed"] += 1
                    continue

                # Apply based on source
                result = None
                if job.source.value == "linkedin":
                    result = await self.applier.apply_linkedin(job, profile, app)
                elif job.source.value == "indeed":
                    result = await self.applier.apply_indeed(job, profile, app)
                else:
                    result = await self.applier._handle_generic_apply(profile, app, [])

                # Update application
                app.auto_apply_attempt += 1
                app.auto_apply_error = result.error
                app.screenshot_path = result.screenshot_path
                app.was_auto_applied = True

                if result.success:
                    app.status = ApplicationStatus.APPLIED
                    app.applied_at = datetime.utcnow()
                    app.application_id = result.application_id
                    app.application_url = job.source_url
                    stats["successful"] += 1
                elif app.auto_apply_attempt >= settings.MAX_RETRIES:
                    app.status = ApplicationStatus.FAILED
                    stats["failed"] += 1
                else:
                    app.status = ApplicationStatus.QUEUED  # Retry later
                    stats["failed"] += 1

                self.daily_count += 1
                stats["processed"] += 1
                stats["remaining_today"] = max_applications - self.daily_count

                await db.commit()

                # Rate limiting between applications
                await asyncio.sleep(random.uniform(30, 60))

            await self.applier.close()
            return stats