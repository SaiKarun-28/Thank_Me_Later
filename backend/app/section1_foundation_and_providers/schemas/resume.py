"""
Resume and Profile Data Models.
"""
from typing import List, Optional, Literal, Dict, Any
from pydantic import BaseModel, Field


RemotePreference = Literal["remote", "hybrid", "onsite", "any"]
ExperienceLevel = Literal["intern", "fresher", "junior", "mid", "senior", "lead"]


def calculate_default_experience_level(years: float) -> ExperienceLevel:
    """Derive standard experience level from years of experience."""
    if years < 1.0:
        return "fresher"
    if years < 3.0:
        return "junior"
    if years < 6.0:
        return "mid"
    return "senior"


class TargetRole(BaseModel):
    role: str
    confidence: float = Field(default=0.8, ge=0.0, le=1.0)


class ContactInfo(BaseModel):
    email: Optional[str] = None
    phone: Optional[str] = None
    linkedin: Optional[str] = None
    github: Optional[str] = None
    website: Optional[str] = None


class ExperienceItem(BaseModel):
    company: str
    title: str
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    description: Optional[str] = None
    bullets: List[str] = Field(default_factory=list)


class EducationItem(BaseModel):
    institution: str
    degree: Optional[str] = None
    field_of_study: Optional[str] = None
    graduation_year: Optional[str] = None


class ParsedProfile(BaseModel):
    """
    Complete parsed profile extracted from resume.
    Sent back to user on /upload; never persisted.
    """
    name: str = ""
    contact: ContactInfo = Field(default_factory=ContactInfo)
    skills: List[str] = Field(default_factory=list)
    years_experience: float = 0.0
    target_roles: List[TargetRole] = Field(default_factory=list)
    past_titles: List[str] = Field(default_factory=list)
    domains: List[str] = Field(default_factory=list)
    experience: List[ExperienceItem] = Field(default_factory=list)
    projects: List[Dict[str, Any]] = Field(default_factory=list)
    education: List[EducationItem] = Field(default_factory=list)
    certifications: List[str] = Field(default_factory=list)
    raw_text: str = ""


class ConfirmedProfile(BaseModel):
    """
    Profile confirmed & edited by user in the frontend.
    """
    name: str = ""
    skills: List[str] = Field(default_factory=list)
    target_roles: List[TargetRole] = Field(default_factory=list)
    location: str = ""
    remote_preference: RemotePreference = "any"
    experience_level: ExperienceLevel = "mid"
    years_experience: float = 0.0
    certifications: List[str] = Field(default_factory=list)


class SearchProfile(BaseModel):
    """
    Privacy-preserving minimal profile sent to /jobs/search.
    Zero raw_text, zero bullets, zero PII.
    """
    target_roles: List[TargetRole] = Field(default_factory=list)
    skills: List[str] = Field(default_factory=list)
    location: str = ""
    remote_preference: RemotePreference = "any"
    experience_level: ExperienceLevel = "mid"
    years_experience: float = 0.0
