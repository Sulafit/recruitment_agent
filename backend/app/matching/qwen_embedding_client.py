from sentence_transformers import SentenceTransformer
import numpy as np
from typing import List
from ..config import settings
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class QwenEmbeddingClient:
    """
    Client for BGE-M3 embedding model via sentence-transformers

    Uses local BGE-M3 model for generating embeddings.
    Supports multilingual text and various embedding tasks.
    """

    def __init__(self):
        """Initialize BGE-M3 model"""
        try:
            self.model_name = settings.qwen_model  # Will be renamed to bge_model in config
            # Initialize sentence-transformers model
            # BGE-M3 runs locally, no API token needed
            self.model = SentenceTransformer(self.model_name)
            logger.info(f"Initialized BGE-M3 embedding model: {self.model_name}")
            logger.info(f"Model dimension: {self.model.get_sentence_embedding_dimension()}")
        except Exception as e:
            logger.error(f"Error initializing BGE-M3 model: {e}")
            raise

    def get_embedding(self, text: str, max_retries: int = 3) -> np.ndarray:
        """
        Get embedding for a single text using BGE-M3 model

        Args:
            text: Input text to embed
            max_retries: Not used (kept for backward compatibility)

        Returns:
            numpy array of embedding vector

        Raises:
            Exception: If embedding generation fails
        """
        if not text or not text.strip():
            logger.warning("Empty text provided for embedding")
            # Return zero vector for empty text
            embedding_dim = self.model.get_sentence_embedding_dimension()
            return np.zeros(embedding_dim)

        try:
            # Generate embedding using sentence-transformers
            # BGE-M3 runs locally, so no API calls or retries needed
            embedding = self.model.encode(text, normalize_embeddings=True)

            # Convert to numpy array if not already
            embedding = np.array(embedding)

            # Validate embedding
            if embedding.size == 0:
                raise ValueError("Received empty embedding from model")

            logger.debug(f"Successfully got embedding of dimension {embedding.shape}")
            return embedding

        except Exception as e:
            logger.error(f"Error getting embedding: {e}")
            raise

    def get_embeddings_batch(self, texts: List[str], max_retries: int = 3) -> List[np.ndarray]:
        """
        Get embeddings for multiple texts using BGE-M3

        Uses batch encoding for better performance.

        Args:
            texts: List of texts to embed
            max_retries: Not used (kept for backward compatibility)

        Returns:
            List of numpy arrays (one embedding per text)
        """
        logger.info(f"Getting embeddings for {len(texts)} texts")

        try:
            # Process all texts in batch for better performance
            # sentence-transformers handles batching internally
            embeddings = self.model.encode(
                texts,
                normalize_embeddings=True,
                show_progress_bar=len(texts) > 10,
                batch_size=32
            )

            # Convert to list of numpy arrays
            embeddings_list = [np.array(emb) for emb in embeddings]

            logger.info(f"Successfully got {len(embeddings_list)} embeddings")
            return embeddings_list

        except Exception as e:
            logger.error(f"Error getting batch embeddings: {e}")
            # Fallback to sequential processing on error
            logger.warning("Falling back to sequential processing")
            embeddings = []
            embedding_dim = self.model.get_sentence_embedding_dimension()

            for i, text in enumerate(texts):
                try:
                    embedding = self.get_embedding(text)
                    embeddings.append(embedding)

                    if (i + 1) % 10 == 0:
                        logger.info(f"Processed {i + 1}/{len(texts)} embeddings")

                except Exception as e:
                    logger.error(f"Error getting embedding for text {i}: {e}")
                    # Append zero vector on error to maintain list alignment
                    embeddings.append(np.zeros(embedding_dim))

            logger.info(f"Successfully got {len(embeddings)} embeddings")
            return embeddings
