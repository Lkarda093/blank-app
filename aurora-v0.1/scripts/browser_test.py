"""Optional QA harness. Isolates SQLite and backups in a temporary directory."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import urllib.request

root = Path(__file__).resolve().parents[1]
with tempfile.TemporaryDirectory(prefix="aurora-e2e-") as folder:
    env = dict(os.environ, AURORA_E2E_DB=str(Path(folder) / "test.sqlite3"))
    with (Path(folder) / "backend.log").open("w") as backend_log, (Path(folder) / "frontend.log").open("w") as frontend_log:
        backend = subprocess.Popen([sys.executable, "-m", "uvicorn", "tests.e2e_server:app_factory", "--factory", "--host", "127.0.0.1", "--port", "8000"], cwd=root / "backend", env=env, stdout=backend_log, stderr=subprocess.STDOUT)
        frontend = subprocess.Popen(["node", str(root / "frontend/node_modules/vite/bin/vite.js")], cwd=root / "frontend", stdout=frontend_log, stderr=subprocess.STDOUT)
        try:
            opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
            for _ in range(100):
                if backend.poll() is not None or frontend.poll() is not None:
                    raise RuntimeError("Servidores de teste falharam. Pare a Aurora normal para liberar as portas 8000 e 5173.")
                try:
                    with opener.open("http://127.0.0.1:5173/api/health", timeout=1) as response:
                        if response.status == 200:
                            break
                except Exception:
                    time.sleep(0.1)
            else:
                raise RuntimeError("Servidores de teste não iniciaram.")
            subprocess.run(["node", str(root / "frontend/tests/browser-smoke.cjs")], cwd=root, check=True, timeout=240, env=dict(os.environ,AURORA_TEST_PYTHON=sys.executable))
        finally:
            frontend.terminate()
            backend.terminate()
            for process in (frontend, backend):
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
