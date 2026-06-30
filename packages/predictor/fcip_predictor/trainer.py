from __future__ import annotations

import logging
import time
from pathlib import Path

import joblib
import numpy as np
from sklearn.ensemble import RandomForestRegressor, RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, root_mean_squared_error, accuracy_score, f1_score

from fcip_predictor.generator import SyntheticExperimentGenerator
from fcip_predictor.features import engineer_features, experiment_to_feature_dict
from fcip_shared.exceptions import InsufficientTrainingDataError

MODEL_DIR = Path(__file__).parent.parent / "models"

logger = logging.getLogger(__name__)

MIN_REAL_SAMPLES = 50
REAL_SAMPLE_WEIGHT = 5.0
SYNTHETIC_SAMPLE_WEIGHT = 1.0

# Per-source weights for V2 data source differentiation
SOURCE_WEIGHTS = {
    "tracked": 1.0,       # User's own tracked builds (highest trust)
    "user_upload": 0.8,   # Imported from teammate (trusted but not own)
    "synthetic": 1.0,     # Synthetic baseline
}

def get_source_weight(source: str) -> float:
    """Get weight for a data source."""
    return SOURCE_WEIGHTS.get(source, 1.0)


class ModelTrainer:
    def __init__(self, model_dir: Path | str | None = None, n_synthetic: int = 2000) -> None:
        self.model_dir = Path(model_dir) if model_dir else MODEL_DIR
        self.model_dir.mkdir(parents=True, exist_ok=True)
        self.n_synthetic = n_synthetic

    def train_all(self, real_data=None, data_source: str = "auto") -> dict:
        if data_source == "synthetic":
            return self._train_synthetic_only()

        if data_source == "real":
            if real_data is None:
                raise InsufficientTrainingDataError(
                    "db_session required for real data training",
                    detail="db_session required for real data training",
                )
            # real_data now has 6 elements: X, y_wns, y_runtime, y_success, count, sources
            if len(real_data) == 6:
                X_real, y_wns_real, y_runtime_real, y_success_real, real_count, sources = real_data
            else:
                # Backward compatibility
                X_real, y_wns_real, y_runtime_real, y_success_real, real_count = real_data
                sources = np.full(real_count, "tracked")
            if real_count < MIN_REAL_SAMPLES:
                raise InsufficientTrainingDataError(
                    f"Insufficient real experiments for training. Have {real_count}, need {MIN_REAL_SAMPLES}.",
                    detail=f"Insufficient real experiments for training. Have {real_count}, need {MIN_REAL_SAMPLES}.",
                )
            return self._train_real_only(X_real, y_wns_real, y_runtime_real, y_success_real, sources)

        if real_data is not None:
            if len(real_data) == 6:
                X_real, y_wns_real, y_runtime_real, y_success_real, real_count, sources = real_data
            else:
                X_real, y_wns_real, y_runtime_real, y_success_real, real_count = real_data
                sources = np.full(real_count, "tracked")
            if real_count >= MIN_REAL_SAMPLES:
                return self._train_mixed(X_real, y_wns_real, y_runtime_real, y_success_real, real_count, sources)
            logger.info(
                "only %d real experiments (need %d), using synthetic data",
                real_count, MIN_REAL_SAMPLES,
            )

        return self._train_synthetic_only()

    def _train_synthetic_only(self) -> dict:
        X, y_wns, y_runtime, y_success = self._generate_synthetic_data()
        results = {}
        results["timing"] = self._train_regressor(X, y_wns, "timing_model", "WNS")
        results["runtime"] = self._train_regressor(X, y_runtime, "runtime_model", "Runtime")
        results["timing_classifier"] = self._train_classifier(X, y_success, "timing_classifier_model", "Timing Success")
        for r in results.values():
            r["data_source"] = "synthetic"
        return results

    def _train_real_only(self, X_real, y_wns, y_runtime, y_success, sources) -> dict:
        results = {}
        weights = np.array([get_source_weight(s) for s in sources])
        results["timing"] = self._train_regressor(X_real, y_wns, "timing_model", "WNS", sample_weight=weights)
        results["runtime"] = self._train_regressor(X_real, y_runtime, "runtime_model", "Runtime", sample_weight=weights)
        results["timing_classifier"] = self._train_classifier(X_real, y_success, "timing_classifier_model", "Timing Success", sample_weight=weights)
        for r in results.values():
            r["data_source"] = "real"
        return results

    def _train_mixed(self, X_real, y_wns_real, y_runtime_real, y_success_real, real_count, sources) -> dict:
        X_synth, y_wns_synth, y_runtime_synth, y_success_synth = self._generate_synthetic_data()
        synth_count = len(y_wns_synth)

        X_combined = np.vstack([X_real, X_synth])
        y_wns = np.concatenate([y_wns_real, y_wns_synth])
        y_runtime = np.concatenate([y_runtime_real, y_runtime_synth])
        y_success = np.concatenate([y_success_real, y_success_synth])

        real_weights = np.array([get_source_weight(s) for s in sources])
        synth_weights = np.full(synth_count, SYNTHETIC_SAMPLE_WEIGHT)
        weights = np.concatenate([real_weights, synth_weights])

        results = {}
        results["timing"] = self._train_regressor(X_combined, y_wns, "timing_model", "WNS", sample_weight=weights)
        results["runtime"] = self._train_regressor(X_combined, y_runtime, "runtime_model", "Runtime", sample_weight=weights)
        results["timing_classifier"] = self._train_classifier(X_combined, y_success, "timing_classifier_model", "Timing Success", sample_weight=weights)
        for r in results.values():
            r["data_source"] = "mixed"
        return results

    def _generate_synthetic_data(self):
        gen = SyntheticExperimentGenerator(n_samples=self.n_synthetic)
        syn_data = gen.generate()

        exp_dicts = []
        targets_wns = []
        targets_runtime = []
        targets_success = []

        for s in syn_data:
            lut_pct = (s.lut / s.lut_available * 100) if s.lut_available else 0
            ff_pct = (s.ff / s.ff_available * 100) if s.ff_available else 0
            bram_pct = (s.bram / s.bram_available * 100) if s.bram_available else 0
            dsp_pct = (s.dsp / s.dsp_available * 100) if s.dsp_available else 0

            exp_dicts.append({
                "device": s.device,
                "seed": s.seed,
                "strategy": s.strategy,
                "retiming": s.retiming,
                "phys_opt": s.phys_opt,
                "lut_pct": lut_pct,
                "ff_pct": ff_pct,
                "bram_pct": bram_pct,
                "dsp_pct": dsp_pct,
            })
            targets_wns.append(s.wns)
            targets_runtime.append(s.total_runtime)
            targets_success.append(int(s.timing_success))

        X = engineer_features(exp_dicts)
        return X.values, np.array(targets_wns), np.array(targets_runtime), np.array(targets_success)

    def _train_regressor(self, X, y, model_name: str, target_name: str, sample_weight: np.ndarray | None = None) -> dict:
        start = time.time()
        X_train, X_test, y_train, y_test, sw_train, _ = self._split_with_weights(
            X, y, sample_weight
        )

        model = RandomForestRegressor(n_estimators=100, max_depth=15, random_state=42, n_jobs=-1)
        if sw_train is not None:
            model.fit(X_train, y_train, sample_weight=sw_train)
        else:
            model.fit(X_train, y_train)

        y_pred = model.predict(X_test)
        mae = mean_absolute_error(y_test, y_pred)
        rmse = root_mean_squared_error(y_test, y_pred)
        duration = time.time() - start

        path = self.model_dir / f"{model_name}.pkl"
        joblib.dump(model, path)

        existing_versions = list(self.model_dir.glob(f"{model_name}_v*.pkl"))
        version = len(existing_versions) + 1
        versioned_path = self.model_dir / f"{model_name}_v{version}.pkl"
        joblib.dump(model, versioned_path)

        return {
            "model_type": model_name,
            "version": version,
            "dataset_size": len(y),
            "accuracy": rmse,
            "metrics": {"mae": mae, "rmse": rmse},
            "duration": duration,
            "file_path": str(path),
        }

    def _train_classifier(self, X, y, model_name: str, target_name: str, sample_weight: np.ndarray | None = None) -> dict:
        start = time.time()
        X_train, X_test, y_train, y_test, sw_train, _ = self._split_with_weights(
            X, y, sample_weight
        )

        model = RandomForestClassifier(n_estimators=100, max_depth=15, random_state=42, n_jobs=-1)
        if sw_train is not None:
            model.fit(X_train, y_train, sample_weight=sw_train)
        else:
            model.fit(X_train, y_train)

        y_pred = model.predict(X_test)
        acc = accuracy_score(y_test, y_pred)
        f1 = f1_score(y_test, y_pred, average="weighted")
        duration = time.time() - start

        path = self.model_dir / f"{model_name}.pkl"
        joblib.dump(model, path)

        existing_versions = list(self.model_dir.glob(f"{model_name}_v*.pkl"))
        version = len(existing_versions) + 1
        versioned_path = self.model_dir / f"{model_name}_v{version}.pkl"
        joblib.dump(model, versioned_path)

        return {
            "model_type": model_name,
            "version": version,
            "dataset_size": len(y),
            "accuracy": acc,
            "metrics": {"accuracy": acc, "f1": f1},
            "duration": duration,
            "file_path": str(path),
        }

    @staticmethod
    def _split_with_weights(X, y, sample_weight=None):
        if sample_weight is not None:
            X_train, X_test, y_train, y_test, sw_train, sw_test = train_test_split(
                X, y, sample_weight, test_size=0.2, random_state=42
            )
            return X_train, X_test, y_train, y_test, sw_train, sw_test
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42
        )
        return X_train, X_test, y_train, y_test, None, None
