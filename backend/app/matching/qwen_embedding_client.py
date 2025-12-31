from huggingface_hub import InferenceClient
import numpy as np
from typing import List
from ..config import settings
import logging
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class QwenEmbeddingClient:
    """
    Client for Qwen3-Embedding-0.6B via HuggingFace Inference API

    Uses HF Inference API for feature extraction (embeddings).
    Requires HF_TOKEN in environment variables.
    """

    def __init__(self):
        """Initialize HuggingFace Inference client"""
        try:
            self.model = "Qwen/Qwen3-Embedding-0.6B"
            # Initialize client with model - will use the new HuggingFace API automatically
            self.client = InferenceClient(
                model=self.model,
                token=settings.hf_token
            )
            logger.info(f"Initialized Qwen embedding client with model: {self.model}")
        except Exception as e:
            logger.error(f"Error initializing Qwen client: {e}")
            raise

    def get_embedding(self, text: str, max_retries: int = 3) -> np.ndarray:
        """
        Get embedding for a single text using Qwen model

        Args:
            text: Input text to embed
            max_retries: Maximum number of retry attempts for API calls

        Returns:
            numpy array of embedding vector

        Raises:
            Exception: If API call fails after all retries
        """
        if not text or not text.strip():
            logger.warning("Empty text provided for embedding")
            # Return zero vector for empty text
            return np.zeros(896)  # Qwen3-Embedding-0.6B dimension

        for attempt in range(max_retries):
            try:
                # Call HuggingFace feature extraction API
                response = self.client.feature_extraction(text=text)

                # Convert to numpy array
                embedding = np.array(response)

                # Validate embedding
                if embedding.size == 0:
                    raise ValueError("Received empty embedding from API")

                logger.debug(f"Successfully got embedding of dimension {embedding.shape}")
                return embedding

            except Exception as e:
                error_msg = str(e).lower()

                # Check for rate limit
                if "rate limit" in error_msg or "429" in error_msg:
                    if attempt < max_retries - 1:
                        wait_time = 2 ** attempt  # Exponential backoff: 1s, 2s, 4s
                        logger.warning(
                            f"Rate limit hit, retrying in {wait_time}s "
                            f"(attempt {attempt + 1}/{max_retries})"
                        )
                        time.sleep(wait_time)
                        continue
                    else:
                        logger.error("Rate limit exceeded, max retries reached")
                        raise Exception("HuggingFace API rate limit exceeded") from e

                # Check for other API errors
                elif "api" in error_msg or "inference" in error_msg:
                    if attempt < max_retries - 1:
                        wait_time = 2 ** attempt
                        logger.warning(
                            f"API error, retrying in {wait_time}s "
                            f"(attempt {attempt + 1}/{max_retries}): {e}"
                        )
                        time.sleep(wait_time)
                        continue
                    else:
                        logger.error(f"API error after {max_retries} attempts: {e}")
                        raise Exception("HuggingFace API unavailable") from e

                # For other errors, fail immediately
                else:
                    logger.error(f"Error getting embedding: {e}")
                    raise

        # Should not reach here
        raise Exception("Failed to get embedding after all retries")

    def get_embeddings_batch(self, texts: List[str], max_retries: int = 3) -> List[np.ndarray]:
        """
        Get embeddings for multiple texts

        Currently processes sequentially. Could be optimized with batch API calls.

        Args:
            texts: List of texts to embed
            max_retries: Maximum number of retry attempts per text

        Returns:
            List of numpy arrays (one embedding per text)
        """
        embeddings = []

        logger.info(f"Getting embeddings for {len(texts)} texts")

        for i, text in enumerate(texts):
            try:
                embedding = self.get_embedding(text, max_retries=max_retries)
                embeddings.append(embedding)

                if (i + 1) % 10 == 0:
                    logger.info(f"Processed {i + 1}/{len(texts)} embeddings")

            except Exception as e:
                logger.error(f"Error getting embedding for text {i}: {e}")
                # Append zero vector on error to maintain list alignment
                embeddings.append(np.zeros(896))

        logger.info(f"Successfully got {len(embeddings)} embeddings")
        return embeddings
