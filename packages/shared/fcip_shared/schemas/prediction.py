from __future__ import annotations

from pydantic import BaseModel


class PredictRequest(BaseModel):
    experiment_id: str | None = None
    device: str | None = None
    lut_pct: float | None = None
    ff_pct: float | None = None
    bram_pct: float | None = None
    dsp_pct: float | None = None
    seed: int | None = None
    retiming: bool | None = None
    phys_opt: bool | None = None
    strategy: str | None = None


class PredictionResponse(BaseModel):
    expected_wns: float | None = None
    expected_compile_duration: float | None = None
    timing_success_probability: float | None = None
    model_versions: dict | None = None
    error: str | None = None


class ModelTrainRequest(BaseModel):
    force: bool = False
    data_source: str = "auto"


class ModelTrainResponse(BaseModel):
    status: str
    model_type: str
    version: int
    dataset_size: int
    accuracy: float | None = None
    data_source: str = "synthetic"
    is_active: bool = True
    message: str = ""


class ModelMetadataResponse(BaseModel):
    id: str
    model_type: str
    version: int
    file_path: str
    dataset_size: int | None = None
    accuracy: float | None = None
    trained_at: str
    data_source: str = "synthetic"
    is_active: bool = True

    model_config = {"from_attributes": True}
