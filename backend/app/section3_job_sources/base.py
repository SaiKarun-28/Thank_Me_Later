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
    Thoroughly strips HTML tags, decodes HTML entities (including double-encoded),
    removes ATS company intro/conclusion boilerplates, formats bullet lists,
    and normalizes whitespace.
    """
    if not raw_html or not isinstance(raw_html, str):
        return ""
    
    # 1. Unescape HTML entities first so encoded tags (e.g. &lt;div&gt;) become parseable HTML
    text = raw_html
    for _ in range(2):
        if "&" in text:
            text = html.unescape(text)
        else:
            break

    # 2. Strip script and style blocks entirely
    text = re.sub(r"<(?:script|style)[^>]*>[\s\S]*?</(?:script|style)>", "", text, flags=re.IGNORECASE)

    # 3. Strip Greenhouse / Lever generic ATS boilerplates (e.g. content-intro and content-conclusion)
    candidate = re.sub(
        r"<div[^>]*\bclass=[\"'][^\"']*content-intro[^\"']*[\"'][^>]*>[\s\S]*?</div>",
        "",
        text,
        flags=re.IGNORECASE,
    )
    candidate = re.sub(
        r"<div[^>]*\bclass=[\"'][^\"']*content-conclusion[^\"']*[\"'][^>]*>[\s\S]*?</div>",
        "",
        candidate,
        flags=re.IGNORECASE,
    )
    if len(candidate.strip()) > 100:
        text = candidate

    # 4. Convert list items to bullet points for readability
    text = re.sub(r"<li[^>]*>", "\n• ", text, flags=re.IGNORECASE)

    # 5. Convert block/header/break elements to linebreaks to prevent text smushing
    text = re.sub(r"<(?:p|div|br|h[1-6]|tr|blockquote|section|header|footer|hr)[^>]*>", "\n", text, flags=re.IGNORECASE)

    # 6. Strip all remaining HTML tags
    text = re.sub(r"<[^>]+>", " ", text)

    # 7. Final entity decode and character cleanup
    text = html.unescape(text)
    text = text.replace("\xa0", " ").replace("\u200b", "").replace("\ufeff", "")

    # 8. Normalize spacing and consecutive newlines
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n[ \t]*\n+", "\n\n", text)
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
