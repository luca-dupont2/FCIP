from __future__ import annotations

import os
import subprocess
from pathlib import Path

import httpx
import structlog

logger = structlog.get_logger(__name__)

DEFAULT_API_URL = "http://localhost:8000"


class APIClient:
    def __init__(self, base_url: str | None = None) -> None:
        self.base_url = (base_url or os.environ.get("FCIP_API_URL", DEFAULT_API_URL)).rstrip("/")
        self.client = httpx.Client(base_url=self.base_url, timeout=30.0)

    def _request(self, method: str, path: str, **kwargs):
        try:
            response = self.client.request(method, path, **kwargs)
            response.raise_for_status()
            return response.json()
        except httpx.ConnectError:
            logger.error("backend_unavailable", url=self.base_url)
            print(
                f"\n[ERROR] Backend not reachable at {self.base_url}\n"
                "Start the backend with: docker compose up backend\n"
                "Or natively: uvicorn fcip_backend.main:app --reload\n"
            )
            raise SystemExit(1)
        except httpx.HTTPStatusError as e:
            logger.error("api_error", status=e.response.status_code, body=e.response.text)
            return e.response.json()

    def get(self, path: str, **kwargs):
        return self._request("GET", path, **kwargs)

    def post(self, path: str, **kwargs):
        return self._request("POST", path, **kwargs)

    def delete(self, path: str, **kwargs):
        return self._request("DELETE", path, **kwargs)

    def health(self) -> bool:
        try:
            r = self.client.get("/health")
            return r.status_code == 200
        except httpx.ConnectError:
            return False


def get_git_info(project_path: str) -> dict:
    result = {
        "git_commit": None,
        "branch": None,
        "repository_name": None,
        "changed_files": [],
    }

    try:
        r = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True, text=True, cwd=project_path, timeout=10,
        )
        if r.returncode == 0:
            result["git_commit"] = r.stdout.strip()[:40]

        r = subprocess.run(
            ["git", "branch", "--show-current"],
            capture_output=True, text=True, cwd=project_path, timeout=10,
        )
        if r.returncode == 0:
            result["branch"] = r.stdout.strip() or None

        r = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True, text=True, cwd=project_path, timeout=10,
        )
        if r.returncode == 0:
            result["repository_name"] = Path(r.stdout.strip()).name

        r = subprocess.run(
            ["git", "diff", "--name-only", "HEAD~1", "HEAD"],
            capture_output=True, text=True, cwd=project_path, timeout=10,
        )
        if r.returncode == 0 and r.stdout.strip():
            result["changed_files"] = [f for f in r.stdout.strip().split("\n") if f]
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass

    return result


def get_machine_info() -> dict:
    import platform

    info = {
        "hostname": platform.node(),
        "os": platform.system(),
        "os_version": platform.version(),
        "cpu_count": os.cpu_count(),
    }

    try:
        import psutil
        info["ram_gb"] = round(psutil.virtual_memory().total / (1024**3), 1)
    except ImportError:
        pass

    return info
