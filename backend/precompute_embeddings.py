"""
Precompute embeddings for all resumes

This script generates and caches embeddings for all resumes in advance,
making the candidate search nearly instant.

Usage:
    python -m backend.precompute_embeddings

Features:
- Processes all resumes in data/resumes directory
- Generates dual embeddings (skills + experience) for each
- Saves to data/embeddings_cache/ for fast lookup
- Shows progress and statistics
"""

import sys
import os
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from app.matching.dual_embedding_matcher import DualEmbeddingMatcher
from app.matching.embedding_cache import EmbeddingCache
from app.resume_parser import ResumeParser
from app.models import Resume
from app.config import settings
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def load_all_resumes():
    """Load and parse all resumes from backend/data/resumes directory"""
    resumes = []
    # Force correct path
    resumes_dir = "backend/data/resumes"

    if not os.path.exists(resumes_dir):
        logger.error(f"Resumes directory not found: {resumes_dir}")
        return resumes

    resume_parser = ResumeParser()

    for filename in os.listdir(resumes_dir):
        filepath = os.path.join(resumes_dir, filename)

        # Skip directories
        if os.path.isdir(filepath):
            continue

        try:
            # Parse resume
            parsed_data = resume_parser.parse_file(filepath)

            # Create Resume object
            resume = Resume(
                id=filename,
                raw_text=parsed_data['raw_text'],
                name=parsed_data.get('name'),
                email=parsed_data.get('email'),
                phone=parsed_data.get('phone'),
                location=parsed_data.get('location'),
                summary=parsed_data.get('summary'),
                skills=parsed_data.get('skills', []),
                years_of_experience=parsed_data.get('years_of_experience'),
                work_experience=parsed_data.get('work_experience', []),
                experience=parsed_data.get('experience', ''),
                education_details=parsed_data.get('education_details', []),
                education=parsed_data.get('education', ''),
                languages=parsed_data.get('languages', []),
                certifications=parsed_data.get('certifications', []),
                projects=parsed_data.get('projects', [])
            )
            resumes.append(resume)
            logger.info(f"Loaded resume: {filename}")
        except Exception as e:
            logger.error(f"Error parsing resume {filename}: {e}")

    return resumes


def precompute_all_embeddings():
    """
    Precompute embeddings for all resumes

    Process:
    1. Load all resumes from data/resumes
    2. For each resume, generate dual embeddings (skills + experience)
    3. Cache all embeddings to data/embeddings_cache/
    4. Show statistics
    """
    print("=" * 70)
    print("PRECOMPUTING EMBEDDINGS FOR ALL RESUMES")
    print("=" * 70)

    # Initialize components
    logger.info("Initializing embedding matcher...")
    matcher = DualEmbeddingMatcher()
    cache = matcher.cache

    # Load all resumes
    logger.info("Loading all resumes...")
    resumes = load_all_resumes()

    if not resumes:
        logger.error("No resumes found. Please add resumes to data/resumes directory.")
        return

    print(f"\nFound {len(resumes)} resumes to process\n")

    # Prepare texts for batch processing
    skills_texts = []
    exp_texts = []
    resume_ids = []

    for resume in resumes:
        resume_id = resume.id
        resume_ids.append(resume_id)

        # Check if already cached
        cached = cache.get(resume_id, resume.model_dump())
        if cached:
            logger.info(f"✓ {resume_id} - Already cached, skipping")
            continue

        # Format texts
        resume_skills = resume.skills or []
        resume_skills_text = matcher._format_skills_text(resume_skills)
        skills_texts.append(resume_skills_text)

        # Convert work_experience Pydantic models to dicts
        resume_work_exp = resume.work_experience or []
        resume_work_exp_dicts = [exp.model_dump() if hasattr(exp, 'model_dump') else exp for exp in resume_work_exp]
        resume_exp_text = matcher._format_experience_text(resume_work_exp_dicts)
        exp_texts.append(resume_exp_text)

    if not skills_texts:
        print("\n✓ All resumes already have cached embeddings!")
        print_cache_stats(cache)
        return

    print(f"Processing {len(skills_texts)} new resumes...\n")

    # Generate embeddings in batch (FAST!)
    logger.info(f"Generating skills embeddings for {len(skills_texts)} resumes...")
    skills_embeddings = matcher.embedding_client.get_embeddings_batch(skills_texts)

    logger.info(f"Generating experience embeddings for {len(exp_texts)} resumes...")
    exp_embeddings = matcher.embedding_client.get_embeddings_batch(exp_texts)

    # Cache all embeddings
    logger.info("Caching all embeddings...")
    cached_count = 0

    # We need to match up with resumes that weren't cached
    batch_idx = 0
    for resume in resumes:
        resume_id = resume.id

        # Skip if already cached
        cached = cache.get(resume_id, resume.model_dump())
        if cached:
            continue

        # Cache this resume's embeddings
        cache.set(
            resume_id,
            resume.model_dump(),
            skills_embeddings[batch_idx],
            exp_embeddings[batch_idx]
        )
        cached_count += 1
        print(f"✓ Cached embeddings for: {resume.name or resume_id}")

        batch_idx += 1

    print(f"\n{'=' * 70}")
    print(f"✓ Successfully precomputed embeddings for {cached_count} resumes")
    print(f"{'=' * 70}\n")

    # Show cache statistics
    print_cache_stats(cache)


def print_cache_stats(cache: EmbeddingCache):
    """Print cache statistics"""
    stats = cache.get_cache_stats()

    print("\nCACHE STATISTICS:")
    print("-" * 70)
    print(f"  Cached resumes:  {stats['cached_resumes']}")
    print(f"  Total size:      {stats['total_size_mb']} MB ({stats['total_size_bytes']:,} bytes)")
    print(f"  Cache directory: {stats['cache_dir']}")
    print("-" * 70)
    print("\n✓ Future searches will be nearly instant!\n")


if __name__ == "__main__":
    try:
        precompute_all_embeddings()
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        sys.exit(1)
