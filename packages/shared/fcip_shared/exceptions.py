from __future__ import annotations


class FCIPError(Exception):
    detail: str = ""

    def __init__(self, message: str = "", detail: str = "") -> None:
        self.detail = detail or message
        super().__init__(message)


class ParseError(FCIPError):
    pass


class ImportError(FCIPError):
    pass


class PredictionError(FCIPError):
    pass


class RecommendationError(FCIPError):
    pass


class NotFoundError(FCIPError):
    pass


class ValidationError(FCIPError):
    pass


class InsufficientTrainingDataError(FCIPError):
    pass
