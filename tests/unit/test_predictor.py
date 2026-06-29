from __future__ import annotations

import pytest
from pathlib import Path
from unittest.mock import MagicMock

import numpy as np

from fcip_predictor.generator import SyntheticExperimentGenerator
from fcip_predictor.features import engineer_features, engineer_single, experiment_to_feature_dict
from fcip_predictor.trainer import ModelTrainer, MIN_REAL_SAMPLES, REAL_SAMPLE_WEIGHT, SYNTHETIC_SAMPLE_WEIGHT
from fcip_predictor.predictor import Predictor
from fcip_shared.exceptions import InsufficientTrainingDataError


class TestSyntheticGenerator:
    def test_generate_default(self):
        gen = SyntheticExperimentGenerator(n_samples=10, base_seed=42)
        data = gen.generate()
        assert len(data) == 10

    def test_generated_fields_present(self):
        gen = SyntheticExperimentGenerator(n_samples=5, base_seed=1)
        data = gen.generate()
        for d in data:
            assert d.device is not None
            assert d.lut > 0
            assert d.lut_available > 0
            assert d.ff > 0
            assert d.ff_available > 0
            assert d.bram >= 0
            assert d.bram_available > 0
            assert d.dsp >= 0
            assert d.dsp_available > 0
            assert d.seed >= 1
            assert d.wns is not None
            assert d.total_runtime > 0

    def test_reproducible_with_same_seed(self):
        gen1 = SyntheticExperimentGenerator(n_samples=5, base_seed=99)
        gen2 = SyntheticExperimentGenerator(n_samples=5, base_seed=99)
        d1 = gen1.generate()
        d2 = gen2.generate()
        for a, b in zip(d1, d2):
            assert a.wns == b.wns
            assert a.total_runtime == b.total_runtime
            assert a.device == b.device

    def test_different_seeds_produce_different_data(self):
        gen1 = SyntheticExperimentGenerator(n_samples=20, base_seed=1)
        gen2 = SyntheticExperimentGenerator(n_samples=20, base_seed=2)
        d1 = gen1.generate()
        d2 = gen2.generate()
        wns_vals_1 = [d.wns for d in d1]
        wns_vals_2 = [d.wns for d in d2]
        assert wns_vals_1 != wns_vals_2


class TestFeatureEngineering:
    def test_engineer_features_shape(self):
        experiments = [
            {
                "device": "xcvu9p-flgb2104-2-e",
                "lut_pct": 45.0,
                "ff_pct": 38.0,
                "bram_pct": 20.0,
                "dsp_pct": 12.0,
                "seed": 42,
                "retiming": True,
                "phys_opt": False,
                "strategy": "Performance_Explore",
            },
            {
                "device": "5CEFA7F31C6",
                "lut_pct": 80.0,
                "ff_pct": 70.0,
                "bram_pct": 60.0,
                "dsp_pct": 50.0,
                "seed": 1,
                "retiming": False,
                "phys_opt": True,
                "strategy": "default",
            },
        ]
        df = engineer_features(experiments)
        assert len(df) == 2
        assert "lut_pct" in df.columns
        assert "seed" in df.columns
        assert "retiming" in df.columns

    def test_engineer_single(self):
        exp = {
            "device": "xcvu3p-ffvc1517-2-e",
            "lut_pct": 30.0,
            "ff_pct": 25.0,
            "bram_pct": 10.0,
            "dsp_pct": 5.0,
            "seed": 7,
            "retiming": False,
            "phys_opt": False,
            "strategy": "default",
        }
        df = engineer_single(exp)
        assert len(df) == 1

    def test_unknown_device_gets_one_hot(self):
        exp = {
            "device": "some_unknown_device",
            "lut_pct": 50.0,
            "ff_pct": 40.0,
            "bram_pct": 15.0,
            "dsp_pct": 8.0,
            "seed": 1,
            "retiming": False,
            "phys_opt": False,
            "strategy": "default",
        }
        df = engineer_single(exp)
        assert "device_unknown" in df.columns
        assert df["device_unknown"].iloc[0] == 1

    def test_missing_numerics_imputed(self):
        exp = {
            "device": "xcvu9p-flgb2104-2-e",
            "lut_pct": None,
            "ff_pct": 40.0,
            "bram_pct": None,
            "dsp_pct": 8.0,
            "seed": 1,
            "retiming": False,
            "phys_opt": False,
            "strategy": "default",
        }
        df = engineer_single(exp)
        assert not df["lut_pct"].isna().any()

    def test_cross_features_present(self):
        exp = {
            "device": "xcvu9p-flgb2104-2-e",
            "lut_pct": 45.0,
            "ff_pct": 38.0,
            "bram_pct": 20.0,
            "dsp_pct": 12.0,
            "seed": 42,
            "retiming": True,
            "phys_opt": False,
            "strategy": "Performance_Explore",
        }
        df = engineer_single(exp)
        assert "util_product" in df.columns
        assert "bram_dsp_ratio" in df.columns
        assert "high_util_flag" in df.columns
        assert "strategy_perf_flag" in df.columns
        assert df["util_product"].iloc[0] == pytest.approx(45.0 * 38.0)
        assert df["high_util_flag"].iloc[0] == 0
        assert df["strategy_perf_flag"].iloc[0] == 1

    def test_high_util_flag_triggered(self):
        exp = {
            "device": "xcvu9p-flgb2104-2-e",
            "lut_pct": 80.0,
            "ff_pct": 40.0,
            "bram_pct": 20.0,
            "dsp_pct": 12.0,
            "seed": 42,
            "retiming": False,
            "phys_opt": False,
            "strategy": "default",
        }
        df = engineer_single(exp)
        assert df["high_util_flag"].iloc[0] == 1


