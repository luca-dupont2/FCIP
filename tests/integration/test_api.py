from __future__ import annotations

import pytest
import pytest_asyncio

from fcip_shared.exceptions import NotFoundError


@pytest.mark.asyncio
class TestHealthEndpoint:
    async def test_health(self, client):
        resp = await client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"


@pytest.mark.asyncio
class TestProjectsAPI:
    async def test_create_project(self, client):
        resp = await client.post("/api/projects", json={"name": "test-proj"})
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "test-proj"
        assert "id" in data

    async def test_list_projects(self, client):
        resp = await client.get("/api/projects")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    async def test_get_project_not_found(self, client):
        resp = await client.get("/api/projects/00000000-0000-0000-0000-000000000000")
        assert resp.status_code == 404

    async def test_delete_project(self, client):
        create = await client.post("/api/projects", json={"name": "delete-me"})
        pid = create.json()["id"]
        resp = await client.delete(f"/api/projects/{pid}")
        assert resp.status_code == 204


@pytest.mark.asyncio
class TestExperimentsAPI:
    async def test_create_experiment(self, client):
        proj = await client.post("/api/projects", json={"name": "exp-proj"})
        pid = proj.json()["id"]
        resp = await client.post("/api/experiments", json={
            "project_id": pid,
            "tool": "vivado",
            "device": "xcvu9p-flgb2104-2-e",
            "seed": 1,
            "status": "success",
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["tool"] == "vivado"
        assert data["device"] == "xcvu9p-flgb2104-2-e"

    async def test_list_experiments(self, client):
        resp = await client.get("/api/experiments")
        assert resp.status_code == 200
        body = resp.json()
        assert "items" in body
        assert "total" in body

    async def test_search_experiments(self, client):
        resp = await client.get("/api/experiments/search")
        assert resp.status_code == 200

    async def test_get_experiment_not_found(self, client):
        resp = await client.get("/api/experiments/00000000-0000-0000-0000-000000000000")
        assert resp.status_code == 404

    async def test_update_experiment(self, client):
        proj = await client.post("/api/projects", json={"name": "patch-proj"})
        pid = proj.json()["id"]
        exp = await client.post("/api/experiments", json={
            "project_id": pid,
            "tool": "vivado",
            "status": "running",
        })
        eid = exp.json()["id"]
        resp = await client.patch(f"/api/experiments/{eid}", json={"status": "success"})
        assert resp.status_code == 200
        assert resp.json()["status"] == "success"


@pytest.mark.asyncio
class TestReportsAPI:
    async def test_create_and_list_report(self, client):
        proj = await client.post("/api/projects", json={"name": "rpt-proj"})
        pid = proj.json()["id"]
        exp = await client.post("/api/experiments", json={
            "project_id": pid,
            "tool": "vivado",
            "status": "success",
        })
        eid = exp.json()["id"]

        resp = await client.post("/api/reports", json={
            "experiment_id": eid,
            "report_type": "timing",
            "wns": 0.456,
            "tns": 0.0,
            "failing_paths": 0,
        })
        assert resp.status_code == 201

        listing = await client.get("/api/reports", params={"experiment_id": eid})
        assert listing.status_code == 200
        assert len(listing.json()) >= 1


@pytest.mark.asyncio
class TestCompareAPI:
    async def test_compare_two_experiments(self, client):
        proj = await client.post("/api/projects", json={"name": "cmp-proj"})
        pid = proj.json()["id"]

        exp_a = await client.post("/api/experiments", json={
            "project_id": pid, "tool": "vivado", "status": "success",
        })
        exp_b = await client.post("/api/experiments", json={
            "project_id": pid, "tool": "vivado", "status": "success",
        })
        aid = exp_a.json()["id"]
        bid = exp_b.json()["id"]

        await client.post("/api/reports", json={
            "experiment_id": aid, "report_type": "timing",
            "wns": 0.5, "tns": 0.0,
        })
        await client.post("/api/reports", json={
            "experiment_id": bid, "report_type": "timing",
            "wns": -1.0, "tns": -3.0,
        })

        resp = await client.post("/api/compare", json={"experiment_ids": [aid, bid]})
        assert resp.status_code == 200
        data = resp.json()
        assert "deltas" in data
        assert "wns" in data["deltas"]
        assert data["deltas"]["wns"]["delta"] == pytest.approx(-1.5)

    async def test_compare_requires_two_ids(self, client):
        resp = await client.post("/api/compare", json={"experiment_ids": ["one-id"]})
        assert resp.status_code == 404 or resp.status_code == 422


@pytest.mark.asyncio
class TestPredictAPI:
    async def test_predict_with_features(self, client):
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
        assert resp.status_code == 200
        data = resp.json()
        assert "error" in data or "expected_wns" in data

    async def test_train_models(self, client):
        resp = await client.post("/api/predict/train")
        assert resp.status_code == 202

    async def test_list_models(self, client):
        resp = await client.get("/api/predict/models")
        assert resp.status_code == 200


@pytest.mark.asyncio
class TestRecommendAPI:
    async def test_recommend_for_experiment(self, client):
        proj = await client.post("/api/projects", json={"name": "rec-proj"})
        pid = proj.json()["id"]
        exp = await client.post("/api/experiments", json={
            "project_id": pid, "tool": "vivado", "status": "success",
        })
        eid = exp.json()["id"]

        import uuid
        eid_uuid = str(uuid.UUID(eid))

        resp = await client.post("/api/recommend", json={"experiment_id": eid_uuid})
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)
