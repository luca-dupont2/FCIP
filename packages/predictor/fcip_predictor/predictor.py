from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import joblib

from fcip_predictor.features import engineer_single

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

MODEL_DIR = Path(__file__).parent.parent / "models"


class Predictor:
    def __init__(self, model_dir: Path | str | None = None) -> None:
        self.model_dir = Path(model_dir) if model_dir else MODEL_DIR
        self._timing_model = None
        self._runtime_model = None
        self._classifier_model = None
        self._timing_version = None
        self._runtime_version = None
        self._classifier_version = None

    @classmethod
    async def from_db(cls, db: AsyncSession) -> Predictor:
        instance = cls()
        from fcip_predictor.registry import ModelRegistry
        registry = ModelRegistry(db)

        for model_type, attr, version_attr in [
            ("timing_model", "_timing_model", "_timing_version"),
            ("runtime_model", "_runtime_model", "_runtime_version"),
            ("timing_classifier_model", "_classifier_model", "_classifier_version"),
        ]:
            meta = await registry.get_active(model_type)
            if meta:
                model = instance._load_model_from_path(meta.file_path)
                if model is not None:
                    setattr(instance, attr, model)
                    setattr(instance, version_attr, meta.version)

        return instance

    def _load_model(self, name: str):
        path = self.model_dir / f"{name}.pkl"
        if not path.exists():
            return None
        try:
            return joblib.load(path)
        except Exception:
            return None

    def _load_model_from_path(self, file_path: str):
        path = Path(file_path)
        if not path.exists():
            return None
        try:
            return joblib.load(path)
        except Exception:
            return None

    @property
    def timing_model(self):
        if self._timing_model is None:
            self._timing_model = self._load_model("timing_model")
        return self._timing_model

    @property
    def runtime_model(self):
        if self._runtime_model is None:
            self._runtime_model = self._load_model("runtime_model")
        return self._runtime_model

    @property
    def classifier_model(self):
        if self._classifier_model is None:
            self._classifier_model = self._load_model("timing_classifier_model")
        return self._classifier_model

    def predict(self, features: dict) -> dict:
        result: dict = {
            "expected_wns": None,
            "expected_compile_duration": None,
            "timing_success_probability": None,
            "model_versions": {},
            "error": None,
        }

        X = engineer_single(features)

        if self.timing_model is not None:
            try:
                pred = self.timing_model.predict(X)[0]
                result["expected_wns"] = round(float(pred), 4)
                result["model_versions"]["timing"] = self._timing_version or "latest"
            except Exception as e:
                result["error"] = f"timing prediction failed: {e}"
        else:
            result["error"] = "timing model not available (run training first)"

        if self.runtime_model is not None:
            try:
                pred = self.runtime_model.predict(X)[0]
                result["expected_compile_duration"] = round(float(pred), 1)
                result["model_versions"]["runtime"] = self._runtime_version or "latest"
            except Exception as e:
                if result["error"]:
                    result["error"] += f"; runtime prediction failed: {e}"

        if self.classifier_model is not None:
            try:
                proba = self.classifier_model.predict_proba(X)
                if proba.shape[1] > 1:
                    result["timing_success_probability"] = round(float(proba[0][1]), 4)
                else:
                    result["timing_success_probability"] = round(float(proba[0][0]), 4)
                result["model_versions"]["classifier"] = self._classifier_version or "latest"
            except Exception as e:
                if result["error"]:
                    result["error"] += f"; classifier prediction failed: {e}"

        return result