class TestExperimentToFeatureDict:
    def test_extracts_features_from_orm(self):
        experiment = MagicMock()
        experiment.device = "xcvu9p-flgb2104-2-e"
        experiment.seed = 42
        experiment.compile_options = {"strategy": "Performance_Explore", "retiming": True, "phys_opt": False}

        report = MagicMock()
        report.lut = 45000
        report.lut_available = 100000
        report.ff = 38000
        report.ff_available = 100000
        report.bram = 200
        report.bram_available = 1000
        report.dsp = 120
        report.dsp_available = 1000

        result = experiment_to_feature_dict(experiment, report)
        assert result["device"] == "xcvu9p-flgb2104-2-e"
        assert result["seed"] == 42
        assert result["strategy"] == "Performance_Explore"
        assert result["retiming"] is True
        assert result["phys_opt"] is False
        assert result["lut_pct"] == 45.0
        assert result["ff_pct"] == 38.0
        assert result["bram_pct"] == 20.0
        assert result["dsp_pct"] == 12.0

    def test_handles_none_report(self):
        experiment = MagicMock()
        experiment.device = "xcvu9p-flgb2104-2-e"
        experiment.seed = 1
        experiment.compile_options = {}

        result = experiment_to_feature_dict(experiment, None)
        assert result["device"] == "xcvu9p-flgb2104-2-e"
        assert result["lut_pct"] == 0.0
        assert result["strategy"] == "default"


class TestModelTrainer:
    def test_train_all_succeeds(self, tmp_path):
        trainer = ModelTrainer(model_dir=tmp_path, n_synthetic=50)
        results = trainer.train_all()
        assert "timing" in results
        assert "runtime" in results
        assert "timing_classifier" in results
        for key, val in results.items():
            assert "metrics" in val or "mae" in val or "accuracy" in val or isinstance(val, dict)

    def test_pkl_files_created(self, tmp_path):
        trainer = ModelTrainer(model_dir=tmp_path, n_synthetic=20)
        trainer.train_all()
        pkl_files = list(tmp_path.glob("*.pkl"))
        assert len(pkl_files) >= 3

    def test_train_all_default_returns_synthetic(self, tmp_path):
        trainer = ModelTrainer(model_dir=tmp_path, n_synthetic=20)
        results = trainer.train_all()
        for r in results.values():
            assert r["data_source"] == "synthetic"

    def test_train_all_explicit_synthetic(self, tmp_path):
        trainer = ModelTrainer(model_dir=tmp_path, n_synthetic=20)
        results = trainer.train_all(data_source="synthetic")
        for r in results.values():
            assert r["data_source"] == "synthetic"

    def test_train_all_real_insufficient_raises(self, tmp_path):
        gen = SyntheticExperimentGenerator(n_samples=10, base_seed=42)
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
                "device": s.device, "seed": s.seed, "strategy": s.strategy,
                "retiming": s.retiming, "phys_opt": s.phys_opt,
                "lut_pct": lut_pct, "ff_pct": ff_pct, "bram_pct": bram_pct, "dsp_pct": dsp_pct,
            })
            targets_wns.append(s.wns)
            targets_runtime.append(s.total_runtime)
            targets_success.append(int(s.timing_success))

        X = engineer_features(exp_dicts)
        real_data = (X.values, np.array(targets_wns), np.array(targets_runtime), np.array(targets_success), len(targets_wns))

        trainer = ModelTrainer(model_dir=tmp_path, n_synthetic=20)
        with pytest.raises(InsufficientTrainingDataError):
            trainer.train_all(real_data=real_data, data_source="real")

    def test_train_all_real_sufficient(self, tmp_path):
        gen = SyntheticExperimentGenerator(n_samples=60, base_seed=42)
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
                "device": s.device, "seed": s.seed, "strategy": s.strategy,
                "retiming": s.retiming, "phys_opt": s.phys_opt,
                "lut_pct": lut_pct, "ff_pct": ff_pct, "bram_pct": bram_pct, "dsp_pct": dsp_pct,
            })
            targets_wns.append(s.wns)
            targets_runtime.append(s.total_runtime)
            targets_success.append(int(s.timing_success))

        X = engineer_features(exp_dicts)
        real_data = (X.values, np.array(targets_wns), np.array(targets_runtime), np.array(targets_success), len(targets_wns))

        trainer = ModelTrainer(model_dir=tmp_path, n_synthetic=20)
        results = trainer.train_all(real_data=real_data, data_source="real")
        for r in results.values():
            assert r["data_source"] == "real"

    def test_train_all_auto_mixed_when_enough_real(self, tmp_path):
        gen = SyntheticExperimentGenerator(n_samples=60, base_seed=42)
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
                "device": s.device, "seed": s.seed, "strategy": s.strategy,
                "retiming": s.retiming, "phys_opt": s.phys_opt,
                "lut_pct": lut_pct, "ff_pct": ff_pct, "bram_pct": bram_pct, "dsp_pct": dsp_pct,
            })
            targets_wns.append(s.wns)
            targets_runtime.append(s.total_runtime)
            targets_success.append(int(s.timing_success))

        X = engineer_features(exp_dicts)
        real_data = (X.values, np.array(targets_wns), np.array(targets_runtime), np.array(targets_success), len(targets_wns))

        trainer = ModelTrainer(model_dir=tmp_path, n_synthetic=20)
        results = trainer.train_all(real_data=real_data, data_source="auto")
        for r in results.values():
            assert r["data_source"] == "mixed"

    def test_train_all_auto_synthetic_when_insufficient_real(self, tmp_path):
        gen = SyntheticExperimentGenerator(n_samples=10, base_seed=42)
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
                "device": s.device, "seed": s.seed, "strategy": s.strategy,
                "retiming": s.retiming, "phys_opt": s.phys_opt,
                "lut_pct": lut_pct, "ff_pct": ff_pct, "bram_pct": bram_pct, "dsp_pct": dsp_pct,
            })
            targets_wns.append(s.wns)
            targets_runtime.append(s.total_runtime)
            targets_success.append(int(s.timing_success))

        X = engineer_features(exp_dicts)
        real_data = (X.values, np.array(targets_wns), np.array(targets_runtime), np.array(targets_success), len(targets_wns))

        trainer = ModelTrainer(model_dir=tmp_path, n_synthetic=20)
        results = trainer.train_all(real_data=real_data, data_source="auto")
        for r in results.values():
            assert r["data_source"] == "synthetic"

    def test_train_all_real_no_data_raises(self, tmp_path):
        trainer = ModelTrainer(model_dir=tmp_path, n_synthetic=20)
        with pytest.raises(InsufficientTrainingDataError):
            trainer.train_all(real_data=None, data_source="real")

    def test_sample_weights_constants(self):
        assert MIN_REAL_SAMPLES == 50
        assert REAL_SAMPLE_WEIGHT == 5.0
        assert SYNTHETIC_SAMPLE_WEIGHT == 1.0


