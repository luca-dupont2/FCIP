"""DEPRECATED: HLSFactory benchmark harvesting.

This script is deprecated and retained for reference only.

**Why deprecated**:
- HLSFactory provides HLS synthesis estimates only — not post-implementation timing
- Requires Vitis HLS installation (~10GB Xilinx tool)
- Generic benchmarks ≠ user's proprietary designs (not the product moat)
- Strategic focus: **User's own tracked builds** provide real production data

**Recommended alternative**: Use `fcip track <dir>` to ingest your own Vivado/Quartus build logs.

Original usage (no longer supported):
  uv run python scripts/deprecated/harvest_hlsfactory.py scan ./hlsfactory_work
  uv run python scripts/deprecated/harvest_hlsfactory.py run --datasets polybench machsuite
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

XILINX_PART_RESOURCES: dict[str, dict[str, int]] = {
    "xcvu9p-flgb2104-2-e": {"lut": 1185600, "ff": 2371200, "bram": 2160, "dsp": 6840},
    "xcvu3p-ffvc1517-2-e": {"lut": 345600, "ff": 691200, "bram": 960, "dsp": 1680},
    "xcku060-ffva1156-2-e": {"lut": 331680, "ff": 663360, "bram": 1080, "dsp": 2760},
    "xc7z020clg484-1": {"lut": 53200, "ff": 106400, "bram": 140, "dsp": 220},
    "xczu7ev-ffvc1156-2-e": {"lut": 182400, "ff": 364800, "bram": 585, "dsp": 1710},
}

DEFAULT_PART = "xcvu9p-flgb2104-2-e"


def _get_available_resources(part: str) -> dict[str, int]:
    return XILINX_PART_RESOURCES.get(part, XILINX_PART_RESOURCES[DEFAULT_PART])


def scan_hlsfactory_results(work_dir: Path) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    data_hls_files = sorted(work_dir.rglob("data_hls.json"))

    for data_hls_fp in data_hls_files:
        design_dir = data_hls_fp.parent
        design_name = design_dir.name

        try:
            hls_data = json.loads(data_hls_fp.read_text())
        except (json.JSONDecodeError, OSError):
            continue

        data_design_fp = design_dir / "data_design.json"
        design_data: dict = {}
        if data_design_fp.exists():
            try:
                design_data = json.loads(data_design_fp.read_text())
            except (json.JSONDecodeError, OSError):
                pass

        data_impl_fp = design_dir / "data_implementation.json"
        impl_data: dict = {}
        if data_impl_fp.exists():
            try:
                impl_data = json.loads(data_impl_fp.read_text())
            except (json.JSONDecodeError, OSError):
                pass

        part = design_data.get("part", DEFAULT_PART)
        resources = _get_available_resources(part)

        lut_used = hls_data.get("resources_lut_used", 0)
        ff_used = hls_data.get("resources_ff_used", 0)
        bram_used = hls_data.get("resources_bram_used", 0)
        dsp_used = hls_data.get("resources_dsp_used", 0)

        wns = impl_data.get("timing__wns")
        tns = impl_data.get("timing__tns")
        total_runtime = None

        timing_fp = design_dir / "hls_execution_time_VitisHLSSynthFlow.txt"
        if timing_fp.exists():
            try:
                runtime_s = float(timing_fp.read_text().strip())
                total_runtime = runtime_s
            except (ValueError, OSError):
                pass

        entry: dict[str, Any] = {
            "design_name": design_data.get("name", design_name),
            "part": part,
            "target_clock_period": hls_data.get("clock_period", 5.0),
            "dataset_name": design_data.get("dataset_name", "unknown"),
            "vitis_hls_version": design_data.get("version_vitis_hls"),
            "lut": lut_used,
            "lut_available": resources["lut"],
            "ff": ff_used,
            "ff_available": resources["ff"],
            "bram": bram_used,
            "bram_available": resources["bram"],
            "dsp": dsp_used,
            "dsp_available": resources["dsp"],
            "latency_best_cycles": hls_data.get("latency_best_cycles"),
            "latency_worst_cycles": hls_data.get("latency_worst_cycles"),
            "wns": wns,
            "tns": tns,
            "total_runtime": total_runtime,
            "resources_uram_used": hls_data.get("resources_uram_used", 0),
        }
        results.append(entry)

    return results


def run_hlsfactory_synth(
    work_dir: Path,
    datasets: list[str] | None = None,
    target_clock_period: float = 5.0,
    n_jobs: int = 1,
    timeout: float | None = None,
) -> Path:
    from hlsfactory.datasets_builtin import datasets_builder
    from hlsfactory.flow_vitis import VitisHLSSynthFlow

    dataset_names = datasets or ["polybench", "machsuite", "chstone"]
    work_dir.mkdir(parents=True, exist_ok=True)

    design_datasets = datasets_builder(work_dir, dataset_names, dataset_names)

    synth_flow = VitisHLSSynthFlow(log_output=True, log_execution_time=True)

    post_synth_datasets = synth_flow.execute_multiple_design_datasets_naive_parallel(
        design_datasets,
        copy_dataset=True,
        n_jobs=n_jobs,
        timeout=timeout,
    )

    output_dir = work_dir / "harvested"
    output_dir.mkdir(parents=True, exist_ok=True)

    return work_dir


async def ingest_harvested_results(
    results: list[dict[str, Any]],
    project_name: str = "hlsfactory_benchmark",
) -> dict[str, int]:
    from fcip_shared.database import async_session_factory
    from fcip_shared.models.project import Project
    from fcip_shared.models.experiment import Experiment
    from fcip_shared.models.report import Report

    counts = {"experiments": 0, "reports": 0, "skipped": 0}

    async with async_session_factory() as session:
        project_result = await session.execute(
            __import__("sqlalchemy").select(Project).where(Project.name == project_name)
        )
        project = project_result.scalar_one_or_none()

        if project is None:
            project = Project(
                id=uuid.uuid4(),
                name=project_name,
                path="/hlsfactory",
                description="HLSFactory benchmark data",
            )
            session.add(project)
            await session.flush()

        for r in results:
            device = r.get("part", DEFAULT_PART)
            design_name = r.get("design_name", "unknown")
            dataset_name = r.get("dataset_name", "unknown")

            wns = r.get("wns")
            tns = r.get("tns")

            if wns is not None:
                status = "success" if wns >= 0 else "failed"
            else:
                status = "success"

            exp = Experiment(
                id=uuid.uuid4(),
                project_id=project.id,
                name=f"hlsf_{dataset_name}_{design_name}",
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
            session.add(exp)
            await session.flush()
            counts["experiments"] += 1

            total_runtime = r.get("total_runtime")
            if total_runtime is not None:
                synth_dur = total_runtime * 0.6
                impl_dur = total_runtime * 0.3
                bit_dur = total_runtime * 0.1
            else:
                synth_dur = None
                impl_dur = None
                bit_dur = None

            report = Report(
                id=uuid.uuid4(),
                experiment_id=exp.id,
                report_type="hls_synth",
                wns=wns,
                tns=tns,
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
            session.add(report)
            counts["reports"] += 1

            if counts["experiments"] % 50 == 0:
                await session.flush()

        await session.commit()

    return counts


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Harvest FPGA build data from HLSFactory"
    )
    subparsers = parser.add_subparsers(dest="mode", required=True)

    scan_parser = subparsers.add_parser("scan", help="Import results from completed HLSFactory runs")
    scan_parser.add_argument("work_dir", type=Path, help="HLSFactory work directory to scan")
    scan_parser.add_argument("--output", type=Path, help="Save results as JSON (optional)")
    scan_parser.add_argument("--ingest", action="store_true", help="Ingest results into FCIP database")

    run_parser = subparsers.add_parser("run", help="Execute Vitis HLS synth and import results")
    run_parser.add_argument("--output", type=Path, default=Path("./hlsfactory_work"), help="Output work directory")
    run_parser.add_argument("--datasets", nargs="+", default=["polybench", "machsuite", "chstone"], help="Datasets to run")
    run_parser.add_argument("--clock-period", type=float, default=5.0, help="Target clock period (ns)")
    run_parser.add_argument("--n-jobs", type=int, default=1, help="Parallel jobs")
    run_parser.add_argument("--timeout", type=float, default=None, help="Timeout per design (seconds)")
    run_parser.add_argument("--ingest", action="store_true", help="Ingest results into FCIP database")

    args = parser.parse_args()

    if args.mode == "scan":
        print(f"Scanning {args.work_dir} for HLSFactory results...")
        results = scan_hlsfactory_results(args.work_dir)
        print(f"Found {len(results)} design results")

        if args.output:
            args.output.write_text(json.dumps(results, indent=2, default=str))
            print(f"Results saved to {args.output}")

        for r in results[:5]:
            name = r["design_name"]
            lut = r["lut"]
            bram = r["bram"]
            print(f"  {name}: LUT={lut}, FF={r['ff']}, BRAM={bram}, DSP={r['dsp']}")
        if len(results) > 5:
            print(f"  ... and {len(results) - 5} more")

        if args.ingest:
            counts = asyncio.run(ingest_harvested_results(results))
            print(f"Ingested: {counts}")

    elif args.mode == "run":
        print(f"Running HLSFactory synth on: {args.datasets}")
        print(f"  Output dir: {args.output}")
        print(f"  Clock period: {args.clock_period} ns")
        print(f"  Parallel jobs: {args.n_jobs}")

        work_dir = run_hlsfactory_synth(
            work_dir=args.output,
            datasets=args.datasets,
            target_clock_period=args.clock_period,
            n_jobs=args.n_jobs,
            timeout=args.timeout,
        )

        results = scan_hlsfactory_results(work_dir)
        print(f"Completed: {len(results)} design results")

        if args.ingest:
            counts = asyncio.run(ingest_harvested_results(results))
            print(f"Ingested: {counts}")


if __name__ == "__main__":
    main()
