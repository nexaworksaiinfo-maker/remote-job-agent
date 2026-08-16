"""Job scraper services."""

import asyncio
import random
import re
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from urllib.parse import urljoin, urlencode
import httpx
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright, Browser, Page, BrowserContext

from app.core.config import settings
from app.models.job import Job, JobSource, JobType, ExperienceLevel, JobStatus


class BaseScraper(ABC):
    """Base class for job scrapers."""

    def __init__(self):
        self.source: JobSource = JobSource.OTHER
        self.base_url: str = ""
        self.rate_limit_delay: tuple = (settings.REQUEST_DELAY_MIN, settings.REQUEST_DELAY_MAX)
        self.headers = {
            "User-Agent": self._get_user_agent(),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate",
            "Connection": "keep-alive",
        }

    def _get_user_agent(self) -> str:
        """Get random user agent."""
        agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
        ]
        return random.choice(agents)

    async def _rate_limit(self):
        """Apply rate limiting."""
        delay = random.uniform(*self.rate_limit_delay)
        await asyncio.sleep(delay)

    @abstractmethod
    async def search_jobs(self, query: str, location: str = "Remote", **kwargs) -> List[Dict[str, Any]]:
        """Search for jobs."""
        pass

    @abstractmethod
    async def parse_job_detail(self, job_url: str) -> Optional[Dict[str, Any]]:
        """Parse detailed job information."""
        pass

    def _parse_salary(self, salary_text: str) -> tuple:
        """Parse salary from text."""
        if not salary_text:
            return None, None, "USD", "yearly"

        # Common patterns
        patterns = [
            r"\$?(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)\s*[-–]\s*\$?(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)",
            r"\$?(\d{1,3}(?:,\d{3})*)\s*[-–]\s*(\d{1,3}(?:,\d{3})*)",
            r"up to\s+\$?(\d{1,3}(?:,\d{3})*)",
            r"\$?(\d{1,3}(?:,\d{3})*)\+",
        ]

        for pattern in patterns:
            match = re.search(pattern, salary_text, re.IGNORECASE)
            if match:
                groups = match.groups()
                if len(groups) == 2:
                    min_sal = float(groups[0].replace(",", ""))
                    max_sal = float(groups[1].replace(",", ""))
                    return min_sal, max_sal, "USD", "yearly"
                elif len(groups) == 1:
                    sal = float(groups[0].replace(",", ""))
                    if "up to" in salary_text.lower():
                        return None, sal, "USD", "yearly"
                    else:
                        return sal, None, "USD", "yearly"

        return None, None, "USD", "yearly"

    def _parse_experience(self, text: str) -> ExperienceLevel:
        """Parse experience level from text."""
        text = text.lower()
        if any(kw in text for kw in ["entry", "junior", "0-1", "0-2", "new grad", "graduate"]):
            return ExperienceLevel.ENTRY
        elif any(kw in text for kw in ["junior", "1-2", "1-3", "associate"]):
            return ExperienceLevel.JUNIOR
        elif any(kw in text for kw in ["mid", "mid-level", "3-5", "2-4", "intermediate"]):
            return ExperienceLevel.MID
        elif any(kw in text for kw in ["senior", "sr.", "lead", "5-7", "5-8", "6-8", "7+"]):
            return ExperienceLevel.SENIOR
        elif any(kw in text for kw in ["staff", "principal", "architect", "8+", "10+"]):
            return ExperienceLevel.PRINCIPAL
        elif any(kw in text for kw in ["director", "vp", "vice president", "head of"]):
            return ExperienceLevel.DIRECTOR
        elif any(kw in text for kw in ["c-level", "cto", "ceo", "cfo", "chief"]):
            return ExperienceLevel.C_LEVEL
        return ExperienceLevel.MID

    def _parse_job_type(self, text: str) -> JobType:
        """Parse job type from text."""
        text = text.lower()
        if "contract" in text or "freelance" in text:
            return JobType.CONTRACT
        elif "part.time" in text or "part-time" in text:
            return JobType.PART_TIME
        elif "intern" in text:
            return JobType.INTERNSHIP
        elif "temporary" in text or "temp" in text:
            return JobType.TEMPORARY
        return JobType.FULL_TIME

    def _is_remote(self, text: str) -> bool:
        """Check if job is remote."""
        text = text.lower()
        remote_keywords = ["remote", "work from home", "wfh", "distributed", "anywhere", "worldwide", "global"]
        return any(kw in text for kw in remote_keywords)

    def _extract_skills(self, text: str) -> List[str]:
        """Extract technical skills from job description."""
        # Common tech skills
        skills_db = [
            "python", "javascript", "typescript", "java", "go", "rust", "c++", "c#", "ruby", "php",
            "react", "vue", "angular", "svelte", "next.js", "nuxt", "remix",
            "django", "fastapi", "flask", "express", "nestjs", "spring", "rails", "laravel",
            "postgresql", "mysql", "mongodb", "redis", "elasticsearch", "dynamodb", "cassandra",
            "aws", "gcp", "azure", "docker", "kubernetes", "terraform", "ansible",
            "ci/cd", "github actions", "gitlab ci", "jenkins", "circleci",
            "graphql", "rest", "grpc", "microservices", "serverless",
            "machine learning", "ml", "ai", "pytorch", "tensorflow", "scikit-learn",
            "data science", "pandas", "numpy", "sql", "spark", "kafka", "airflow",
        ]

        text_lower = text.lower()
        found = [skill for skill in skills_db if skill in text_lower]
        return found


