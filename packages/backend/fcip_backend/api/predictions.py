from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from fcip_shared.schemas.prediction import PredictRequest, PredictionResponse, ModelTrainRequest
from fcip_shared.exceptions import InsufficientTrainingDataError
from fcip_shared.models.experiment import Experiment
from fcip_shared.models.report import Report
from fcip_shared.models.model_metadata import ModelMetadata
from fcip_backend.api.deps import get_db

router = APIRouter()


@router.post("", response_model=PredictionResponse)
async def predict(body: PredictRequest, db: AsyncSession = Depends(get_db)):
    try:
        from fcip_predictor.predictor import Predictor
        predictor = await Predictor.from_db(db)
    except Exception:
        try:
            from fcip_predictor.predictor import Predictor
            predictor = Predictor()
        except Exception as e:
            return PredictionResponse(error=f"prediction engine unavailable: {e}")

    features: dict = {}

    if body.experiment_id:
        try:
            eid = uuid.UUID(body.experiment_id)
        except ValueError:
            return PredictionResponse(error=f"invalid experiment_id: {body.experiment_id}")

        exp_result = await db.execute(select(Experiment).where(Experiment.id == eid))
        exp = exp_result.scalar_one_or_none()
        if not exp:
            return PredictionResponse(error=f"experiment {body.experiment_id} not found")

        rpt_result = await db.execute(select(Report).where(Report.experiment_id == eid))
        rpt = rpt_result.scalars().first()

        features["device"] = exp.device or "unknown"
        features["seed"] = exp.seed or 1
        opts = exp.compile_options or {}
        features["retiming"] = opts.get("retiming", False)
        features["phys_opt"] = opts.get("phys_opt", False)
        features["strategy"] = opts.get("strategy", "default")

        if rpt:
            features["lut_pct"] = (rpt.lut / rpt.lut_available * 100) if rpt.lut and rpt.lut_available else None
            features["ff_pct"] = (rpt.ff / rpt.ff_available * 100) if rpt.ff and rpt.ff_available else None
            features["bram_pct"] = (rpt.bram / rpt.bram_available * 100) if rpt.bram and rpt.bram_available else None
            features["dsp_pct"] = (rpt.dsp / rpt.dsp_available * 100) if rpt.dsp and rpt.dsp_available else None
    else:
        features = {
            "device": body.device or "unknown",
            "seed": body.seed or 1,
            "retiming": body.retiming or False,
            "phys_opt": body.phys_opt or False,
            "strategy": body.strategy or "default",
            "lut_pct": body.lut_pct,
            "ff_pct": body.ff_pct,
            "bram_pct": body.bram_pct,
            "dsp_pct": body.dsp_pct,
        }

    result = predictor.predict(features)
    return PredictionResponse(
        expected_wns=result.get("expected_wns"),
        expected_compile_duration=result.get("expected_compile_duration"),
        timing_success_probability=result.get("timing_success_probability"),
        model_versions=result.get("model_versions"),
        error=result.get("error"),
    )


async def _extract_real_training_data(db: AsyncSession):
    from fcip_predictor.features import engineer_features, experiment_to_feature_dict

    result = await db.execute(
        select(Experiment)
        .where(Experiment.source == "tracked")
        .where(Experiment.status.in_(["success", "failed"]))
        .options(selectinload(Experiment.reports))
    )
    experiments = result.scalars().all()

    exp_dicts = []
    targets_wns = []
    targets_runtime = []
    targets_success = []

    for exp in experiments:
        report = exp.reports[0] if exp.reports else None
        if report is None:
            continue

        fdict = experiment_to_feature_dict(exp, report)
        exp_dicts.append(fdict)

        wns = report.wns if report.wns is not None else 0.0
        targets_wns.append(wns)

        runtime = report.total_runtime if report.total_runtime is not None else 0.0
        targets_runtime.append(runtime)

        targets_success.append(1 if wns >= 0 else 0)

    if not exp_dicts:
        return None

    import numpy as np
    X = engineer_features(exp_dicts)
    return (X.values, np.array(targets_wns), np.array(targets_runtime), np.array(targets_success), len(exp_dicts))


@router.post("/train", status_code=202)
async def train_models(body: ModelTrainRequest = ModelTrainRequest(), db: AsyncSession = Depends(get_db)):
    try:
        from fcip_predictor.trainer import ModelTrainer
        from fcip_predictor.registry import ModelRegistry

        real_data = None
        if body.data_source in ("auto", "real"):
            real_data = await _extract_real_training_data(db)

        trainer = ModelTrainer()
        results = trainer.train_all(real_data=real_data, data_source=body.data_source)

        registry = ModelRegistry(db)
        for model_name, result in results.items():
            await registry.deactivate_previous(result["model_type"])
            await registry.register(
                model_type=result["model_type"],
                version=result["version"],
                file_path=result["file_path"],
                dataset_size=result["dataset_size"],
                accuracy=result["accuracy"],
                training_duration=result["duration"],
                hyperparams={"n_estimators": 100, "max_depth": 15},
                data_source=result.get("data_source", "synthetic"),
            )

        await db.flush()
        return {"status": "trained", "results": results}
    except InsufficientTrainingDataError:
        raise
    except Exception as e:
        return {"status": "failed", "error": str(e)}


@router.get("/models")
async def list_models(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(ModelMetadata).order_by(ModelMetadata.trained_at.desc())
    )
    models = result.scalars().all()
    return [
        {
            "id": str(m.id),
            "model_type": m.model_type,
            "version": m.version,
            "file_path": m.file_path,
            "dataset_size": m.dataset_size,
            "accuracy": m.accuracy,
            "trained_at": m.trained_at.isoformat() if m.trained_at else None,
            "data_source": m.data_source,
            "is_active": m.is_active,
        }
        for m in models
    ]


@router.get("/retrain-status")
async def retrain_status(db: AsyncSession = Depends(get_db)):
    from fcip_shared.config import get_settings

    settings = get_settings()
    new_count = await _count_new_tracked_experiments(db)
    threshold = settings.MODEL_RETRAIN_THRESHOLD

    return {
        "should_retrain": new_count >= threshold,
        "new_experiments_count": new_count,
        "threshold": threshold,
    }


async def _count_new_tracked_experiments(db: AsyncSession) -> int:
    latest_trained = await db.execute(
        select(func.max(ModelMetadata.trained_at)).where(ModelMetadata.is_active == True)
    )
    last_trained_at = latest_trained.scalar()

    count_query = select(func.count()).select_from(Experiment).where(
        Experiment.source == "tracked",
        Experiment.status.in_(["success", "failed"]),
    )
    if last_trained_at:
        count_query = count_query.where(Experiment.created_at > last_trained_at)

    result = await db.execute(count_query)
    return result.scalar() or 0
