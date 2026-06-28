from math import isclose

from app.core.config import settings


class TasteVectorService:
    def __init__(self, review_weight: float = 0.6, taste_weight: float = 0.4):
        if review_weight < 0 or taste_weight < 0:
            raise ValueError("taste vector weights must be non-negative.")
        if not isclose(review_weight + taste_weight, 1.0):
            raise ValueError("taste vector weights must sum to 1.")

        self.review_weight = review_weight
        self.taste_weight = taste_weight

    def build_query_vector(
        self,
        review_embedding: list[float],
        reviewed_album_embeddings: list[list[float]],
    ) -> list[float]:
        
        self._validate_vector(review_embedding)

        if not reviewed_album_embeddings:
            return review_embedding

        for vector in reviewed_album_embeddings:
            self._validate_vector(vector)

        taste_vector = self._mean_vector(reviewed_album_embeddings)
        
        return [
            review_value * self.review_weight + taste_value * self.taste_weight
            for review_value, taste_value in zip(review_embedding, taste_vector)
        ]

    def _mean_vector(self, vectors: list[list[float]]) -> list[float]:
        vector_count = len(vectors)
        return [
            sum(values) / vector_count
            for values in zip(*vectors)
        ]

    def _validate_vector(self, vector: list[float]) -> None:
        if len(vector) != settings.EMBEDDING_DIMENSIONS:
            raise ValueError("embedding has invalid dimensions.")
