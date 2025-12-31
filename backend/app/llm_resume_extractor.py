"""
LLM-based Resume Data Extractor
Использует Mistral API для извлечения структурированных данных из резюме
"""

from mistralai import Mistral
from typing import Dict, List, Optional
import json
import re
from .config import settings
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class LLMResumeExtractor:
    """
    Класс для извлечения структурированных данных из текста резюме
    используя LLM вместо regex
    """

    def __init__(self):
        self.client = Mistral(api_key=settings.mistral_api_key)
        self.model = settings.mistral_model

    def extract_resume_data(self, resume_text: str) -> Dict:
        """
        Извлекает структурированные данные из текста резюме

        Args:
            resume_text: Текст резюме (извлеченный через OCR/PyPDF2)

        Returns:
            Dict со структурированными данными резюме
        """
        logger.info("Extracting resume data using LLM")

        prompt = self._create_extraction_prompt(resume_text)

        try:
            response = self.client.chat.complete(
                model=self.model,
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.1,  # Низкая температура для более консистентных результатов
                response_format={"type": "json_object"}
            )

            # Получаем ответ от LLM
            content = response.choices[0].message.content

            # Парсим JSON
            extracted_data = json.loads(content)

            logger.info(f"Successfully extracted data: {len(extracted_data.get('skills', []))} skills, "
                       f"{len(extracted_data.get('work_experience', []))} work experiences")

            return extracted_data

        except Exception as e:
            logger.error(f"Error extracting resume data with LLM: {e}")
            # Возвращаем пустую структуру в случае ошибки
            return self._get_empty_structure()

    def _create_extraction_prompt(self, resume_text: str) -> str:
        """
        Создает промпт для извлечения данных из резюме
        """
        return f"""You are an expert resume parser. Extract structured information from the following resume text.

Resume Text:
{resume_text[:4000]}

Extract the following information and return it as a JSON object:

{{
  "name": "Full name of the candidate",
  "email": "Email address",
  "phone": "Phone number",
  "location": "City/Country/Location",
  "summary": "Brief professional summary or objective (2-3 sentences)",
  "skills": ["List of technical and professional skills"],
  "years_of_experience": 5,
  "work_experience": [
    {{
      "position": "Job title",
      "company": "Company name",
      "start_date": "Start date (e.g., 'January 2020', '2020', '01/2020')",
      "end_date": "End date or 'Present'",
      "duration": "Duration (e.g., '2 years 3 months')",
      "description": "Brief description of the role",
      "responsibilities": ["Key responsibility 1", "Key responsibility 2"]
    }}
  ],
  "education_details": [
    {{
      "degree": "Degree type (e.g., Bachelor's, Master's)",
      "institution": "University/School name",
      "field_of_study": "Field of study/Major",
      "graduation_year": "Graduation year",
      "description": "Additional details if any"
    }}
  ],
  "languages": ["Language 1", "Language 2"],
  "certifications": ["Certification 1", "Certification 2"],
  "projects": ["Project description 1", "Project description 2"]
}}

Important instructions:
1. Extract all information that is present in the resume
2. If a field is not found, use null for strings/objects or empty array [] for lists
3. For skills, extract ALL technical skills, frameworks, tools, and technologies mentioned
4. Calculate years_of_experience based on work history (can be approximate)
5. Extract work experience in chronological order (most recent first)
6. Be thorough but concise - focus on key information
7. Support both English and Russian text
8. Return ONLY valid JSON, no additional text

Return the extracted data as a JSON object."""

    def _get_empty_structure(self) -> Dict:
        """
        Возвращает пустую структуру данных резюме
        """
        return {
            "name": None,
            "email": None,
            "phone": None,
            "location": None,
            "summary": None,
            "skills": [],
            "years_of_experience": None,
            "work_experience": [],
            "education_details": [],
            "languages": [],
            "certifications": [],
            "projects": []
        }

    def extract_with_fallback(self, resume_text: str, fallback_data: Dict) -> Dict:
        """
        Извлекает данные с использованием LLM, но использует fallback данные
        если LLM не смог извлечь определенные поля

        Args:
            resume_text: Текст резюме
            fallback_data: Данные извлеченные через regex (для обратной совместимости)

        Returns:
            Объединенные данные
        """
        llm_data = self.extract_resume_data(resume_text)

        # Объединяем данные - приоритет у LLM, но используем fallback если LLM вернул пустые значения
        merged_data = {
            "name": llm_data.get("name") or fallback_data.get("name"),
            "email": llm_data.get("email") or fallback_data.get("email"),
            "phone": llm_data.get("phone"),
            "location": llm_data.get("location"),
            "summary": llm_data.get("summary"),
            "skills": llm_data.get("skills", []) or fallback_data.get("skills", []),
            "years_of_experience": llm_data.get("years_of_experience"),
            "work_experience": llm_data.get("work_experience", []),
            "education_details": llm_data.get("education_details", []),
            "languages": llm_data.get("languages", []),
            "certifications": llm_data.get("certifications", []),
            "projects": llm_data.get("projects", []),
            # Сохраняем старые поля для обратной совместимости
            "experience": fallback_data.get("experience", ""),
            "education": fallback_data.get("education", "")
        }

        return merged_data
