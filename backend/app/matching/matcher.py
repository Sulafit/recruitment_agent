from typing import List, Dict
from .dual_embedding_matcher import DualEmbeddingMatcher
from .llm_reranker import LLMReranker
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Matcher:
    def __init__(self):
        self.dual_embedding_matcher = DualEmbeddingMatcher()
        self.llm_reranker = LLMReranker()

    def get_recommendations(
        self,
        job_description: str,
        resumes: List[Dict],
        method: str = "hybrid",
        top_k: int = 3
    ) -> List[Dict]:
        """
        Get top-k candidate recommendations using two-layer architecture

        New Architecture:
        - Layer 1: Dual vector search (Qwen embeddings) → Top-5
        - Layer 2: LLM re-ranking (Mistral) → Top-3

        Args:
            job_description: Job description text
            resumes: List of parsed resume dictionaries
            method: Must be "hybrid" (only supported method)
            top_k: Number of top candidates to return (default: 3)

        Returns:
            List of top candidates with scores and explanations
        """
        logger.info(f"Getting recommendations using {method} method for {len(resumes)} resumes")

        # Only hybrid method is supported in new architecture
        if method != "hybrid":
            raise ValueError(
                "Only 'hybrid' method is supported in new architecture. "
                "Legacy methods ('embedding', 'llm') have been removed."
            )

        # Two-layer matching
        results = self._dual_layer_match(job_description, resumes, top_k)
        return results

    def _dual_layer_match(
        self,
        job_description: str,
        resumes: List[Dict],
        top_k: int = 3
    ) -> List[Dict]:
        """
        Two-layer architecture for candidate matching

        Layer 1: Dual embedding vector search → Top-5
        Layer 2: LLM re-ranking → Top-3

        This approach provides:
        - Accurate matching via dual embeddings (skills 60%, experience 40%)
        - Deep analysis via LLM re-ranking
        - Detailed explanations for hiring decisions

        Args:
            job_description: Job description text
            resumes: List of all resume dictionaries
            top_k: Final number of top candidates to return (default: 3)

        Returns:
            List of top-k candidates with LLM ranks, scores, and explanations
        """
        logger.info(f"[Layer 1] Starting dual embedding search on {len(resumes)} resumes")

        # Layer 1: Get top-5 candidates via dual embedding vector search
        top_5_candidates = self.dual_embedding_matcher.match_candidates(
            job_description,
            resumes
        )  # Already returns exactly 5 candidates

        if not top_5_candidates:
            logger.warning("[Layer 1] No candidates found")
            return []

        logger.info(
            f"[Layer 1] Selected {len(top_5_candidates)} candidates "
            f"(scores: {top_5_candidates[0]['score']:.3f} - {top_5_candidates[-1]['score']:.3f})"
        )

        # Extract full resume data for Layer 2 (LLM needs complete profiles)
        candidate_ids = {c['candidate_id'] for c in top_5_candidates}
        candidates_for_reranking = [r for r in resumes if r['id'] in candidate_ids]

        # Preserve Layer 1 order for LLM input
        candidates_for_reranking.sort(
            key=lambda r: next(
                i for i, c in enumerate(top_5_candidates)
                if c['candidate_id'] == r['id']
            )
        )

        # Layer 2: LLM re-rank top-5 → top-k (default top-3)
        logger.info(f"[Layer 2] LLM re-ranking {len(candidates_for_reranking)} candidates")

        reranked_results = self.llm_reranker.rerank_candidates(
            job_description,
            candidates_for_reranking
        )

        # Return top-k (default 3)
        final_results = reranked_results[:top_k]

        if final_results:
            logger.info(
                f"[Layer 2] Final Top-{len(final_results)} "
                f"(scores: {final_results[0]['score']:.3f} - {final_results[-1]['score']:.3f})"
            )
        else:
            logger.warning("[Layer 2] No candidates returned from LLM reranking")

        logger.info(f"[Dual Layer] Complete: returning {len(final_results)} candidates")
        return final_results
