from pydantic import BaseModel
from typing import List, Optional, Dict


class WorkExperience(BaseModel):
    """Структура для описания опыта работы"""
    position: str
    company: str
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    duration: Optional[str] = None
    description: Optional[str] = None
    responsibilities: List[str] = []


class Education(BaseModel):
    """Структура для описания образования"""
    degree: Optional[str] = None
    institution: str
    field_of_study: Optional[str] = None
    graduation_year: Optional[str] = None
    description: Optional[str] = None


class Resume(BaseModel):
    id: str
    raw_text: str

    # Основная информация
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    location: Optional[str] = None

    # Профессиональная информация
    summary: Optional[str] = None
    skills: List[str] = []
    years_of_experience: Optional[int] = None

    # Опыт работы
    work_experience: List[WorkExperience] = []
    experience: str = ""  # Оставляем для обратной совместимости

    # Образование
    education_details: List[Education] = []
    education: str = ""  # Оставляем для обратной совместимости

    # Дополнительная информация
    languages: List[str] = []
    certifications: List[str] = []
    projects: List[str] = []


class Job(BaseModel):
    id: str
    title: str
    description: str
    requirements: str
    tech_stack: List[str] = []


class MatchResult(BaseModel):
    candidate_id: str
    candidate_name: Optional[str]
    score: float
    explanation: Optional[str] = None
    matching_skills: List[str] = []


class RecommendationResponse(BaseModel):
    job_id: str
    job_title: str
    candidates: List[MatchResult]
    method: str
