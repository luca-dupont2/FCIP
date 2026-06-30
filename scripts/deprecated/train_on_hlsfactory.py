"""DEPRECATED: Train ML models on HLSFactory data.

This script is deprecated and retained for reference only.

**Why deprecated**:
- Creates mock HLSFactory data (not real) using numpy random generation
- HLSFactory provides HLS synthesis estimates only — not post-implementation timing
- Requires Vitis HLS installation for real synth flow
- Strategic focus: **User's own tracked builds** provide real production data

**Recommended alternative**: 
1. Track your builds: `fcip track vivado /path/to/project`
2. Train on your data: `fcip train --data-source=auto`

Original usage (no longer supported):
  uv run python scripts/deprecated/train_on_hlsfactory.py
"""
from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone
from pathlib import Path
import sys

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import numpy as np
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from fcip_shared.database import Base
from fcip_shared.models.project import Project
from fcip_shared.models.experiment import Experiment
from fcip_shared.models.report import Report
from fcip_predictor.features import engineer_features, experiment_to_feature_dict
from fcip_predictor.trainer import ModelTrainer
from fcip_predictor.predictor import Predictor
from sqlalchemy import select
from sqlalchemy.orm import selectinload


async def create_mock_hlsfactory_data(n_samples: int = 200) -> list[dict]:
    """Create realistic mock HLSFactory benchmark data."""
    rng = np.random.default_rng(42)
    
    datasets = ["polybench", "machsuite", "chstone"]
    devices = ["xcvu9p-flgb2104-2-e", "xcvu3p-ffvc1517-2-e", "xcku060-ffva1156-2-e"]
    
    XILINX_PART_RESOURCES = {
        "xcvu9p-flgb2104-2-e": {"lut": 1185600, "ff": 2371200, "bram": 2160, "dsp": 6840, "uram": 960},
        "xcvu3p-ffvc1517-2-e": {"lut": 345600, "ff": 691200, "bram": 960, "dsp": 1680, "uram": 0},
        "xcku060-ffva1156-2-e": {"lut": 331680, "ff": 663360, "bram": 1080, "dsp": 2760, "uram": 0},
    }
    
    results = []
    
    for i in range(n_samples):
        dataset = rng.choice(datasets)
        device = rng.choice(devices)
        resources = XILINX_PART_RESOURCES[device]
        
        design_name = f"{dataset}_{rng.choice(['gemm', 'convolution', 'fft', 'sort', 'spmv', 'stencil', 'histogram', 'crc', 'aes', 'md5'])}_{rng.integers(1, 10)}"
        
        if dataset == "polybench":
            util_base = rng.uniform(0.15, 0.75)
            bram_ratio = rng.uniform(0.05, 0.3)
            dsp_ratio = rng.uniform(0.1, 0.5)
        elif dataset == "machsuite":
            util_base = rng.uniform(0.1, 0.8)
            bram_ratio = rng.uniform(0.02, 0.2)
            dsp_ratio = rng.uniform(0.05, 0.4)
        else:  # chstone
            util_base = rng.uniform(0.05, 0.6)
            bram_ratio = rng.uniform(0.01, 0.15)
            dsp_ratio = rng.uniform(0.01, 0.2)
        
        lut_pct = min(95, max(5, util_base * 100 * rng.uniform(0.8, 1.2)))
        ff_pct = min(95, max(5, util_base * 100 * rng.uniform(0.7, 1.3)))
        bram_pct = min(95, max(1, bram_ratio * 100 * rng.uniform(0.7, 1.3)))
        dsp_pct = min(95, max(1, dsp_ratio * 100 * rng.uniform(0.7, 1.3)))
        
        util_avg = (lut_pct + ff_pct + bram_pct + dsp_pct) / 4
        base_wns = 2.0 - (util_avg / 100) * 3.5
        wns = base_wns + rng.normal(0, 0.4)
        
        tns = wns * rng.uniform(1, 8) if wns < 0 else 0.0
        
        base_runtime = rng.uniform(300, 3600)
        runtime = base_runtime * (1 + util_avg / 200)
        
        results.append({
            "design_name": design_name,
            "part": device,
            "target_clock_period": float(rng.choice([3.33, 5.0, 6.67, 10.0])),
            "dataset_name": dataset,
            "vitis_hls_version": "2024.1",
            "lut": int(resources["lut"] * lut_pct / 100),
            "lut_available": int(resources["lut"]),
            "ff": int(resources["ff"] * ff_pct / 100),
            "ff_available": int(resources["ff"]),
            "bram": int(resources["bram"] * bram_pct / 100),
            "bram_available": int(resources["bram"]),
            "dsp": int(resources["dsp"] * dsp_pct / 100),
            "dsp_available": int(resources["dsp"]),
            "latency_best_cycles": int(rng.integers(50, 500)),
            "latency_worst_cycles": int(rng.integers(500, 5000)),
            "wns": round(float(wns), 4),
            "tns": round(float(tns), 4),
            "total_runtime": round(float(runtime), 1),
            "resources_uram_used": int(resources.get("uram", 0) * rng.uniform(0, 0.1)),
        })
    
    return results


