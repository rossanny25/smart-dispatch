from __future__ import annotations

import json
import os
import re
from typing import Any, Callable
from urllib import error, request

from pydantic import ValidationError

from app.adapters.stages.deterministic_analyze import DeterministicAnalyzeStage
from app.contracts.stages.analyze import (
    AnalyzeInputV1,
    AnalyzeOutputV1,
    SuppliedDispatchRequirementsV1,
)


DEFAULT_OLLAMA_BASE_URL = "http://127.0.0.1:11434"
DEFAULT_OLLAMA_MODEL = "llama3.1:8b"
DEFAULT_OLLAMA_TIMEOUT_SECONDS = 8.0


class OllamaAnalyzeStage:
    """Optional local LLM adapter that revalidates proposals through Analyze v1."""

    def __init__(
        self,
        *,
        base_url: str = DEFAULT_OLLAMA_BASE_URL,
        model: str = DEFAULT_OLLAMA_MODEL,
        timeout_seconds: float = DEFAULT_OLLAMA_TIMEOUT_SECONDS,
        fallback_stage: DeterministicAnalyzeStage | None = None,
        post_json: Callable[[str, dict[str, Any], float], dict[str, Any]] | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._timeout_seconds = timeout_seconds
        self._fallback_stage = fallback_stage or DeterministicAnalyzeStage()
        self._post_json = post_json or _post_json

    def execute(self, payload: dict[str, Any]) -> dict[str, Any]:
        validated = AnalyzeInputV1.model_validate(payload)
        try:
            proposal = self._request_requirements(validated)
            delegated_payload = _payload_with_llm_proposal(payload, proposal)
            result = self._fallback_stage.execute(delegated_payload)
            result["adapter_metadata"] = {
                "kind": "llm",
                "provider": "ollama",
                "model": self._model,
            }
            return AnalyzeOutputV1.model_validate(result).model_dump(mode="json")
        except (OSError, ValueError, ValidationError, error.URLError, TimeoutError):
            return self._fallback_stage.execute(payload)

    def _request_requirements(
        self, payload: AnalyzeInputV1
    ) -> SuppliedDispatchRequirementsV1:
        body = {
            "model": self._model,
            "prompt": _prompt(payload),
            "stream": False,
            "format": "json",
            "options": {"temperature": 0},
        }
        response = self._post_json(
            f"{self._base_url}/api/generate",
            body,
            self._timeout_seconds,
        )
        content = response.get("response")
        if not isinstance(content, str):
            raise ValueError("Ollama response did not include a text response")
        parsed = _parse_json_object(content)
        return SuppliedDispatchRequirementsV1.model_validate(parsed)


def build_analyze_stage_from_environment() -> DeterministicAnalyzeStage | OllamaAnalyzeStage:
    adapter = os.environ.get("SMART_DISPATCH_ANALYZE_ADAPTER", "deterministic")
    if adapter.strip().lower() != "ollama":
        return DeterministicAnalyzeStage()
    timeout_raw = os.environ.get(
        "OLLAMA_TIMEOUT_SECONDS", str(DEFAULT_OLLAMA_TIMEOUT_SECONDS)
    )
    try:
        timeout_seconds = max(0.5, min(float(timeout_raw), 60.0))
    except ValueError:
        timeout_seconds = DEFAULT_OLLAMA_TIMEOUT_SECONDS
    return OllamaAnalyzeStage(
        base_url=os.environ.get("OLLAMA_BASE_URL", DEFAULT_OLLAMA_BASE_URL),
        model=os.environ.get("OLLAMA_MODEL", DEFAULT_OLLAMA_MODEL),
        timeout_seconds=timeout_seconds,
    )


def _post_json(url: str, payload: dict[str, Any], timeout: float) -> dict[str, Any]:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    http_request = request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with request.urlopen(http_request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def _payload_with_llm_proposal(
    payload: dict[str, Any], proposal: SuppliedDispatchRequirementsV1
) -> dict[str, Any]:
    copied = json.loads(json.dumps(payload, ensure_ascii=False))
    work_order = copied["work_order"]
    context = dict(work_order.get("context") or {})
    context["dispatch_requirements"] = proposal.model_dump(
        exclude_none=True,
        mode="json",
    )
    work_order["context"] = context
    return copied


def _parse_json_object(content: str) -> dict[str, Any]:
    stripped = content.strip()
    if stripped.startswith("```"):
        stripped = re.sub(r"^```(?:json)?", "", stripped.strip(), flags=re.IGNORECASE)
        stripped = re.sub(r"```$", "", stripped.strip())
    if "{" in stripped and "}" in stripped:
        stripped = stripped[stripped.index("{") : stripped.rindex("}") + 1]
    parsed = json.loads(stripped)
    if not isinstance(parsed, dict):
        raise ValueError("Ollama proposal must be a JSON object")
    return parsed


def _prompt(payload: AnalyzeInputV1) -> str:
    work_order = payload.work_order
    return f"""
You are the optional local ANALYZE adapter for Smart Dispatch IA.
Return only one JSON object. Do not include markdown or explanation.
Use exactly these enum values:
- category: gas, electricity, telecommunications, plumbing, hvac, maintenance
- required_certifications: gas_registered, electrician_category_a, wan_networks, fiber_optics, working_at_height, licensed_plumber, high_pressure_refrigerants

Required schema:
{{
  "category": "...",
  "priority": 1,
  "sla_target_minutes": 60,
  "required_certifications": ["..."],
  "estimated_service_duration_minutes": 90
}}

Rules:
- priority is an integer from 1 to 5.
- sla_target_minutes must match priority: 1=10080, 2=2880, 3=720, 4=240, 5=60.
- estimated_service_duration_minutes is between 15 and 1440.
- Use an empty certification list only for maintenance/general work.
- If uncertain, choose maintenance, priority 3, SLA 720, no certifications, duration 60.

Incident text:
{work_order.incident_text}

Zone:
{work_order.zone}
""".strip()
