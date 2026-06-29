from __future__ import annotations

import time
import pytest
import pytest_asyncio


@pytest.mark.asyncio
class TestBulkImportPerformance:
    async def test_bulk_create_1000_experiments(self, client):
        proj = await client.post("/api/projects", json={"name": "perf-proj"})
        pid = proj.json()["id"]

        start = time.perf_counter()
        for i in range(100):
            await client.post("/api/experiments", json={
                "project_id": pid,
                "tool": "vivado",
                "device": "xcvu9p-flgb2104-2-e",
                "seed": i,
                "status": "success",
                "name": f"perf-exp-{i:04d}",
            })
        elapsed = time.perf_counter() - start

        assert elapsed < 30.0, f"100 experiments took {elapsed:.1f}s (limit 30s)"
        print(f"\n  100 experiments created in {elapsed:.2f}s ({100/elapsed:.0f}/s)")

    async def test_list_experiments_response_time(self, client):
        proj = await client.post("/api/projects", json={"name": "perf-list-proj"})
        pid = proj.json()["id"]

        for i in range(50):
            await client.post("/api/experiments", json={
                "project_id": pid,
                "tool": "vivado",
                "device": "xcvu9p-flgb2104-2-e",
                "seed": i,
                "status": "success",
            })

        start = time.perf_counter()
        resp = await client.get("/api/experiments", params={"limit": 50})
        elapsed = time.perf_counter() - start

        assert resp.status_code == 200
        assert elapsed < 2.0, f"List 50 experiments took {elapsed:.2f}s (limit 2s)"
        print(f"\n  List 50 experiments in {elapsed:.3f}s")

    async def test_health_endpoint_under_500ms(self, client):
        start = time.perf_counter()
        resp = await client.get("/health")
        elapsed = time.perf_counter() - start

        assert resp.status_code == 200
        assert elapsed < 0.5, f"Health endpoint took {elapsed:.3f}s (limit 500ms)"
        print(f"\n  Health endpoint: {elapsed*1000:.1f}ms")

    async def test_predict_endpoint_under_2s(self, client):
        start = time.perf_counter()
        resp = await client.post("/api/predict", json={
            "device": "xcvu9p-flgb2104-2-e",
            "lut_pct": 45.0,
            "ff_pct": 38.0,
            "bram_pct": 20.0,
            "dsp_pct": 12.0,
            "seed": 42,
            "retiming": True,
            "phys_opt": False,
        })
        elapsed = time.perf_counter() - start

        assert resp.status_code == 200
        assert elapsed < 2.0, f"Predict endpoint took {elapsed:.2f}s (limit 2s)"
        print(f"\n  Predict endpoint: {elapsed*1000:.1f}ms")

    async def test_recommend_endpoint_under_2s(self, client):
        proj = await client.post("/api/projects", json={"name": "perf-rec-proj"})
        pid = proj.json()["id"]
        exp = await client.post("/api/experiments", json={
            "project_id": pid,
            "tool": "vivado",
            "device": "xcvu9p-flgb2104-2-e",
            "seed": 1,
            "status": "success",
        })
        eid = exp.json()["id"]

        start = time.perf_counter()
        resp = await client.post("/api/recommend", json={"experiment_id": eid})
        elapsed = time.perf_counter() - start

        assert resp.status_code == 200
        assert elapsed < 2.0, f"Recommend endpoint took {elapsed:.2f}s (limit 2s)"
        print(f"\n  Recommend endpoint: {elapsed*1000:.1f}ms")
