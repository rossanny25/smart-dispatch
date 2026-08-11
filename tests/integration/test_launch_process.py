from hashlib import sha256
import json
from pathlib import Path
import os
import selectors
import subprocess
import sys
import time
from urllib.error import URLError
from urllib.request import Request, urlopen


PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONSOLE_SCRIPT = Path(sys.executable).parent / "smart-dispatch"
LOCAL_URL = "http://127.0.0.1:8000"
LEARNING_SEED = PROJECT_ROOT / "data" / "learning_store.json"


def wait_for_uvicorn_ready(process: subprocess.Popen[str], timeout: float = 10) -> None:
    assert process.stderr is not None
    selector = selectors.DefaultSelector()
    selector.register(process.stderr, selectors.EVENT_READ)
    deadline = time.monotonic() + timeout
    captured: list[str] = []
    try:
        while time.monotonic() < deadline:
            if process.poll() is not None:
                stdout, stderr = process.communicate()
                raise AssertionError(
                    "process exited before its Uvicorn readiness log: "
                    f"{process.returncode}\n{stdout}\n{''.join(captured)}{stderr}"
                )
            for key, _ in selector.select(timeout=0.1):
                line = key.fileobj.readline()
                captured.append(line)
                if "Uvicorn running on http://127.0.0.1:8000" in line:
                    assert process.poll() is None
                    return
    finally:
        selector.close()
    raise AssertionError(f"spawned process readiness timed out: {''.join(captured)}")


def wait_for_http(process: subprocess.Popen[str], timeout: float = 3) -> bytes:
    deadline = time.monotonic() + timeout
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        if process.poll() is not None:
            stdout, stderr = process.communicate()
            raise AssertionError(
                f"process exited before readiness: {process.returncode}\n{stdout}\n{stderr}"
            )
        try:
            with urlopen(LOCAL_URL, timeout=0.25) as response:
                body = response.read()
            assert process.poll() is None
            return body
        except (URLError, TimeoutError) as error:
            last_error = error
            time.sleep(0.05)
    raise AssertionError(f"HTTP readiness timed out: {last_error}")


def request_json(
    path: str,
    *,
    method: str = "GET",
    payload: dict[str, object] | None = None,
) -> tuple[int, object]:
    body = json.dumps(payload).encode() if payload is not None else None
    request = Request(
        f"{LOCAL_URL}{path}",
        data=body,
        method=method,
        headers={"Content-Type": "application/json"} if body is not None else {},
    )
    with urlopen(request, timeout=2) as response:
        return response.status, json.loads(response.read())


def assert_all_legacy_routes_reachable() -> None:
    technicians_status, technicians = request_json("/api/technicians")
    orders_status, orders = request_json("/api/orders")
    memory_status, memory = request_json("/api/memory/learning")
    simulate_status, simulation = request_json(
        "/api/dispatch/simulate",
        method="POST",
        payload={"order_id": "order_001"},
    )
    confirm_status, confirmation = request_json(
        "/api/dispatch/confirm",
        method="POST",
        payload={
            "order_id": "order_001",
            "technician_id": "tech_03",
            "duration_minutes": None,
            "feedback_comment": "",
        },
    )
    reset_status, reset = request_json("/api/reset", method="POST", payload={})

    assert {
        technicians_status,
        orders_status,
        memory_status,
        simulate_status,
        confirm_status,
        reset_status,
    } == {200}
    assert isinstance(technicians, list) and technicians
    assert isinstance(orders, list) and orders
    assert isinstance(memory, list) and memory
    assert isinstance(simulation, dict) and simulation["recommended_assignment"]
    assert isinstance(confirmation, dict) and "learnings_updated" in confirmation
    assert isinstance(reset, dict) and "message" in reset


def stop_process(process: subprocess.Popen[str]) -> tuple[str, str]:
    process.terminate()
    try:
        return process.communicate(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        return process.communicate(timeout=5)


def test_real_console_launch_and_occupied_port_failure(tmp_path: Path) -> None:
    environment = os.environ.copy()
    environment["SMART_DISPATCH_DB_PATH"] = str(tmp_path / "runtime.db")
    environment["SMART_DISPATCH_LEARNING_STORE_PATH"] = str(
        tmp_path / "learning_store.json"
    )
    (tmp_path / "learning_store.json").write_bytes(LEARNING_SEED.read_bytes())
    seed_hash = sha256(LEARNING_SEED.read_bytes()).hexdigest()
    primary = subprocess.Popen(
        [str(CONSOLE_SCRIPT)],
        cwd=tmp_path,
        env=environment,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    try:
        wait_for_uvicorn_ready(primary)
        body = wait_for_http(primary)
        assert b"Smart Dispatch" in body
        assert_all_legacy_routes_reachable()

        second = subprocess.run(
            [str(CONSOLE_SCRIPT)],
            cwd=tmp_path,
            env={**environment, "SMART_DISPATCH_DB_PATH": str(tmp_path / "second.db")},
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
        )
        assert second.returncode != 0
        assert "address already in use" in second.stderr.lower()
    finally:
        stop_process(primary)
    assert sha256(LEARNING_SEED.read_bytes()).hexdigest() == seed_hash


def test_legacy_python_entrypoint_serves_same_app_and_routes(tmp_path: Path) -> None:
    environment = os.environ.copy()
    environment["SMART_DISPATCH_DB_PATH"] = str(tmp_path / "legacy-entry.db")
    environment["SMART_DISPATCH_LEARNING_STORE_PATH"] = str(
        tmp_path / "legacy-learning-store.json"
    )
    (tmp_path / "legacy-learning-store.json").write_bytes(LEARNING_SEED.read_bytes())
    process = subprocess.Popen(
        [sys.executable, str(PROJECT_ROOT / "server.py")],
        cwd=tmp_path,
        env=environment,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    try:
        wait_for_uvicorn_ready(process)
        assert b"Smart Dispatch" in wait_for_http(process)
        assert_all_legacy_routes_reachable()
    finally:
        stop_process(process)
