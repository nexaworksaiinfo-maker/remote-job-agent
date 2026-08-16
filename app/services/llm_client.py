"""Unified LLM Client - Supports Ollama (primary) and OpenAI (fallback)."""

import asyncio
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

import httpx
from openai import AsyncOpenAI

from app.core.config import settings


@dataclass
class LLMResponse:
    """Standardized LLM response."""
    content: str
    model: str
    usage: Optional[Dict[str, int]] = None


class LLMClient:
    """Unified client for Ollama and OpenAI."""
    
    def __init__(self):
        self._ollama_base_url = settings.OLLAMA_BASE_URL
        self._ollama_model = settings.OLLAMA_MODEL
        self._ollama_embedding_model = settings.OLLAMA_EMBEDDING_MODEL
        self._openai_client: Optional[AsyncOpenAI] = None
        
    @property
    def openai_client(self) -> Optional[AsyncOpenAI]:
        """Lazy-load OpenAI client."""
        if self._openai_client is None and settings.OPENAI_API_KEY:
            self._openai_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        return self._openai_client
    
    async def _ollama_chat(
        self,
        messages: List[Dict[str, str]],
        model: str = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> LLMResponse:
        """Call Ollama chat API."""
        model = model or self._ollama_model
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{self._ollama_base_url}/chat/completions",
                json={
                    "model": model,
                    "messages": messages,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                    "stream": False,
                }
            )
            response.raise_for_status()
            data = response.json()
            return LLMResponse(
                content=data["choices"][0]["message"]["content"],
                model=data.get("model", model),
                usage=data.get("usage"),
            )
    
    async def _ollama_embeddings(
        self,
        texts: List[str],
        model: str = None,
    ) -> List[List[float]]:
        """Call Ollama embeddings API."""
        model = model or self._ollama_embedding_model
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{self._ollama_base_url}/embeddings",
                json={
                    "model": model,
                    "input": texts,
                }
            )
            response.raise_for_status()
            data = response.json()
            return [item["embedding"] for item in data["data"]]
    
    async def _openai_chat(
        self,
        messages: List[Dict[str, str]],
        model: str = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> LLMResponse:
        """Call OpenAI chat API."""
        if not self.openai_client:
            raise RuntimeError("OpenAI client not available")
        
        model = model or settings.OPENAI_MODEL
        response = await self.openai_client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return LLMResponse(
            content=response.choices[0].message.content,
            model=response.model,
            usage={
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens,
            } if response.usage else None,
        )
    
    async def _openai_embeddings(
        self,
        texts: List[str],
        model: str = None,
    ) -> List[List[float]]:
        """Call OpenAI embeddings API."""
        if not self.openai_client:
            raise RuntimeError("OpenAI client not available")
        
        model = model or settings.OPENAI_EMBEDDING_MODEL
        response = await self.openai_client.embeddings.create(
            model=model,
            input=texts,
        )
        return [item.embedding for item in response.data]
    
    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: str = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> str:
        """
        Get chat completion - tries Ollama first, falls back to OpenAI.
        
        Args:
            messages: List of {"role": "user|system|assistant", "content": "..."}
            model: Model name (uses default if not specified)
            temperature: Sampling temperature
            max_tokens: Maximum tokens in response
            
        Returns:
            Generated text content
        """
        # Try Ollama first (free, local)
        if settings.USE_OLLAMA_FOR_CHAT:
            try:
                response = await self._ollama_chat(messages, model, temperature, max_tokens)
                return response.content
            except Exception as e:
                print(f"Ollama chat failed: {e}, trying OpenAI...")
        
        # Fallback to OpenAI
        if self.openai_client:
            try:
                response = await self._openai_chat(messages, model, temperature, max_tokens)
                return response.content
            except Exception as e:
                print(f"OpenAI chat failed: {e}")
        
        raise RuntimeError("No LLM available - both Ollama and OpenAI failed")
    
    async def generate_cover_letter(
        self,
        job_description: str,
        profile_summary: str,
        skills: List[str],
        company_name: str,
        role_title: str,
    ) -> str:
        """Generate a tailored cover letter."""
        prompt = f"""Write a compelling, personalized cover letter for this job application.

Job: {role_title} at {company_name}
Job Description: {job_description[:2500]}

Candidate Profile:
{profile_summary}

Key Skills: {', '.join(skills[:12])}

Requirements:
- Professional, confident tone
- 3-4 paragraphs maximum
- Reference specific job requirements
- Highlight relevant experience
- No generic filler
- End with call to action

Cover Letter:"""
        
        messages = [
            {"role": "system", "content": "You are an expert career coach writing tailored cover letters. Be specific, concise, and compelling."},
            {"role": "user", "content": prompt}
        ]
        
        return await self.chat_completion(messages, temperature=0.7, max_tokens=1000)
    
    async def generate_application_answers(
        self,
        questions: List[str],
        profile_summary: str,
        skills: List[str],
        experience_years: int,
    ) -> Dict[str, str]:
        """Generate answers to application questions."""
        prompt = f"""Answer these job application questions based on the candidate profile.

Candidate: {experience_years} years experience
Profile: {profile_summary}
Skills: {', '.join(skills[:15])}

Questions:
{chr(10).join(f"{i+1}. {q}" for i, q in enumerate(questions))}

Provide concise, professional answers (2-4 sentences each). Be specific with examples where possible.

Answers:"""
        
        messages = [
            {"role": "system", "content": "You are an expert job applicant. Answer application questions professionally and specifically."},
            {"role": "user", "content": prompt}
        ]
        
        response = await self.chat_completion(messages, temperature=0.7, max_tokens=1500)
        
        # Parse numbered answers
        answers = {}
        for i, q in enumerate(questions):
            # Simple extraction - in practice you'd want better parsing
            answers[q] = response
        
        return answers
    
    async def extract_job_details(
        self,
        job_html: str,
    ) -> Dict[str, Any]:
        """Extract structured job details from HTML."""
        prompt = f"""Extract structured job details from this job posting HTML.

Return JSON with these fields:
- title: Job title
- company: Company name
- location: Location (city, state, country or "Remote")
- is_remote: true/false
- description: Full job description (cleaned)
- requirements: List of required qualifications
- preferred_skills: List of preferred/nice-to-have skills
- tech_stack: List of technologies mentioned
- experience_level: entry/junior/mid/senior/lead/principal/director/vp/c_level
- salary_min: Minimum salary (number, annual USD) or null
- salary_max: Maximum salary (number, annual USD) or null
- visa_sponsorship: true/false/null
- employment_type: full-time/part-time/contract/internship
- posted_date: ISO date string or null

HTML:
{job_html[:8000]}

JSON:"""
        
        messages = [
            {"role": "system", "content": "You are a job data extraction expert. Return only valid JSON."},
            {"role": "user", "content": prompt}
        ]
        
        response = await self.chat_completion(messages, temperature=0.1, max_tokens=2000)
        
        # Parse JSON from response
        import json
        try:
            # Find JSON in response
            start = response.find("{")
            end = response.rfind("}") + 1
            if start >= 0 and end > start:
                return json.loads(response[start:end])
        except Exception as e:
            print(f"Failed to parse job extraction: {e}")
        
        return {}
    
    async def get_embeddings(
        self,
        texts: List[str],
        model: str = None,
    ) -> List[List[float]]:
        """
        Get embeddings for texts - tries Ollama first, then OpenAI, then local.
        
        Args:
            texts: List of texts to embed
            model: Model name (uses default if not specified)
            
        Returns:
            List of embedding vectors
        """
        # Try Ollama first
        if settings.USE_OLLAMA_FOR_EMBEDDINGS:
            try:
                return await self._ollama_embeddings(texts, model)
            except Exception as e:
                print(f"Ollama embeddings failed: {e}, trying OpenAI...")
        
        # Try OpenAI
        if self.openai_client:
            try:
                return await self._openai_embeddings(texts, model)
            except Exception as e:
                print(f"OpenAI embeddings failed: {e}")
        
        # Return zero vectors as last resort
        return [[0.0] * 1536] * len(texts)


# Global client instance
llm_client = LLMClient()