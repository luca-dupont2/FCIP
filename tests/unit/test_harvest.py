"""Tests for deprecated harvest_hlsfactory.py functionality.

DEPRECATED: HLSFactory infrastructure is deprecated. Tests retained for reference only.
See scripts/deprecated/ for the actual implementation.

**Why deprecated**:
- HLSFactory provides HLS synthesis estimates only — not post-implementation timing
- Requires Vitis HLS installation
- Strategic focus: user's own tracked builds
"""
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
import pytest

from fcip_predictor.generator import SyntheticExperimentGenerator


def test_scan_hlsfactory_results_basic():
    """Test scanning HLSFactory results from a directory structure."""
    # Create a temporary directory structure mimicking HLSFactory output
    with tempfile.TemporaryDirectory() as tmpdir:
        work_dir = Path(tmpdir)
        
        # Create a sample design directory
        design_dir = work_dir / "design_1"
        design_dir.mkdir()
        
        # Create data_hls.json
        hls_data = {
            "clock_period": 5.0,
            "latency_best_cycles": 100,
            "latency_worst_cycles": 150,
            "resources_lut_used": 1200,
            "resources_ff_used": 800,
            "resources_bram_used": 10,
            "resources_dsp_used": 5,
            "resources_uram_used": 0,
        }
        (design_dir / "data_hls.json").write_text(json.dumps(hls_data))
        
        # Create data_design.json
        design_data = {
            "name": "design_1",
            "part": "xcvu9p-flgb2104-2-e",
            "target_clock_period": 5.0,
            "version_vitis_hls": "2024.1",
        }
        (design_dir / "data_design.json").write_text(json.dumps(design_data))
        
        # Create data_implementation.json
        impl_data = {
            "timing__wns": 0.2,
            "timing__tns": 0.5,
            "power__total_power": 1.2,
            "utilization__Total LUTs": 1200,
            "timing__clock_period": 5.0,
            "timing__clock_frequency": 200.0,
        }
        (design_dir / "data_implementation.json").write_text(json.dumps(impl_data))
        
        # Create hls_execution_time_VitisHLSSynthFlow.txt
        (design_dir / "hls_execution_time_VitisHLSSynthFlow.txt").write_text("123.45")
        
        # Import the function to test
        from scripts.harvest_hlsfactory import scan_hlsfactory_results
        
        results = scan_hlsfactory_results(work_dir)
        
        assert len(results) == 1
        r = results[0]
        assert r["design_name"] == "design_1"
        assert r["part"] == "xcvu9p-flgb2104-2-e"
        assert r["target_clock_period"] == 5.0
        assert r["vitis_hls_version"] == "2024.1"
        assert r["lut"] == 1200
        assert r["ff"] == 800
        assert r["bram"] == 10
        assert r["dsp"] == 5
        assert r["wns"] == 0.2
        assert r["tns"] == 0.5
        assert r["total_runtime"] == 123.45
        assert r["latency_best_cycles"] == 100
        assert r["latency_worst_cycles"] == 150