async def ingest_hlsfactory_data(db, results: list[dict], project_name: str = "hlsfactory_demo") -> dict:
    """Ingest HLSFactory results into FCIP database."""
    counts = {"experiments": 0, "reports": 0}
    
    # Create or get project
    project_result = await db.execute(
        select(Project).where(Project.name == project_name)
    )
    project = project_result.scalar_one_or_none()
    
    if project is None:
        project = Project(
            id=uuid.uuid4(),
            name=project_name,
            path="/hlsfactory",
            description="HLSFactory demo benchmark data",
        )
        db.add(project)
        await db.flush()
    
    print(f"Using project: {project.name} ({project.id})")
    
    for r in results:
        device = r["part"]
        wns = r["wns"]
        
        if wns is not None:
            status = "success" if wns >= 0 else "failed"
        else:
            status = "success"
        
        exp = Experiment(
            id=uuid.uuid4(),
            project_id=project.id,
            name=f"hlsf_{r['dataset_name']}_{r['design_name']}",
            tool="vivado",
            tool_version=r.get("vitis_hls_version"),
            device=device,
            seed=1,
            status=status,
            source="hlsfactory",
            compile_options={
                "strategy": "default",
                "retiming": False,
                "phys_opt": False,
                "target_clock_period": r.get("target_clock_period", 5.0),
                "latency_best_cycles": r.get("latency_best_cycles"),
                "latency_worst_cycles": r.get("latency_worst_cycles"),
            },
            created_at=datetime.now(timezone.utc),
            completed_at=datetime.now(timezone.utc),
        )
        db.add(exp)
        await db.flush()
        counts["experiments"] += 1
        
        total_runtime = r.get("total_runtime")
        if total_runtime is not None:
            synth_dur = total_runtime * 0.6
            impl_dur = total_runtime * 0.3
            bit_dur = total_runtime * 0.1
        else:
            synth_dur = impl_dur = bit_dur = None
        
        report = Report(
            id=uuid.uuid4(),
            experiment_id=exp.id,
            report_type="hls_synth",
            wns=wns,
            tns=r.get("tns"),
            lut=r.get("lut"),
            lut_available=r.get("lut_available"),
            ff=r.get("ff"),
            ff_available=r.get("ff_available"),
            bram=r.get("bram"),
            bram_available=r.get("bram_available"),
            dsp=r.get("dsp"),
            dsp_available=r.get("dsp_available"),
            io_used=0,
            io_available=520,
            synthesis_duration=synth_dur,
            implementation_duration=impl_dur,
            bitstream_duration=bit_dur,
            total_runtime=total_runtime,
        )
        db.add(report)
        counts["reports"] += 1
        
        if counts["experiments"] % 50 == 0:
            await db.flush()
            print(f"  Inserted {counts['experiments']} experiments...")
    
    await db.commit()
    
    return counts


