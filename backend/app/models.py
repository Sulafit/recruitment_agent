from pydantic import BaseModel, field_validator
from typing import List, Optional, Dict, Union


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
    graduation_year: Optional[Union[str, int]] = None
    description: Optional[str] = None

    @field_validator('graduation_year')
    @classmethod
    def convert_year_to_string(cls, v):
        """Конвертирует год в строку, если пришло число"""
        if v is not None and isinstance(v, int):
            return str(v)
        return v


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

    @field_validator('projects', mode='before')
    @classmethod
    def convert_projects_to_strings(cls, v):
        """Конвертирует проекты из словарей в строки, если необходимо"""
        if not isinstance(v, list):
            return v

        result = []
        for item in v:
            if isinstance(item, dict):
                # Конвертируем словарь проекта в строку
                name = item.get('name', 'Unknown Project')
                description = item.get('description', '')
                if description:
                    result.append(f"{name}: {description}")
                else:
                    result.append(name)
            elif isinstance(item, str):
                result.append(item)
            else:
                result.append(str(item))

        return result


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
