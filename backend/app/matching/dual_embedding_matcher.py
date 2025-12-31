import numpy as np
from typing import List, Dict
import re
from .qwen_embedding_client import QwenEmbeddingClient
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DualEmbeddingMatcher:
    """
    Layer 1: Dual embedding vector search matcher

    Uses two separate embeddings:
    1. Skills embedding (60% weight)
    2. Experience embedding (40% weight)

    Combined score = 0.6 × skills_similarity + 0.4 × experience_similarity

    Returns top-5 candidates for LLM re-ranking
    """

    def __init__(self):
        """Initialize Qwen embedding client"""
        self.embedding_client = QwenEmbeddingClient()
        logger.info("Initialized DualEmbeddingMatcher with Qwen embeddings")

    def cosine_similarity(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        """
        Calculate cosine similarity between two vectors

        Args:
            vec1: First embedding vector
            vec2: Second embedding vector

        Returns:
            Cosine similarity score (0-1)
        """
        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return float(dot_product / (norm1 * norm2))

    def _format_skills_text(self, skills: List[str]) -> str:
        """
        Format skills list into natural text for embedding

        Args:
            skills: List of skill keywords

        Returns:
            Formatted text string

        Example:
            Input: ["Python", "Django", "PostgreSQL"]
            Output: "Professional skills: Python, Django, PostgreSQL"
        """
        if not skills:
            return "No specific skills listed"

        return f"Professional skills: {', '.join(skills)}"

    def _format_experience_text(self, work_experience: List[Dict]) -> str:
        """
        Format work_experience structured data into narrative text for embedding

        Args:
            work_experience: List of WorkExperience dictionaries with
                           positions, companies, dates, responsibilities

        Returns:
            Formatted text string

        Example:
            Input: [{"position": "Senior Python Developer", "company": "TechCorp",
                    "start_date": "2020", "end_date": "2023",
                    "responsibilities": ["Led team", "Built APIs"]}]
            Output: "Work experience: Senior Python Developer at TechCorp (2020 - 2023):
                    Led team. Built APIs. | ..."
        """
        if not work_experience:
            return "No work experience listed"

        parts = []
        for exp in work_experience:
            # Build position line
            position = exp.get('position', 'Unknown Position')
            company = exp.get('company', 'Unknown Company')
            position_info = f"{position} at {company}"

            # Add dates if available
            start_date = exp.get('start_date')
            end_date = exp.get('end_date')
            if start_date or end_date:
                dates = f"({start_date or 'Unknown'} - {end_date or 'Present'})"
                position_info += f" {dates}"

            # Add duration if available
            if exp.get('duration'):
                position_info += f", {exp['duration']}"

            # Add responsibilities (limit to top 3 for brevity)
            if exp.get('responsibilities'):
                resp_text = ". ".join(exp['responsibilities'][:3])
                position_info += f": {resp_text}"
            elif exp.get('description'):
                # Fallback to description, limit length
                description = exp['description'][:200]
                position_info += f": {description}"

            parts.append(position_info)

        return "Work experience: " + " | ".join(parts)

    def _extract_job_skills(self, job_description: str) -> List[str]:
        """
        Extract skills from job description using keyword matching

        Args:
            job_description: Full job description text

        Returns:
            List of identified skill keywords
        """
        # Comprehensive skill keywords list (from old embedding_matcher.py)
        skills_keywords = [
            'python', 'java', 'javascript', 'typescript', 'c++', 'c#', 'ruby', 'go',
            'rust', 'kotlin', 'swift', 'php', 'scala', 'r', 'matlab',
            'django', 'flask', 'fastapi', 'react', 'vue', 'angular', 'node.js',
            'spring', 'express', 'nextjs', 'svelte',
            'sql', 'mongodb', 'postgresql', 'mysql', 'redis', 'elasticsearch',
            'cassandra', 'dynamodb', 'oracle',
            'docker', 'kubernetes', 'aws', 'azure', 'gcp', 'terraform', 'ansible',
            'jenkins', 'gitlab', 'github actions', 'ci/cd',
            'machine learning', 'deep learning', 'nlp', 'computer vision',
            'tensorflow', 'pytorch', 'scikit-learn', 'pandas', 'numpy',
            'data science', 'data engineering', 'big data', 'spark', 'hadoop',
            'rest api', 'graphql', 'microservices', 'kafka', 'rabbitmq',
            'linux', 'unix', 'bash', 'git', 'agile', 'scrum', 'devops'
        ]

        text_lower = job_description.lower()
        found_skills = []

        for skill in skills_keywords:
            if skill in text_lower:
                # Capitalize first letter for consistent formatting
                found_skills.append(skill.title())

        return found_skills

    def _extract_job_experience(self, job_description: str) -> str:
        """
        Extract experience requirements from job description

        Looks for sections mentioning requirements, experience, responsibilities

        Args:
            job_description: Full job description text

        Returns:
            Extracted experience text (limited to ~500 chars)
        """
        # Patterns to extract relevant sections
        patterns = [
            r'requirements?:?\s*(.*?)(?=\n\n|\Z)',
            r'qualifications?:?\s*(.*?)(?=\n\n|\Z)',
            r'experience:?\s*(.*?)(?=\n\n|\Z)',
            r'responsibilities?:?\s*(.*?)(?=\n\n|\Z)',
            r'what we.*?looking for:?\s*(.*?)(?=\n\n|\Z)',
        ]

        extracted_parts = []
        for pattern in patterns:
            match = re.search(pattern, job_description, re.IGNORECASE | re.DOTALL)
            if match:
                text = match.group(1).strip()
                # Limit each section to 300 chars
                extracted_parts.append(text[:300])

        if extracted_parts:
            combined = " ".join(extracted_parts)
            return f"Job requirements: {combined[:500]}"
        else:
            # Fallback: use first 500 chars of job description
            return f"Job requirements: {job_description[:500]}"

    def match_candidates(self, job_description: str, resumes: List[Dict]) -> List[Dict]:
        """
        Match candidates using dual embedding approach

        Process:
        1. Extract skills and experience from job description
        2. Get embeddings for job (skills + experience)
        3. For each resume:
           - Format skills and experience
           - Get embeddings
           - Calculate combined similarity: 0.6*skills + 0.4*experience
        4. Sort by combined score
        5. Return top-5 candidates

        Args:
            job_description: Full job description text
            resumes: List of resume dictionaries with parsed data

        Returns:
            List of top-5 candidate dictionaries with scores
        """
        logger.info(f"[Dual Embedding] Matching {len(resumes)} candidates")

        # Step 1: Extract job skills and experience requirements
        job_skills = self._extract_job_skills(job_description)
        job_exp_text = self._extract_job_experience(job_description)

        logger.info(f"[Dual Embedding] Extracted {len(job_skills)} skills from job")
        logger.debug(f"[Dual Embedding] Job skills: {job_skills[:10]}...")  # First 10

        # Step 2: Get embeddings for job
        job_skills_text = self._format_skills_text(job_skills)
        job_skills_emb = self.embedding_client.get_embedding(job_skills_text)
        job_exp_emb = self.embedding_client.get_embedding(job_exp_text)

        logger.info("[Dual Embedding] Got job embeddings (skills + experience)")

        # Step 3: Process each resume
        results = []
        for i, resume in enumerate(resumes):
            try:
                # Format resume skills
                resume_skills = resume.get('skills', [])
                resume_skills_text = self._format_skills_text(resume_skills)

                # Format resume experience from work_experience structured data
                resume_work_exp = resume.get('work_experience', [])
                resume_exp_text = self._format_experience_text(resume_work_exp)

                # Get embeddings for resume
                resume_skills_emb = self.embedding_client.get_embedding(resume_skills_text)
                resume_exp_emb = self.embedding_client.get_embedding(resume_exp_text)

                # Calculate similarities
                skills_sim = self.cosine_similarity(job_skills_emb, resume_skills_emb)
                exp_sim = self.cosine_similarity(job_exp_emb, resume_exp_emb)

                # Combined score: 60% skills, 40% experience
                combined_score = 0.6 * skills_sim + 0.4 * exp_sim

                # Find matching skills for transparency
                job_skills_lower = set(skill.lower() for skill in job_skills)
                resume_skills_lower = set(skill.lower() for skill in resume_skills)
                matching_skills = list(job_skills_lower.intersection(resume_skills_lower))

                results.append({
                    'candidate_id': resume['id'],
                    'candidate_name': resume.get('name', 'Unknown'),
                    'score': round(combined_score, 4),
                    'matching_skills': matching_skills,
                    # Store component scores for debugging
                    'skills_score': round(skills_sim, 4),
                    'experience_score': round(exp_sim, 4)
                })

                # Log progress every 20 resumes
                if (i + 1) % 20 == 0:
                    logger.info(f"[Dual Embedding] Processed {i + 1}/{len(resumes)} resumes")

            except Exception as e:
                logger.error(f"[Dual Embedding] Error matching resume {resume.get('id', 'unknown')}: {e}")
                continue

        # Step 4: Sort by combined score descending
        results.sort(key=lambda x: x['score'], reverse=True)

        # Step 5: Return top-5
        top_5 = results[:5]

        logger.info(
            f"[Dual Embedding] Matched {len(results)} candidates, "
            f"returning top-5 (scores: {top_5[0]['score']:.3f} - {top_5[-1]['score']:.3f})"
        )

        return top_5