async def train_on_real_data(db):
    """Train models using the ingested HLSFactory data."""
    # Get all hlsfactory experiments
    result = await db.execute(
        select(Experiment)
        .where(Experiment.source == "hlsfactory")
        .where(Experiment.status.in_(["success", "failed"]))
        .options(selectinload(Experiment.reports))
    )
    experiments = result.scalars().all()
    
    print(f"\nFound {len(experiments)} HLSFactory experiments")
    
    if len(experiments) < 50:
        print(f"WARNING: Only {len(experiments)} experiments, need 50+ for real training mode")
        print("Falling back to mixed mode...")
        data_source = "auto"
    else:
        data_source = "real"
    
    # Extract features
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
        print("No valid experiment data found!")
        return
    
    X = engineer_features(exp_dicts)
    real_data = (X.values, np.array(targets_wns), np.array(targets_runtime), 
                 np.array(targets_success), len(exp_dicts))
    
    print(f"Training with {len(exp_dicts)} samples (data_source={data_source})")
    
    # Train models
    trainer = ModelTrainer()
    results = trainer.train_all(real_data=real_data, data_source=data_source)
    
    for name, result in results.items():
        print(f"\n  {name}:")
        print(f"    Version: {result['version']}")
        print(f"    Dataset size: {result['dataset_size']}")
        print(f"    Data source: {result.get('data_source', 'unknown')}")
        print(f"    Metrics: {result['metrics']}")
        print(f"    Duration: {result['duration']:.1f}s")
    
    return results


async def test_prediction():
    """Test making a prediction with the trained model."""
    predictor = Predictor()
    
    features = {
        "device": "xcvu9p-flgb2104-2-e",
        "lut_pct": 60.0,
        "ff_pct": 55.0,
        "bram_pct": 30.0,
        "dsp_pct": 40.0,
        "seed": 1,
        "retiming": False,
        "phys_opt": False,
        "strategy": "default",
    }
    
    print("\n[Testing prediction with sample features]")
    result = predictor.predict(features)
    
    print(f"  Expected WNS: {result.get('expected_wns', 'N/A')} ns")
    print(f"  Expected Duration: {result.get('expected_compile_duration', 'N/A')} s")
    print(f"  Timing Success Probability: {result.get('timing_success_probability', 'N/A')}")
    print(f"  Model Versions: {result.get('model_versions', {})}")
    if result.get('error'):
        print(f"  Error: {result['error']}")


async def main():
    print("=" * 60)
    print("HLSFactory Real Data Training Pipeline")
    print("=" * 60)
    
    # Create SQLite engine
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    
    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    print("\n[0/4] Database initialized")
    
    # Create session factory
    factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    
    async with factory() as db:
        # Step 1: Generate mock HLSFactory data
        print("\n[1/4] Generating mock HLSFactory data...")
        n_samples = 200
        results = await create_mock_hlsfactory_data(n_samples)
        print(f"Generated {len(results)} experiment results")
        
        # Show distribution
        wns_vals = [r["wns"] for r in results]
        success_count = sum(1 for w in wns_vals if w >= 0)
        print(f"  Timing success: {success_count}/{len(results)} ({100*success_count/len(results):.1f}%)")
        print(f"  WNS range: {min(wns_vals):.3f} to {max(wns_vals):.3f}")
        
        # Step 2: Ingest into database
        print("\n[2/4] Ingesting into FCIP database...")
        counts = await ingest_hlsfactory_data(db, results)
        print(f"Inserted: {counts['experiments']} experiments, {counts['reports']} reports")
        
        # Step 3: Train models
        print("\n[3/4] Training ML models on real data...")
        train_results = await train_on_real_data(db)
        
        # Step 4: Test prediction
        print("\n[4/4] Testing prediction...")
        await test_prediction()
    
    await engine.dispose()
    
    print("\n" + "=" * 60)
    print("Training complete!")
    print("=" * 60)
    print("\nModels saved to: packages/predictor/models/")
    print("You can now make predictions using:")
    print("  fcip predict --experiment-id <ID>")
    print("  or via API: POST /api/predict")


if __name__ == "__main__":
    asyncio.run(main())