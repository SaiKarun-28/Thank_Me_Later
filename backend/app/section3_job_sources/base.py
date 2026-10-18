"""
Base Source Adapter contract and text normalization utilities.
"""
from abc import ABC, abstractmethod
import html
import logging
import re
from typing import Any, Dict, List, Optional

from app.section1_foundation_and_providers.schemas.job import JobPosting, JobSourceConfig
from app.section1_foundation_and_providers.security.security import sanitize_url

logger = logging.getLogger(__name__)


def strip_html(raw_html: Optional[str]) -> str:
    """
    Strips HTML tags, decodes HTML entities, and normalizes excessive whitespace.
    """
    if not raw_html or not isinstance(raw_html, str):
        return ""
    
    # Replace common block elements with spaces to prevent word smushing
    text = re.sub(r"<(?:p|div|br|li|h[1-6]|tr)[^>]*>", "\n", raw_html, flags=re.IGNORECASE)
    # Strip all remaining HTML tags
    text = re.sub(r"<[^>]+>", " ", text)
    # Decode HTML entities (&amp;, &nbsp;, &#39;, etc.)
    text = html.unescape(text)
    # Normalize excessive newlines and spaces
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n\s*\n+", "\n\n", text)
    return text.strip()


class BaseSourceAdapter(ABC):
    """
    Abstract base class for all job board and ATS aggregators.
    """
    def __init__(self, id: str, name: str, is_keyless: bool = False, timeout: float = 10.0):
        self.id = id
        self.name = name
        self.is_keyless = is_keyless
        self.timeout = timeout

    def build_posting(
        self,
        id: str,
        title: str,
        company: str,
        apply_url: str,
        location: str = "",
        remote: bool = False,
        description: str = "",
        posted_date: Optional[str] = None,
        salary: Optional[str] = None,
    ) -> Optional[JobPosting]:
        """
        Validates the apply_url and constructs a JobPosting.
        Returns None if apply_url is invalid (drops bad links silently).
        """
        valid_url = sanitize_url(apply_url)
        if not valid_url:
            logger.debug("Skipping job '%s' from %s due to invalid apply_url: %s", title, self.name, apply_url)
            return None

        clean_title = (title or "Untitled").strip()
        clean_company = (company or "Unknown").strip()

        return JobPosting(
            id=str(id),
            title=clean_title,
            company=clean_company,
            location=(location or "").strip(),
            remote=bool(remote),
            description=strip_html(description),
            apply_url=valid_url,
            posted_date=posted_date,
            source=self.name,
            salary=salary,
        )

    @abstractmethod
    async def fetch(self, queries: List[str], config: JobSourceConfig) -> List[JobPosting]:
        """
        Fetches job postings matching given search queries and credentials.
        Returns a list of valid JobPosting objects.
        """
        pass