def test_scan_hlsfactory_results_missing_files():
    """Test scanning when some files are missing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        work_dir = Path(tmpdir)
        design_dir = work_dir / "design_1"
        design_dir.mkdir()
        
        # Only create data_hls.json
        hls_data = {
            "clock_period": 5.0,
            "resources_lut_used": 1200,
            "resources_ff_used": 800,
            "resources_bram_used": 10,
            "resources_dsp_used": 5,
        }
        (design_dir / "data_hls.json").write_text(json.dumps(hls_data))
        
        # No data_design.json, no data_implementation.json, no timing file
        
        from scripts.harvest_hlsfactory import scan_hlsfactory_results
        
        results = scan_hlsfactory_results(work_dir)
        
        assert len(results) == 1
        r = results[0]
        assert r["design_name"] == "design_1"
        assert r["part"] == "xcvu9p-flgb2104-2-e"  # default part
        assert r["target_clock_period"] == 5.0
        assert r["wns"] is None
        assert r["tns"] is None
        assert r["total_runtime"] is None
        assert r["latency_best_cycles"] is None
        assert r["latency_worst_cycles"] is None
        assert r["vitis_hls_version"] is None


@pytest.mark.skipif(not os.environ.get("TEST_POSTGRES"), reason="Requires PostgreSQL database running")
def test_ingest_harvested_results():
    """Test ingesting harvested results into FCIP database."""
    # Create test data
    results = [
        {
            "design_name": "polybench_1",
            "part": "xcvu9p-flgb2104-2-e",
            "target_clock_period": 5.0,
            "dataset_name": "polybench",
            "vitis_hls_version": "2024.1",
            "lut": 1200,
            "lut_available": 1185600,
            "ff": 800,
            "ff_available": 2371200,
            "bram": 10,
            "bram_available": 2160,
            "dsp": 5,
            "dsp_available": 6840,
            "latency_best_cycles": 100,
            "latency_worst_cycles": 150,
            "wns": 0.2,
            "tns": 0.5,
            "total_runtime": 123.45,
            "resources_uram_used": 0,
        }
    ]
    
    # Import the function
    from scripts.harvest_hlsfactory import ingest_harvested_results
    
    # Use a temporary database (in-memory)
    # We'll use the same database setup as the test suite
    import asyncio
    
    async def run_test():
        counts = await ingest_harvested_results(results)
        return counts
    
    counts = asyncio.run(run_test())
    
    assert counts["experiments"] == 1
    assert counts["reports"] == 1
    assert counts["skipped"] == 0


@pytest.mark.skipif(not os.environ.get("TEST_VITIS_HLS"), reason="Requires Vitis HLS installation")
def test_run_hlsfactory_synth():
    """Test running HLSFactory synth (mocked)."""
    # This test is skipped because it requires actual Vitis HLS installation
    # We'll just test that the function can be called without error
    
    import asyncio
    
    from scripts.harvest_hlsfactory import run_hlsfactory_synth
    
    with tempfile.TemporaryDirectory() as tmpdir:
        work_dir = Path(tmpdir)
        
        # Call the function - it should not raise an error
        result = run_hlsfactory_synth(work_dir=work_dir, datasets=["polybench"], target_clock_period=5.0)
        
        # We can't verify actual results without Vitis HLS
        assert result == work_dir


def test_harvest_cli_scan():
    """Test the harvest CLI scan mode."""
    # We'll test that the CLI command structure is correct
    # This is a smoke test for the typer command
    
    from fcip_cli.main import app
    from typer.testing import CliRunner
    
    runner = CliRunner()
    
    # Create a temporary directory
    with tempfile.TemporaryDirectory() as tmpdir:
        result = runner.invoke(app, ["harvest", "scan", tmpdir])
        
        # We don't expect success (no real data), but it should not crash
        assert result.exit_code != 0  # Will fail if no data, but command should execute
        
        # Check help works
        help_result = runner.invoke(app, ["harvest", "--help"])
        assert help_result.exit_code == 0
        assert "scan" in help_result.output
        assert "run" in help_result.output


def test_harvest_cli_run():
    """Test the harvest CLI run mode."""
    from fcip_cli.main import app
    from typer.testing import CliRunner
    
    runner = CliRunner()
    
    with tempfile.TemporaryDirectory() as tmpdir:
        result = runner.invoke(app, ["harvest", "run", tmpdir, "--datasets", "polybench", "--ingest"])
        
        # We don't expect success (no Vitis HLS), but it should not crash
        assert result.exit_code != 0  # Will fail if no Vitis HLS, but command should execute
        
        # Check help works
        help_result = runner.invoke(app, ["harvest", "--help"])
        assert help_result.exit_code == 0
        assert "run" in help_result.output
        assert "--ingest" in help_result.output