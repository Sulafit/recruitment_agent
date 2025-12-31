from mistralai import Mistral
from typing import List, Dict
import json
import re
from ..config import settings
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class LLMReranker:
    """
    Layer 2: LLM-based re-ranking for top candidates

    Takes top-5 candidates from Layer 1 (dual embedding matcher)
    and uses Mistral Large to:
    - Rank them from 1 (best) to 5 (weakest)
    - Provide detailed explanations for each ranking
    - Return top-3 candidates with reasoning
    """

    def __init__(self):
        """Initialize Mistral API client"""
        self.client = Mistral(api_key=settings.mistral_api_key)
        self.model = settings.mistral_model
        logger.info(f"Initialized LLMReranker with model: {self.model}")

    def rerank_candidates(
        self,
        job_description: str,
        candidates: List[Dict]
    ) -> List[Dict]:
        """
        Re-rank top-5 candidates using LLM

        Process:
        1. Format all 5 candidates into single prompt
        2. Send to Mistral API for ranking
        3. Parse JSON response with ranks 1-5
        4. Return top-3 with explanations

        Args:
            job_description: Full job description text
            candidates: List of 5 candidate dictionaries (from Layer 1)

        Returns:
            List of top-3 candidates with ranks, scores, and explanations
        """
        if not candidates:
            logger.warning("[LLM Reranker] No candidates to rerank")
            return []

        logger.info(f"[LLM Reranker] Re-ranking {len(candidates)} candidates")

        # Create comprehensive prompt with all candidates
        prompt = self._create_reranking_prompt(job_description, candidates)

        try:
            # Call Mistral API once for all candidates
            response = self.client.chat.complete(
                model=self.model,
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.3,  # Low temperature for consistent ranking
            )

            # Parse response
            content = response.choices[0].message.content
            rankings = self._parse_ranking_response(content, candidates)

            if not rankings:
                logger.warning("[LLM Reranker] Failed to parse rankings, returning Layer 1 order")
                # Fallback: return candidates in Layer 1 order with default scores
                return [
                    {
                        'candidate_id': c['id'],
                        'candidate_name': c.get('name', 'Unknown'),
                        'score': 0.8 - i * 0.1,  # Descending scores
                        'explanation': 'Ranking unavailable, ordered by embedding score',
                        'matching_skills': c.get('skills', [])[:5]
                    }
                    for i, c in enumerate(candidates[:3])
                ]

            # Return top-3 from rankings
            top_3 = rankings[:3]

            logger.info(
                f"[LLM Reranker] Re-ranked to top-3 "
                f"(ranks: {top_3[0].get('rank', 'N/A')}, "
                f"{top_3[1].get('rank', 'N/A')}, {top_3[2].get('rank', 'N/A')})"
            )

            return top_3

        except Exception as e:
            logger.error(f"[LLM Reranker] Error calling Mistral API: {e}")
            # Fallback: return candidates in Layer 1 order
            return [
                {
                    'candidate_id': c['id'],
                    'candidate_name': c.get('name', 'Unknown'),
                    'score': 0.8,
                    'explanation': f'Error during LLM ranking: {str(e)}',
                    'matching_skills': c.get('skills', [])[:5]
                }
                for c in candidates[:3]
            ]

    def _create_reranking_prompt(
        self,
        job_description: str,
        candidates: List[Dict]
    ) -> str:
        """
        Create comprehensive prompt for ranking 5 candidates

        Args:
            job_description: Full job description
            candidates: List of candidate dictionaries

        Returns:
            Formatted prompt string
        """
        prompt = f"""Вы эксперт-рекрутер с 15+ летним опытом в IT-индустрии.
У вас есть 5 предварительно отобранных кандидатов на техническую позицию.
Ваша задача: проанализировать каждого кандидата и ранжировать их от 1 (лучший) до 5 (слабейший) с детальным обоснованием.

ВАКАНСИЯ:
{job_description}

КАНДИДАТЫ:
"""

        # Add each candidate with FULL profile
        for i, candidate in enumerate(candidates, 1):
            candidate_text = self._format_candidate_for_llm(candidate)
            prompt += f"\n{'='*80}\nКАНДИДАТ {i}: {candidate.get('name', 'Неизвестно')}\n{'='*80}\n"
            prompt += candidate_text + "\n"

        prompt += """
КРИТЕРИИ ОЦЕНКИ:
- Соответствие навыков (Skills Match): насколько технические навыки соответствуют требованиям вакансии
- Релевантность опыта (Experience Relevance): релевантность и глубина опыта работы
- Уровень сеньорности (Seniority Level): соответствует ли уровень кандидата позиции
- Потенциал роста (Growth Potential): может ли кандидат расти и развиваться в этой роли

Для каждого кандидата укажите:
- Ранг (rank): число от 1 до 5, где 1 - лучший кандидат, 5 - слабейший
- Оценка (score): число от 0.0 до 1.0, где 1.0 - идеальное совпадение
- Детальное объяснение (explanation): 3-4 предложения, включающие:
  * Ключевые сильные стороны кандидата
  * Как его опыт и навыки соответствуют вакансии
  * Любые пробелы или слабые стороны
  * Общая оценка соответствия

ВАЖНО:
- Все 5 кандидатов должны быть проранжированы
- Ранги должны быть уникальными (нельзя двум кандидатам присвоить один и тот же ранг)
- Ответьте ТОЛЬКО валидным JSON, без дополнительного текста

Ответьте в JSON формате:
{
  "rankings": [
    {
      "candidate_id": "resume_id_here",
      "candidate_name": "Имя Кандидата",
      "rank": 1,
      "score": 0.92,
      "explanation": "Детальное объяснение на русском или английском языке..."
    },
    ...
  ]
}
"""

        return prompt

    def _format_candidate_for_llm(self, candidate: Dict) -> str:
        """
        Format FULL candidate profile for LLM evaluation

        Includes: name, contact, skills, work_experience (detailed!),
                 education, languages, certifications

        Args:
            candidate: Resume dictionary with all fields

        Returns:
            Formatted candidate profile string
        """
        parts = []

        # Contact information
        if candidate.get('email'):
            parts.append(f"Email: {candidate['email']}")
        if candidate.get('phone'):
            parts.append(f"Телефон: {candidate['phone']}")
        if candidate.get('location'):
            parts.append(f"Локация: {candidate['location']}")

        # Professional summary
        if candidate.get('summary'):
            parts.append(f"\nКраткое описание:\n{candidate['summary']}")

        # Skills (critical for matching)
        if candidate.get('skills'):
            skills_text = ', '.join(candidate['skills'])
            parts.append(f"\nНавыки:\n{skills_text}")

        # Years of experience
        if candidate.get('years_of_experience'):
            parts.append(f"\nОбщий опыт работы: {candidate['years_of_experience']} лет")

        # Work Experience (DETAILED from structured data)
        if candidate.get('work_experience'):
            parts.append("\nОпыт работы:")
            for exp in candidate['work_experience']:
                exp_text = f"\n  • {exp.get('position', 'Неизвестная позиция')}"
                exp_text += f" в {exp.get('company', 'Неизвестная компания')}"

                # Dates
                if exp.get('start_date') or exp.get('end_date'):
                    start = exp.get('start_date', 'Н/Д')
                    end = exp.get('end_date', 'Настоящее время')
                    exp_text += f" ({start} - {end})"

                # Duration
                if exp.get('duration'):
                    exp_text += f" — {exp['duration']}"

                # Responsibilities (up to 5 key ones)
                if exp.get('responsibilities'):
                    exp_text += "\n    Обязанности:"
                    for resp in exp['responsibilities'][:5]:
                        exp_text += f"\n      - {resp}"
                elif exp.get('description'):
                    exp_text += f"\n    {exp['description']}"

                parts.append(exp_text)
        elif candidate.get('experience'):
            # Fallback to legacy experience field
            parts.append(f"\nОпыт работы:\n{candidate['experience']}")

        # Education
        if candidate.get('education_details'):
            parts.append("\nОбразование:")
            for edu in candidate['education_details']:
                degree = edu.get('degree', '')
                field = edu.get('field_of_study', '')
                institution = edu.get('institution', 'Неизвестный ВУЗ')
                year = edu.get('graduation_year', '')

                edu_text = f"\n  • {degree}"
                if field:
                    edu_text += f" в области {field}"
                edu_text += f" — {institution}"
                if year:
                    edu_text += f" ({year})"

                parts.append(edu_text)
        elif candidate.get('education'):
            # Fallback to legacy education field
            parts.append(f"\nОбразование:\n{candidate['education']}")

        # Additional information
        if candidate.get('languages'):
            langs = ', '.join(candidate['languages'])
            parts.append(f"\nЯзыки: {langs}")

        if candidate.get('certifications'):
            certs = ', '.join(candidate['certifications'])
            parts.append(f"\nСертификаты: {certs}")

        if candidate.get('projects'):
            projects = '\n  - '.join(candidate['projects'][:3])  # Top 3 projects
            parts.append(f"\nКлючевые проекты:\n  - {projects}")

        return "\n".join(parts)

    def _parse_ranking_response(
        self,
        response_content: str,
        candidates: List[Dict]
    ) -> List[Dict]:
        """
        Parse LLM ranking response

        Args:
            response_content: Raw LLM response content
            candidates: Original candidate list (for fallback matching)

        Returns:
            List of candidates sorted by rank (1-5), with scores and explanations
        """
        try:
            # Extract JSON from response
            json_match = re.search(r'\{.*\}', response_content, re.DOTALL)
            if not json_match:
                logger.error("[LLM Reranker] No JSON found in response")
                return []

            data = json.loads(json_match.group())
            rankings = data.get('rankings', [])

            if not rankings:
                logger.error("[LLM Reranker] No rankings found in JSON")
                return []

            # Validate and enrich rankings
            for ranking in rankings:
                # Validate required fields
                if 'candidate_id' not in ranking:
                    logger.warning("[LLM Reranker] Missing candidate_id in ranking")
                    continue

                if 'rank' not in ranking:
                    logger.warning(f"[LLM Reranker] Missing rank for {ranking.get('candidate_id')}")
                    ranking['rank'] = 999  # Put at end

                if 'explanation' not in ranking or not ranking['explanation']:
                    ranking['explanation'] = "Объяснение не предоставлено"

                # Convert rank to score if score is missing
                if 'score' not in ranking or ranking['score'] is None:
                    # Formula: rank 1 → 0.95, rank 2 → 0.85, rank 3 → 0.75, etc.
                    rank = ranking.get('rank', 5)
                    ranking['score'] = max(0.5, 1.0 - (rank - 1) * 0.1)

                # Ensure score is in valid range
                ranking['score'] = max(0.0, min(1.0, float(ranking['score'])))

                # Add matching_skills if not present
                if 'matching_skills' not in ranking:
                    # Find original candidate
                    orig_candidate = next(
                        (c for c in candidates if c['id'] == ranking['candidate_id']),
                        None
                    )
                    if orig_candidate:
                        ranking['matching_skills'] = orig_candidate.get('skills', [])[:5]
                    else:
                        ranking['matching_skills'] = []

            # Sort by rank (ascending: 1, 2, 3, 4, 5)
            rankings.sort(key=lambda x: x.get('rank', 999))

            logger.info(f"[LLM Reranker] Successfully parsed {len(rankings)} rankings")

            return rankings

        except json.JSONDecodeError as e:
            logger.error(f"[LLM Reranker] JSON decode error: {e}")
            return []
        except Exception as e:
            logger.error(f"[LLM Reranker] Error parsing ranking response: {e}")
            return []
