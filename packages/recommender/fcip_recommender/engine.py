from __future__ import annotations

from fcip_recommender.rules import RULES, Rule
from fcip_recommender.types import Recommendation, RecommendationPriority


PRIORITY_ORDER = {
    RecommendationPriority.HIGH: 0,
    RecommendationPriority.MEDIUM: 1,
    RecommendationPriority.LOW: 2,
}


class RecommendationEngine:
    def __init__(self, rules: list[Rule] | None = None) -> None:
        self.rules = rules or RULES

    def evaluate(self, experiment, reports, project_experiments=None) -> list[Recommendation]:
        report = reports[0] if reports else None

        recommendations: list[Recommendation] = []
        for rule in self.rules:
            rec = rule.evaluate(experiment, report, project_experiments)
            if rec is not None:
                recommendations.append(rec)

        recommendations.sort(key=lambda r: PRIORITY_ORDER.get(r.priority, 99))
        return recommendations
