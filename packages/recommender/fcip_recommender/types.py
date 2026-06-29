from __future__ import annotations

from enum import Enum
from dataclasses import dataclass


class RecommendationCategory(str, Enum):
    TIMING = "timing"
    UTILIZATION = "utilization"
    RUNTIME = "runtime"
    STRATEGY = "strategy"


class RecommendationPriority(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class Recommendation:
    rule_name: str
    category: RecommendationCategory
    priority: RecommendationPriority
    message: str
    confidence: float
