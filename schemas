from typing import List, Optional, TypedDict
from pydantic import BaseModel, Field


class Profile(BaseModel):
    """Student profile extracted from free text."""
    education_level: Optional[str] = Field(None, description="e.g. Class 10, Class 12, UG, PG, PhD")
    course: Optional[str] = Field(None, description="e.g. B.E. Computer Science")
    state: Optional[str] = Field(None, description="Home state in India")
    category: Optional[str] = Field(None, description="General / OBC / SC / ST / EWS")
    gender: Optional[str] = None
    annual_family_income_inr: Optional[int] = None
    minority: Optional[bool] = None
    disability: Optional[bool] = None
    marks_percent: Optional[float] = None
    other: Optional[str] = Field(None, description="Anything else relevant, e.g. first-gen, sports, orphan")


class Scholarship(BaseModel):
    name: str
    provider: str = ""
    eligibility: str = ""
    benefits: str = ""
    deadline: str = ""
    url: str


class ScholarshipList(BaseModel):
    scholarships: List[Scholarship] = []


class Match(BaseModel):
    name: str
    url: str
    fit_score: int = Field(description="0-100 fit for this student")
    eligible: str = Field(description="yes | maybe | no")
    reason: str
    documents_needed: List[str] = []
    deadline: str = ""


class MatchList(BaseModel):
    matches: List[Match] = []


class AnveshanState(TypedDict, total=False):
    user_id: str
    query: str
    profile: dict
    candidates: List[dict]
    ranked: List[dict]
    answer: str