class TestPredictor:
    def test_predict_with_trained_model(self, tmp_path):
        trainer = ModelTrainer(model_dir=tmp_path, n_synthetic=100)
        trainer.train_all()

        predictor = Predictor(model_dir=tmp_path)
        features = {
            "device": "xcvu9p-flgb2104-2-e",
            "lut_pct": 45.0,
            "ff_pct": 38.0,
            "bram_pct": 20.0,
            "dsp_pct": 12.0,
            "seed": 42,
            "retiming": True,
            "phys_opt": False,
            "strategy": "Performance_Explore",
        }
        result = predictor.predict(features)
        assert "expected_wns" in result
        assert "expected_compile_duration" in result
        assert "timing_success_probability" in result
        assert isinstance(result["expected_wns"], float)
        assert isinstance(result["expected_compile_duration"], float)
        assert 0.0 <= result["timing_success_probability"] <= 1.0

    def test_predict_returns_version_numbers(self, tmp_path):
        trainer = ModelTrainer(model_dir=tmp_path, n_synthetic=100)
        trainer.train_all()

        predictor = Predictor(model_dir=tmp_path)
        features = {
            "device": "xcvu9p-flgb2104-2-e",
            "lut_pct": 45.0,
            "ff_pct": 38.0,
            "bram_pct": 20.0,
            "dsp_pct": 12.0,
            "seed": 42,
            "retiming": True,
            "phys_opt": False,
            "strategy": "default",
        }
        result = predictor.predict(features)
        assert "model_versions" in result
        assert "timing" in result["model_versions"]

    async def test_predictor_from_db_fallback(self, tmp_path):
        trainer = ModelTrainer(model_dir=tmp_path, n_synthetic=50)
        trainer.train_all()

        mock_db = MagicMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute = MagicMock(return_value=mock_result)
        mock_db.execute.return_value = mock_result

        predictor = Predictor(model_dir=tmp_path)
        features = {
            "device": "xcvu9p-flgb2104-2-e",
            "lut_pct": 45.0,
            "ff_pct": 38.0,
            "bram_pct": 20.0,
            "dsp_pct": 12.0,
            "seed": 42,
            "retiming": True,
            "phys_opt": False,
            "strategy": "default",
        }
        result = predictor.predict(features)
        assert result.get("expected_wns") is not None or result.get("error") is not None
