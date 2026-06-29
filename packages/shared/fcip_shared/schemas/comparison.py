from __future__ import annotations

from pydantic import BaseModel


class CompareRequest(BaseModel):
    experiment_ids: list[str]


class MetricDelta(BaseModel):
    a: float | int | None = None
    b: float | int | None = None
    delta: float | int | None = None


class CompareResponse(BaseModel):
    experiment_ids: list[str]
    deltas: dict[str, MetricDelta]
    option_diffs: dict[str, dict]