class RemoteOKScraper(BaseScraper):
    """Scraper for RemoteOK.com"""

    def __init__(self):
        super().__init__()
        self.source = JobSource.REMOTEOK
        self.base_url = "https://remoteok.com"

    async def search_jobs(self, query: str, location: str = "Remote", **kwargs) -> List[Dict[str, Any]]:
        """Search jobs on RemoteOK."""
        jobs = []
        url = f"{self.base_url}/remote-{query.replace(' ', '-')}-jobs"

        async with httpx.AsyncClient(headers=self.headers, timeout=30) as client:
            try:
                response = await client.get(url)
                response.raise_for_status()
                soup = BeautifulSoup(response.text, "html.parser")

                # Parse job table
                for row in soup.select("table#jobsboard tr.job"):
                    try:
                        job_data = self._parse_job_row(row)
                        if job_data:
                            jobs.append(job_data)
                    except Exception as e:
                        print(f"Error parsing RemoteOK job row: {e}")
                        continue

            except Exception as e:
                print(f"Error searching RemoteOK: {e}")

        await self._rate_limit()
        return jobs

    def _parse_job_row(self, row) -> Optional[Dict[str, Any]]:
        """Parse a job row from RemoteOK table."""
        try:
            # Company and position
            company_elem = row.select_one("td.company a.companyLink")
            position_elem = row.select_one("td.company h2")

            if not company_elem or not position_elem:
                return None

            company = company_elem.get_text(strip=True)
            title = position_elem.get_text(strip=True)

            # Link
            link_elem = row.select_one("a.preventLink")
            if not link_elem:
                link_elem = row.select_one("td.position a")
            job_url = urljoin(self.base_url, link_elem.get("href", "")) if link_elem else ""

            # Tags
            tags = [tag.get_text(strip=True) for tag in row.select("td.tags a.tag")]

            # Location
            location_elem = row.select_one("td.location")
            location = location_elem.get_text(strip=True) if location_elem else "Remote"

            # Salary
            salary_elem = row.select_one("td.salary")
            salary_text = salary_elem.get_text(strip=True) if salary_elem else ""
            salary_min, salary_max, currency, period = self._parse_salary(salary_text)

            # Date
            date_elem = row.select_one("td.time time")
            posted_at = None
            if date_elem and date_elem.get("datetime"):
                posted_at = datetime.fromisoformat(date_elem["datetime"].replace("Z", "+00:00"))

            return {
                "source": self.source.value,
                "source_id": row.get("data-id", ""),
                "source_url": job_url,
                "company_name": company,
                "title": title,
                "description": "",
                "location": location,
                "is_remote": True,
                "remote_regions": ["Global"],
                "salary_min": salary_min,
                "salary_max": salary_max,
                "salary_currency": currency,
                "salary_period": period,
                "tech_stack": tags,
                "posted_at": posted_at,
                "raw_data": {"tags": tags},
            }
        except Exception as e:
            print(f"Error parsing RemoteOK row: {e}")
            return None

    async def parse_job_detail(self, job_url: str) -> Optional[Dict[str, Any]]:
        """Parse detailed job page."""
        async with httpx.AsyncClient(headers=self.headers, timeout=30) as client:
            try:
                response = await client.get(job_url)
                response.raise_for_status()
                soup = BeautifulSoup(response.text, "html.parser")

                # Main content
                content = soup.select_one("div.job-description")
                description = content.get_text(strip=True) if content else ""

                # Requirements
                requirements_elem = soup.select_one("div.requirements")
                requirements = requirements_elem.get_text(strip=True) if requirements_elem else ""

                return {
                    "description": description,
                    "requirements": requirements,
                }
            except Exception as e:
                print(f"Error parsing RemoteOK detail: {e}")
                return None


