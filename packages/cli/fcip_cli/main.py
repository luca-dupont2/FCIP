from __future__ import annotations

import time
from pathlib import Path

import httpx
import rich.console
import rich.panel
import rich.table
import typer
from rich import print as rprint

from fcip_cli.client import APIClient, get_git_info, get_machine_info

app = typer.Typer(
    name="fcip",
    help="FPGA Compile Intelligence Platform CLI",
    add_completion=False,
)

console = rich.console.Console()

_CONFIG_DIR = ".fcip"
_CONFIG_FILE = ".fcip/config.toml"


def _load_config() -> dict | None:
    import tomllib
    config_path = Path(_CONFIG_FILE)
    if not config_path.exists():
        return None
    with open(config_path, "rb") as f:
        return tomllib.load(f)


def _save_config(config: dict) -> None:
    import tomli_w
    Path(_CONFIG_DIR).mkdir(exist_ok=True)
    with open(_CONFIG_FILE, "wb") as f:
        tomli_w.dump(config, f)


def _get_api_client() -> APIClient:
    config = _load_config()
    url = None
    if config and "api" in config:
        url = config["api"].get("url")
    return APIClient(base_url=url)


@app.command()
def init(
    name: str = typer.Option(..., prompt="Project name", help="Name of the project"),
    tool: str = typer.Option("vivado", help="FPGA tool: vivado or quartus"),
    api_url: str = typer.Option("http://localhost:8000", help="FCIP backend API URL"),
):
    """Initialize FCIP in the current directory."""
    Path(_CONFIG_DIR).mkdir(exist_ok=True)

    config = {
        "project": {"name": name, "tool": tool},
        "api": {"url": api_url},
        "tracking": {"last_import": "", "imported_experiments": []},
    }
    _save_config(config)

    client = APIClient(base_url=api_url)
    resp = client.post("/api/projects", json={"name": name, "path": str(Path.cwd())})

    rprint(f"[green]Initialized FCIP project '{name}' (tool: {tool})[/green]")
    rprint(f"  Config saved to {_CONFIG_FILE}")
    rprint(f"  Project registered with backend (id: {resp.get('id', 'N/A')})")


