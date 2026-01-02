import os
import json
import hashlib
import numpy as np
from typing import Optional, Dict
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class EmbeddingCache:
    """
    Cache for resume embeddings to avoid recomputing them on every request

    Cache structure:
    - Stores embeddings in data/embeddings_cache/{resume_id}.json
    - Each cache file contains:
      * resume_id
      * content_hash (hash of resume text to detect changes)
      * skills_embedding (as list)
      * experience_embedding (as list)
      * timestamp
    """

    def __init__(self, cache_dir: str = "backend/data/embeddings_cache"):
        """
        Initialize embedding cache

        Args:
            cache_dir: Directory to store cached embeddings
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Initialized EmbeddingCache at {self.cache_dir}")

    def _get_cache_path(self, resume_id: str) -> Path:
        """Get cache file path for a resume"""
        # Sanitize resume_id for filename
        safe_id = resume_id.replace('/', '_').replace('\\', '_')
        return self.cache_dir / f"{safe_id}.json"

    def _compute_content_hash(self, resume_data: Dict) -> str:
        """
        Compute hash of resume content to detect changes

        Uses: skills + work_experience for hash (these are used for embeddings)

        Args:
            resume_data: Resume dictionary

        Returns:
            SHA256 hash of relevant content
        """
        # Extract fields used for embeddings
        skills = resume_data.get('skills', [])
        work_exp = resume_data.get('work_experience', [])

        # Create stable string representation
        content = json.dumps({
            'skills': sorted(skills),  # Sort for stability
            'work_experience': work_exp
        }, sort_keys=True)

        # Compute hash
        return hashlib.sha256(content.encode()).hexdigest()

    def get(self, resume_id: str, resume_data: Dict) -> Optional[Dict[str, np.ndarray]]:
        """
        Get cached embeddings for a resume

        Returns None if:
        - Cache doesn't exist
        - Resume content has changed (hash mismatch)

        Args:
            resume_id: Resume identifier
            resume_data: Current resume data (for hash comparison)

        Returns:
            Dict with 'skills_embedding' and 'experience_embedding' as numpy arrays,
            or None if cache invalid/missing
        """
        cache_path = self._get_cache_path(resume_id)

        if not cache_path.exists():
            logger.debug(f"No cache found for {resume_id}")
            return None

        try:
            with open(cache_path, 'r') as f:
                cache_data = json.load(f)

            # Verify content hasn't changed
            current_hash = self._compute_content_hash(resume_data)
            cached_hash = cache_data.get('content_hash')

            if current_hash != cached_hash:
                logger.info(f"Cache invalid for {resume_id} (content changed)")
                return None

            # Load embeddings
            skills_emb = np.array(cache_data['skills_embedding'])
            exp_emb = np.array(cache_data['experience_embedding'])

            logger.debug(f"Cache hit for {resume_id}")

            return {
                'skills_embedding': skills_emb,
                'experience_embedding': exp_emb
            }

        except Exception as e:
            logger.warning(f"Error reading cache for {resume_id}: {e}")
            return None

    def set(
        self,
        resume_id: str,
        resume_data: Dict,
        skills_embedding: np.ndarray,
        experience_embedding: np.ndarray
    ):
        """
        Cache embeddings for a resume

        Args:
            resume_id: Resume identifier
            resume_data: Resume data (for hash computation)
            skills_embedding: Skills embedding vector
            experience_embedding: Experience embedding vector
        """
        cache_path = self._get_cache_path(resume_id)

        try:
            cache_data = {
                'resume_id': resume_id,
                'content_hash': self._compute_content_hash(resume_data),
                'skills_embedding': skills_embedding.tolist(),
                'experience_embedding': experience_embedding.tolist(),
                'embedding_dim': len(skills_embedding),
                'timestamp': __import__('time').time()
            }

            with open(cache_path, 'w') as f:
                json.dump(cache_data, f)

            logger.debug(f"Cached embeddings for {resume_id}")

        except Exception as e:
            logger.warning(f"Error caching embeddings for {resume_id}: {e}")

    def clear(self, resume_id: Optional[str] = None):
        """
        Clear cache

        Args:
            resume_id: If provided, clear only this resume's cache.
                      If None, clear all cache.
        """
        if resume_id:
            cache_path = self._get_cache_path(resume_id)
            if cache_path.exists():
                cache_path.unlink()
                logger.info(f"Cleared cache for {resume_id}")
        else:
            # Clear all cache files
            for cache_file in self.cache_dir.glob("*.json"):
                cache_file.unlink()
            logger.info("Cleared all embedding cache")

    def get_cache_stats(self) -> Dict:
        """
        Get cache statistics

        Returns:
            Dict with cache stats (count, total size, etc.)
        """
        cache_files = list(self.cache_dir.glob("*.json"))
        total_size = sum(f.stat().st_size for f in cache_files)

        return {
            'cached_resumes': len(cache_files),
            'total_size_bytes': total_size,
            'total_size_mb': round(total_size / (1024 * 1024), 2),
            'cache_dir': str(self.cache_dir)
        }
