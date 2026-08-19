from hashlib import sha256
import json
from pathlib import Path
import os
import selectors
import socket
import subprocess
import sys
import time
from urllib.error import URLError
from urllib.request import Request, urlopen


PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONSOLE_SCRIPT = Path(sys.executable).parent / "smart-dispatch"
LEARNING_SEED = PROJECT_ROOT / "data" / "learning_store.json"


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def wait_for_uvicorn_ready(
    process: subprocess.Popen[str],
    *,
    port: int,
    timeout: float = 10,
) -> None:
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
                if f"Uvicorn running on http://127.0.0.1:{port}" in line:
                    assert process.poll() is None
                    return
    finally:
        selector.close()
    raise AssertionError(f"spawned process readiness timed out: {''.join(captured)}")


def wait_for_http(
    process: subprocess.Popen[str],
    *,
    base_url: str,
    timeout: float = 3,
) -> bytes:
    deadline = time.monotonic() + timeout
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        if process.poll() is not None:
            stdout, stderr = process.communicate()
            raise AssertionError(
                f"process exited before readiness: {process.returncode}\n{stdout}\n{stderr}"
            )
        try:
            with urlopen(base_url, timeout=0.25) as response:
                body = response.read()
            assert process.poll() is None
            return body
        except (URLError, TimeoutError) as error:
            last_error = error
            time.sleep(0.05)
    raise AssertionError(f"HTTP readiness timed out: {last_error}")


def request_json(
    base_url: str,
    path: str,
    *,
    method: str = "GET",
    payload: dict[str, object] | None = None,
    headers: dict[str, str] | None = None,
) -> tuple[int, object]:
    body = json.dumps(payload).encode() if payload is not None else None
    request_headers = {"Content-Type": "application/json"} if body is not None else {}
    request_headers.update(headers or {})
    request = Request(
        f"{base_url}{path}",
        data=body,
        method=method,
        headers=request_headers,
    )
    with urlopen(request, timeout=2) as response:
        return response.status, json.loads(response.read())


def login_cookie(base_url: str) -> str:
    body = json.dumps({"username": "admin", "password": "smart2026AI"}).encode()
    request = Request(
        f"{base_url}/auth/login",
        data=body,
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    with urlopen(request, timeout=2) as response:
        assert response.status == 200
        return response.headers["Set-Cookie"].split(";", 1)[0]


def assert_all_legacy_routes_reachable(base_url: str) -> None:
    headers = {"Cookie": login_cookie(base_url)}
    technicians_status, technicians = request_json(
        base_url,
        "/api/technicians",
        headers=headers,
    )
    orders_status, orders = request_json(base_url, "/api/orders", headers=headers)
    memory_status, memory = request_json(
        base_url,
        "/api/memory/learning",
        headers=headers,
    )
    simulate_status, simulation = request_json(
        base_url,
        "/api/dispatch/simulate",
        method="POST",
        payload={"order_id": "order_001"},
        headers=headers,
    )
    confirm_status, confirmation = request_json(
        base_url,
        "/api/dispatch/confirm",
        method="POST",
        payload={
            "order_id": "order_001",
            "technician_id": "tech_03",
            "duration_minutes": None,
            "feedback_comment": "",
        },
        headers=headers,
    )
    reset_status, reset = request_json(
        base_url,
        "/api/reset",
        method="POST",
        payload={},
        headers=headers,
    )

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
    port = free_port()
    base_url = f"http://127.0.0.1:{port}"
    environment = os.environ.copy()
    environment["SMART_DISPATCH_PORT"] = str(port)
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
        wait_for_uvicorn_ready(primary, port=port)
        body = wait_for_http(primary, base_url=base_url)
        assert b"Smart Dispatch" in body
        assert_all_legacy_routes_reachable(base_url)

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
    port = free_port()
    base_url = f"http://127.0.0.1:{port}"
    environment = os.environ.copy()
    environment["SMART_DISPATCH_PORT"] = str(port)
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
        wait_for_uvicorn_ready(process, port=port)
        assert b"Smart Dispatch" in wait_for_http(process, base_url=base_url)
        assert_all_legacy_routes_reachable(base_url)
    finally:
        stop_process(process)