@app.command()
def track(
    tool: str = typer.Argument(..., help="FPGA tool: vivado or quartus"),
    path: str = typer.Argument(..., help="Path to project directory"),
    project_id: str = typer.Option(None, help="Override project ID"),
):
    """Import completed compilation runs from a project directory."""
    client = _get_api_client()
    config = _load_config()

    if not config:
        rprint("[red]Not initialized. Run 'fcip init' first.[/red]")
        raise SystemExit(1)

    proj_id = project_id
    if not proj_id:
        projects = client.get("/api/projects")
        proj_name = config.get("project", {}).get("name", "")
        for p in projects:
            if p.get("name") == proj_name:
                proj_id = p["id"]
                break
        if not proj_id and projects:
            proj_id = projects[0]["id"]

    if not proj_id:
        rprint("[red]No project found. Run 'fcip init' first.[/red]")
        raise SystemExit(1)

    from fcip_parsers import get_parser
    from fcip_parsers.vivado import VivadoProjectDetector
    from fcip_parsers.quartus import QuartusProjectDetector

    if tool == "vivado":
        detector = VivadoProjectDetector()
    elif tool == "quartus":
        detector = QuartusProjectDetector()
    else:
        parser = get_parser(tool)
        detector = VivadoProjectDetector()

    detected = detector.detect(path)
    parser = get_parser(tool)

    git_info = get_git_info(path)
    machine_info = get_machine_info()

    imported = 0

    timing_files = detected.get("timing", [])
    util_files = detected.get("utilization", [])
    log_files = detected.get("log", [])

    timing_data = {}
    for tf in timing_files:
        content = Path(tf).read_text(errors="replace")
        result = parser.parse_timing(content, source_file=tf)
        if result.success and result.data:
            timing_data[tf] = result.data

    util_data = {}
    for uf in util_files:
        content = Path(uf).read_text(errors="replace")
        result = parser.parse_utilization(content, source_file=uf)
        if result.success and result.data:
            util_data[uf] = result.data

    runtime_data = {}
    for lf in log_files:
        content = Path(lf).read_text(errors="replace")
        result = parser.parse_runtime(content, source_file=lf)
        if result.success and result.data:
            runtime_data[lf] = result.data

    if not timing_data and not util_data and not runtime_data:
        rprint("[yellow]No parseable reports found in directory.[/yellow]")
        return

    run_name = Path(path).name
    if timing_data:
        first_timing = list(timing_data.values())[0]
        wns_val = first_timing.wns
        status = "success" if wns_val >= 0 else "failed"
    else:
        status = "success"

    exp_body = {
        "project_id": proj_id,
        "name": run_name,
        "git_commit": git_info["git_commit"],
        "branch": git_info["branch"],
        "repository_name": git_info["repository_name"],
        "changed_files": git_info["changed_files"],
        "tool": tool,
        "tool_version": None,
        "device": None,
        "seed": None,
        "status": status,
        "compile_options": {},
        "machine_info": machine_info,
    }

    exp_resp = client.post("/api/experiments", json=exp_body)
    exp_id = exp_resp.get("id")

    if not exp_id:
        rprint(f"[red]Failed to create experiment: {exp_resp}[/red]")
        return

    for tf, tdata in timing_data.items():
        report_body = {
            "experiment_id": exp_id,
            "report_type": "timing",
            "wns": tdata.wns,
            "tns": tdata.tns,
            "failing_paths": tdata.failing_paths,
            "critical_path": str(tdata.critical_path) if tdata.critical_path else None,
            "source_file": tf,
        }
        client.post("/api/reports", json=report_body)

    for uf, udata in util_data.items():
        report_body = {
            "experiment_id": exp_id,
            "report_type": "utilization",
            "lut": udata.lut,
            "lut_available": udata.lut_available,
            "ff": udata.ff,
            "ff_available": udata.ff_available,
            "bram": udata.bram,
            "bram_available": udata.bram_available,
            "dsp": udata.dsp,
            "dsp_available": udata.dsp_available,
            "io_used": udata.io_used,
            "io_available": udata.io_available,
            "clock_utilization": udata.clock_utilization,
            "source_file": uf,
        }
        client.post("/api/reports", json=report_body)

    for lf, rdata in runtime_data.items():
        report_body = {
            "experiment_id": exp_id,
            "report_type": "runtime",
            "synthesis_duration": rdata.synthesis_duration,
            "implementation_duration": rdata.implementation_duration,
            "bitstream_duration": rdata.bitstream_duration,
            "total_runtime": rdata.total_runtime,
            "source_file": lf,
        }
        client.post("/api/reports", json=report_body)

    imported += 1
    rprint(f"[green]Imported experiment: {exp_id}[/green]")
    rprint(f"  Timing files: {len(timing_data)}, Utilization files: {len(util_data)}, Log files: {len(runtime_data)}")

    if config and "tracking" in config:
        config["tracking"]["last_import"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        _save_config(config)


@app.command()
def compare(
    id1: str = typer.Argument(..., help="First experiment ID"),
    id2: str = typer.Argument(..., help="Second experiment ID"),
):
    """Compare two experiments side by side."""
    client = _get_api_client()
    result = client.post("/api/compare", json={"experiment_ids": [id1, id2]})

    if "error" in result and "deltas" not in result:
        rprint(f"[red]Comparison failed: {result.get('detail', result.get('error', 'unknown'))}[/red]")
        return

    table = rich.table.Table(title="Experiment Comparison")
    table.add_column("Metric", style="bold")
    table.add_column("Run A", justify="right")
    table.add_column("Run B", justify="right")
    table.add_column("Delta", justify="right")

    deltas = result.get("deltas", {})
    for metric, data in deltas.items():
        a_val = data.get("a")
        b_val = data.get("b")
        delta = data.get("delta")
        delta_str = ""
        if delta is not None:
            sign = "+" if delta > 0 else ""
            delta_str = f"{sign}{delta:.4f}" if isinstance(delta, float) else f"{sign}{delta}"
            if metric in ("wns", "tns"):
                color = "green" if delta > 0 else "red" if delta < 0 else "white"
            elif metric in ("total_runtime",):
                color = "green" if delta < 0 else "red" if delta > 0 else "white"
            else:
                color = "white"
            delta_str = f"[{color}]{delta_str}[/{color}]"

        table.add_row(
            metric,
            str(a_val) if a_val is not None else "N/A",
            str(b_val) if b_val is not None else "N/A",
            delta_str,
        )

    console.print(table)

    option_diffs = result.get("option_diffs", {})
    if option_diffs:
        opt_table = rich.table.Table(title="Option Differences")
        opt_table.add_column("Option", style="bold")
        opt_table.add_column("Run A", justify="right")
        opt_table.add_column("Run B", justify="right")
        for key, vals in option_diffs.items():
            opt_table.add_row(key, str(vals.get("a")), str(vals.get("b")))
        console.print(opt_table)


@app.command()
def predict(
    experiment_id: str = typer.Option(None, help="Experiment ID to predict from"),
):
    """Generate a prediction for an experiment."""
    client = _get_api_client()
    body = {}
    if experiment_id:
        body["experiment_id"] = experiment_id

    result = client.post("/api/predict", json=body)

    panel_content = []
    if result.get("expected_wns") is not None:
        panel_content.append(f"Expected WNS: {result['expected_wns']:.3f} ns")
    if result.get("expected_compile_duration") is not None:
        hours = result['expected_compile_duration'] / 3600
        panel_content.append(f"Expected Duration: {result['expected_compile_duration']:.0f}s ({hours:.1f}h)")
    if result.get("timing_success_probability") is not None:
        prob = result["timing_success_probability"] * 100
        panel_content.append(f"Timing Success Probability: {prob:.1f}%")
    if result.get("error"):
        panel_content.append(f"[red]Error: {result['error']}[/red]")

    console.print(rich.panel.Panel("\n".join(panel_content), title="Prediction"))


@app.command()
def recommend(
    experiment_id: str = typer.Argument(..., help="Experiment ID"),
):
    """Get recommendations for an experiment."""
    client = _get_api_client()
    result = client.post("/api/recommend", json={"experiment_id": experiment_id})

    if not result:
        rprint("[yellow]No recommendations for this experiment.[/yellow]")
        return

    table = rich.table.Table(title="Recommendations")
    table.add_column("Rule", style="bold")
    table.add_column("Category", justify="center")
    table.add_column("Priority", justify="center")
    table.add_column("Confidence", justify="right")
    table.add_column("Message")

    for rec in result:
        table.add_row(
            rec.get("rule_name", ""),
            rec.get("category", ""),
            rec.get("priority", ""),
            f"{rec.get('confidence', 0):.0%}",
            rec.get("message", ""),
        )

    console.print(table)


@app.command()
def train(
    force: bool = typer.Option(False, help="Force retrain even if threshold not met"),
    data_source: str = typer.Option("auto", help="Data source: auto, real, or synthetic"),
):
    """Train or retrain prediction models."""
    client = _get_api_client()

    if not force:
        status = client.get("/api/predict/retrain-status")
        if not status.get("should_retrain", False):
            rprint(f"[yellow]No retrain needed. {status.get('new_experiments_count', 0)} new experiments (threshold: {status.get('threshold', '?')}). Use --force to override.[/yellow]")
            return

    try:
        result = client.post("/api/predict/train", json={"data_source": data_source})
    except Exception as e:
        rprint(f"[red]Training failed: {e}[/red]")
        raise SystemExit(1)

    if result.get("status") == "failed":
        rprint(f"[red]Training failed: {result.get('error', 'unknown')}[/red]")
        raise SystemExit(1)

    results = result.get("results", {})
    table = rich.table.Table(title="Training Results")
    table.add_column("Model", style="bold")
    table.add_column("Version", justify="right")
    table.add_column("Dataset Size", justify="right")
    table.add_column("Data Source", justify="center")
    table.add_column("Metrics")
    table.add_column("Duration", justify="right")

    for name, info in results.items():
        metrics = info.get("metrics", {})
        metrics_str = ", ".join(f"{k}={v:.4f}" if isinstance(v, float) else f"{k}={v}" for k, v in metrics.items())
        table.add_row(
            name,
            str(info.get("version", "?")),
            str(info.get("dataset_size", "?")),
            info.get("data_source", "?"),
            metrics_str,
            f"{info.get('duration', 0):.1f}s",
        )

    console.print(table)


if __name__ == "__main__":
    app()
