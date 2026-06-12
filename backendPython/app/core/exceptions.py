class RecommendationError(Exception):
    """Base exception for recommendation processing errors."""


class ConfigurationError(RecommendationError):
    pass


class EmbeddingError(RecommendationError):
    pass


class RepositoryError(RecommendationError):
    pass


class CallbackError(RecommendationError):
    pass