class WeWorkRemotelyScraper(BaseScraper):
    """Scraper for WeWorkRemotely.com"""

    def __init__(self):
        super().__init__()
        self.source = JobSource.WEWORKREMOTELY
        self.base_url = "https://weworkremotely.com"

    async def search_jobs(self, query: str, location: str = "Remote", **kwargs) -> List[Dict[str, Any]]:
        """Search jobs on WeWorkRemotely."""
        jobs = []
        url = f"{self.base_url}/remote-jobs/search"
        params = {"term": query, "button": ""}

        async with httpx.AsyncClient(headers=self.headers, timeout=30) as client:
            try:
                response = await client.get(url, params=params)
                response.raise_for_status()
                soup = BeautifulSoup(response.text, "html.parser")

                # Parse job listings
                for section in soup.select("section.jobs"):
                    for li in section.select("li:not(.view-all)"):
                        job_data = self._parse_job_li(li)
                        if job_data:
                            jobs.append(job_data)

            except Exception as e:
                print(f"Error searching WeWorkRemotely: {e}")

        await self._rate_limit()
        return jobs

    def _parse_job_li(self, li) -> Optional[Dict[str, Any]]:
        """Parse job list item."""
        try:
            # Link
            link = li.select_one("a")
            if not link:
                return None
            job_url = urljoin(self.base_url, link.get("href", ""))

            # Company
            company_elem = li.select_one("span.company")
            company = company_elem.get_text(strip=True) if company_elem else ""

            # Title
            title_elem = li.select_one("span.title")
            title = title_elem.get_text(strip=True) if title_elem else ""

            # Location
            location_elem = li.select_one("span.region")
            location = location_elem.get_text(strip=True) if location_elem else "Remote"

            # Tags
            tags = [tag.get_text(strip=True) for tag in li.select("span.tag")]

            return {
                "source": self.source.value,
                "source_id": job_url.split("/")[-1] if job_url else "",
                "source_url": job_url,
                "company_name": company,
                "title": title,
                "location": location,
                "is_remote": True,
                "tech_stack": tags,
                "raw_data": {"tags": tags},
            }
        except Exception as e:
            print(f"Error parsing WWR job: {e}")
            return None

    async def parse_job_detail(self, job_url: str) -> Optional[Dict[str, Any]]:
        """Parse detailed job page."""
        async with httpx.AsyncClient(headers=self.headers, timeout=30) as client:
            try:
                response = await client.get(job_url)
                response.raise_for_status()
                soup = BeautifulSoup(response.text, "html.parser")

                content = soup.select_one("div.listing-container")
                description = content.get_text(strip=True) if content else ""

                return {"description": description}
            except Exception as e:
                print(f"Error parsing WWR detail: {e}")
                return None


