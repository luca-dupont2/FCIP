from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np
import pandas as pd

if TYPE_CHECKING:
    from fcip_shared.models.experiment import Experiment
    from fcip_shared.models.report import Report

KNOWN_DEVICES = [
    "xcvu9p-flgb2104-2-e",
    "xcvu3p-ffvc1517-2-e",
    "xcku060-ffva1156-2-e",
    "5CEFA7F31C6",
    "10AS066N3F40E2SG",
]


def experiment_to_feature_dict(experiment: Experiment, report: Report | None) -> dict:
    opts = experiment.compile_options or {}
    lut_pct = (report.lut / report.lut_available * 100) if report and report.lut and report.lut_available else 0.0
    ff_pct = (report.ff / report.ff_available * 100) if report and report.ff and report.ff_available else 0.0
    bram_pct = (report.bram / report.bram_available * 100) if report and report.bram and report.bram_available else 0.0
    dsp_pct = (report.dsp / report.dsp_available * 100) if report and report.dsp and report.dsp_available else 0.0

    return {
        "device": experiment.device or "unknown",
        "lut_pct": lut_pct,
        "ff_pct": ff_pct,
        "bram_pct": bram_pct,
        "dsp_pct": dsp_pct,
        "seed": experiment.seed or 1,
        "retiming": bool(opts.get("retiming", False)),
        "phys_opt": bool(opts.get("phys_opt", False)),
        "strategy": opts.get("strategy", "default"),
    }


def engineer_features(
    experiments: list[dict],
) -> pd.DataFrame:
    rows = []
    for exp in experiments:
        row: dict = {}

        device = exp.get("device", "unknown")
        for d in KNOWN_DEVICES:
            row[f"device_{d}"] = 1.0 if device == d else 0.0
        row["device_unknown"] = 1.0 if device not in KNOWN_DEVICES else 0.0

        lut_pct = exp.get("lut_pct") or exp.get("lut_percent") or 0.0
        ff_pct = exp.get("ff_pct") or exp.get("ff_percent") or 0.0
        bram_pct = exp.get("bram_pct") or exp.get("bram_percent") or 0.0
        dsp_pct = exp.get("dsp_pct") or exp.get("dsp_percent") or 0.0

        row["lut_pct"] = lut_pct
        row["ff_pct"] = ff_pct
        row["bram_pct"] = bram_pct
        row["dsp_pct"] = dsp_pct

        row["seed"] = exp.get("seed") or 1
        row["retiming"] = int(exp.get("retiming", False) or False)
        row["phys_opt"] = int(exp.get("phys_opt", False) or False)

        strategy = exp.get("strategy", "default")
        for s in ["default", "Performance_Explore", "Area_Explore", "Power_Explore"]:
            row[f"strategy_{s}"] = 1.0 if strategy == s else 0.0

        row["util_product"] = float(lut_pct) * float(ff_pct)
        row["bram_dsp_ratio"] = float(bram_pct) / (float(dsp_pct) + 1.0)
        row["high_util_flag"] = 1 if float(lut_pct) > 70 or float(ff_pct) > 70 else 0
        row["strategy_perf_flag"] = 1 if strategy == "Performance_Explore" else 0

        rows.append(row)

    df = pd.DataFrame(rows)
    numeric_cols = df.select_dtypes(include=[np.number]).columns
    df[numeric_cols] = df[numeric_cols].fillna(df[numeric_cols].median())
    return df


def engineer_single(exp: dict) -> pd.DataFrame:
    return engineer_features([exp])