class LinkedInScraper(BaseScraper):
    """Scraper for LinkedIn Jobs (requires login)."""

    def __init__(self):
        super().__init__()
        self.source = JobSource.LINKEDIN
        self.base_url = "https://www.linkedin.com"
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None

    async def _init_browser(self):
        """Initialize Playwright browser."""
        if self.browser is None:
            playwright = await async_playwright().start()
            self.browser = await playwright.chromium.launch(
                headless=settings.PLAYWRIGHT_HEADLESS,
                slow_mo=settings.PLAYWRIGHT_SLOW_MO,
                args=["--disable-blink-features=AutomationControlled"],
            )
            self.context = await self.browser.new_context(
                user_agent=self._get_user_agent(),
                viewport={"width": 1920, "height": 1080},
                locale="en-US",
            )
            # Add stealth scripts
            await self.context.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                window.chrome = {runtime: {}};
            """)

    async def _login(self, page: Page) -> bool:
        """Login to LinkedIn."""
        email = settings.LINKEDIN_EMAIL
        password = settings.LINKEDIN_PASSWORD
        if not email or not password:
            return False

        try:
            await page.goto("https://www.linkedin.com/login")
            await page.wait_for_selector("#username", timeout=10000)
            await page.fill("#username", email)
            await page.fill("#password", password)
            await page.click('button[type="submit"]')
            await page.wait_for_url("https://www.linkedin.com/feed/", timeout=15000)
            return True
        except Exception as e:
            print(f"LinkedIn login failed: {e}")
            return False

    async def search_jobs(self, query: str, location: str = "Remote", **kwargs) -> List[Dict[str, Any]]:
        """Search jobs on LinkedIn."""
        await self._init_browser()

        if not self.context:
            return []

        page = await self.context.new_page()
        jobs = []

        try:
            # Login if needed
            await self._login(page)

            # Search URL
            search_url = f"{self.base_url}/jobs/search/"
            params = {
                "keywords": query,
                "location": location,
                "f_TPR": "r86400",  # Past 24 hours
                "f_WT": "2",  # Remote
                "sortBy": "DD",  # Most recent
            }
            url = f"{search_url}?{urlencode(params)}"

            await page.goto(url)
            await page.wait_for_selector("ul.jobs-search__results-list", timeout=15000)

            # Scroll to load more
            for _ in range(3):
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await asyncio.sleep(2)

            # Parse jobs
            job_cards = await page.query_selector_all("li[data-occludable-job-id]")
            for card in job_cards[:50]:
                job_data = await self._parse_job_card(card, page)
                if job_data:
                    jobs.append(job_data)

        except Exception as e:
            print(f"Error searching LinkedIn: {e}")
        finally:
            await page.close()

        await self._rate_limit()
        return jobs

    async def _parse_job_card(self, card, page: Page) -> Optional[Dict[str, Any]]:
        """Parse job card."""
        try:
            # Get job ID
            job_id = await card.get_attribute("data-occludable-job-id")

            # Click to view details
            await card.click()
            await asyncio.sleep(1)

            # Parse detail panel
            detail = page.locator(".job-details-jobs-unified-top-card__container")
            await detail.wait_for(timeout=5000)

            title = await detail.locator("h1").text_content()
            company = await detail.locator(".job-details-jobs-unified-top-card__company-name").text_content()
            location = await detail.locator(".job-details-jobs-unified-top-card__bullet").first.text_content()

            # Get description
            desc_elem = page.locator("#job-details")
            description = await desc_elem.text_content() if await desc_elem.count() > 0 else ""

            return {
                "source": self.source.value,
                "source_id": job_id,
                "source_url": f"{self.base_url}/jobs/view/{job_id}",
                "company_name": company.strip() if company else "",
                "title": title.strip() if title else "",
                "location": location.strip() if location else "Remote",
                "description": description,
                "is_remote": self._is_remote(location or ""),
                "raw_data": {},
            }
        except Exception as e:
            print(f"Error parsing LinkedIn card: {e}")
            return None

    async def parse_job_detail(self, job_url: str) -> Optional[Dict[str, Any]]:
        """Parse detailed job page."""
        await self._init_browser()
        page = await self.context.new_page()

        try:
            await page.goto(job_url)
            await page.wait_for_selector(".job-details-jobs-unified-top-card__container", timeout=10000)

            # Extract all details
            description_elem = page.locator("#job-details")
            description = await description_elem.text_content() if await description_elem.count() > 0 else ""

            return {"description": description}
        except Exception as e:
            print(f"Error parsing LinkedIn detail: {e}")
            return None
        finally:
            await page.close()

    async def close(self):
        """Close browser."""
        if self.browser:
            await self.browser.close()
            self.browser = None
            self.context = None


class IndeedScraper(BaseScraper):
    """Scraper for Indeed.com"""

    def __init__(self):
        super().__init__()
        self.source = JobSource.INDEED
        self.base_url = "https://www.indeed.com"

    async def search_jobs(self, query: str, location: str = "Remote", **kwargs) -> List[Dict[str, Any]]:
        """Search jobs on Indeed."""
        jobs = []
        params = {
            "q": query,
            "l": location,
            "remotejob": "1",
            "sort": "date",
            "fromage": "1",  # Last 24 hours
        }

        async with httpx.AsyncClient(headers=self.headers, timeout=30) as client:
            try:
                response = await client.get(f"{self.base_url}/jobs", params=params)
                response.raise_for_status()
                soup = BeautifulSoup(response.text, "html.parser")

                for card in soup.select("div.job_seen_beacon"):
                    job_data = self._parse_job_card(card)
                    if job_data:
                        jobs.append(job_data)

            except Exception as e:
                print(f"Error searching Indeed: {e}")

        await self._rate_limit()
        return jobs

    def _parse_job_card(self, card) -> Optional[Dict[str, Any]]:
        """Parse Indeed job card."""
        try:
            # Title and link
            title_elem = card.select_one("h2.jobTitle a")
            if not title_elem:
                return None

            title = title_elem.get_text(strip=True)
            job_id = title_elem.get("data-jk", "")
            job_url = urljoin(self.base_url, title_elem.get("href", ""))

            # Company
            company_elem = card.select_one("span.companyName")
            company = company_elem.get_text(strip=True) if company_elem else ""

            # Location
            location_elem = card.select_one("div.companyLocation")
            location = location_elem.get_text(strip=True) if location_elem else "Remote"

            # Salary
            salary_elem = card.select_one("div.salary-snippet")
            salary_text = salary_elem.get_text(strip=True) if salary_elem else ""
            salary_min, salary_max, currency, period = self._parse_salary(salary_text)

            # Description snippet
            desc_elem = card.select_one("div.job-snippet")
            description = desc_elem.get_text(strip=True) if desc_elem else ""

            return {
                "source": self.source.value,
                "source_id": job_id,
                "source_url": job_url,
                "company_name": company,
                "title": title,
                "description": description,
                "location": location,
                "is_remote": self._is_remote(location),
                "salary_min": salary_min,
                "salary_max": salary_max,
                "salary_currency": currency,
                "salary_period": period,
                "raw_data": {},
            }
        except Exception as e:
            print(f"Error parsing Indeed card: {e}")
            return None

    async def parse_job_detail(self, job_url: str) -> Optional[Dict[str, Any]]:
        """Parse detailed job page."""
        async with httpx.AsyncClient(headers=self.headers, timeout=30) as client:
            try:
                response = await client.get(job_url)
                response.raise_for_status()
                soup = BeautifulSoup(response.text, "html.parser")

                # Job description
                desc_elem = soup.select_one("div#jobDescriptionText")
                description = desc_elem.get_text(strip=True) if desc_elem else ""

                return {"description": description}
            except Exception as e:
                print(f"Error parsing Indeed detail: {e}")
                return None


class WellfoundScraper(BaseScraper):
    """Scraper for Wellfound (AngelList Talent)"""

    def __init__(self):
        super().__init__()
        self.source = JobSource.WELLFOUND
        self.base_url = "https://wellfound.com"

    async def search_jobs(self, query: str, location: str = "Remote", **kwargs) -> List[Dict[str, Any]]:
        """Search jobs on Wellfound."""
        # Wellfound requires authentication and has GraphQL API
        # For now, return empty - would need API key
        await self._rate_limit()
        return []

    async def parse_job_detail(self, job_url: str) -> Optional[Dict[str, Any]]:
        return None


class YCJobsScraper(BaseScraper):
    """Scraper for Y Combinator Jobs"""

    def __init__(self):
        super().__init__()
        self.source = JobSource.YC_JOBS
        self.base_url = "https://www.ycombinator.com"

    async def search_jobs(self, query: str, location: str = "Remote", **kwargs) -> List[Dict[str, Any]]:
        """Search YC jobs."""
        jobs = []
        url = f"{self.base_url}/jobs/search"
        params = {"query": query, "remote": "true"}

        async with httpx.AsyncClient(headers=self.headers, timeout=30) as client:
            try:
                response = await client.get(url, params=params)
                response.raise_for_status()
                soup = BeautifulSoup(response.text, "html.parser")

                for card in soup.select("div.job-card"):
                    job_data = self._parse_job_card(card)
                    if job_data:
                        jobs.append(job_data)

            except Exception as e:
                print(f"Error searching YC Jobs: {e}")

        await self._rate_limit()
        return jobs

    def _parse_job_card(self, card) -> Optional[Dict[str, Any]]:
        try:
            link = card.select_one("a")
            if not link:
                return None

            job_url = urljoin(self.base_url, link.get("href", ""))
            title = card.select_one("h2").get_text(strip=True) if card.select_one("h2") else ""
            company = card.select_one(".company-name").get_text(strip=True) if card.select_one(".company-name") else ""
            location = card.select_one(".location").get_text(strip=True) if card.select_one(".location") else "Remote"

            return {
                "source": self.source.value,
                "source_id": job_url.split("/")[-1],
                "source_url": job_url,
                "company_name": company,
                "title": title,
                "location": location,
                "is_remote": True,
                "raw_data": {},
            }
        except Exception as e:
            print(f"Error parsing YC card: {e}")
            return None

    async def parse_job_detail(self, job_url: str) -> Optional[Dict[str, Any]]:
        async with httpx.AsyncClient(headers=self.headers, timeout=30) as client:
            try:
                response = await client.get(job_url)
                response.raise_for_status()
                soup = BeautifulSoup(response.text, "html.parser")

                desc = soup.select_one("div.job-description")
                return {"description": desc.get_text(strip=True) if desc else ""}
            except Exception as e:
                print(f"Error parsing YC detail: {e}")
                return None


# Scraper registry
SCRAPERS = {
    JobSource.REMOTEOK: RemoteOKScraper,
    JobSource.WEWORKREMOTELY: WeWorkRemotelyScraper,
    JobSource.LINKEDIN: LinkedInScraper,
    JobSource.INDEED: IndeedScraper,
    JobSource.WELLFOUND: WellfoundScraper,
    JobSource.YC_JOBS: YCJobsScraper,
}


async def get_scraper(source: JobSource) -> BaseScraper:
    """Get scraper instance for source."""
    scraper_class = SCRAPERS.get(source)
    if not scraper_class:
        raise ValueError(f"No scraper for source: {source}")
    return scraper_class()


async def search_all_sources(query: str, location: str = "Remote", sources: List[JobSource] = None) -> List[Dict[str, Any]]:
    """Search jobs across all sources."""
    if sources is None:
        sources = [JobSource.REMOTEOK, JobSource.WEWORKREMOTELY, JobSource.INDEED, JobSource.YC_JOBS]

    all_jobs = []
    for source in sources:
        try:
            scraper = await get_scraper(source)
            jobs = await scraper.search_jobs(query, location)
            all_jobs.extend(jobs)
            print(f"Found {len(jobs)} jobs from {source.value}")
        except Exception as e:
            print(f"Error searching {source.value}: {e}")

    return all_jobs