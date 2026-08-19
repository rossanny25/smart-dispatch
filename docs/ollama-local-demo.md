# Ollama Local Analyze Demo

This document describes the optional local Ollama path for the `ANALYZE` stage.
It is intentionally local-only and is not configured in `render.yaml`.

## What It Does

When enabled, Ollama reads the incident text and proposes structured dispatch
requirements:

- `category`
- `priority`
- `sla_target_minutes`
- `required_certifications`
- `estimated_service_duration_minutes`

The proposal is not authoritative by itself. Smart Dispatch IA revalidates it
through the same `AnalyzeOutputV1` contract and then continues with the
deterministic hard constraints, scoring, confidence, and dispatch state flow.

If Ollama is unavailable, slow, or returns invalid JSON, the app falls back to
the deterministic analyze adapter.

## Option A: Local Host Ollama

Install and start Ollama on the machine:

```bash
ollama serve
ollama pull llama3.1:8b
```

Run Smart Dispatch IA with the optional adapter:

```bash
SMART_DISPATCH_ANALYZE_ADAPTER=ollama \
OLLAMA_BASE_URL=http://127.0.0.1:11434 \
OLLAMA_MODEL=llama3.1:8b \
OLLAMA_TIMEOUT_SECONDS=8 \
uv run smart-dispatch
```

Quickly verify the adapter metadata before opening the browser:

```bash
SMART_DISPATCH_ANALYZE_ADAPTER=ollama \
OLLAMA_BASE_URL=http://127.0.0.1:11434 \
OLLAMA_MODEL=llama3.1:8b \
uv run python tools/run_ollama_analyze_demo.py
```

Expected when Ollama returns a valid proposal:

```json
{
  "adapter_metadata": {
    "kind": "llm",
    "model": "llama3.1:8b",
    "provider": "ollama"
  }
}
```

If Ollama is not running or the model is missing, the same command still
returns a valid deterministic result with `"kind": "local"`.

Open:

```text
http://127.0.0.1:8000
```

## Option B: Docker Compose With Ollama

Start the app plus a local Ollama container:

```bash
docker compose -f docker-compose.yml -f docker-compose.ollama.yml up --build
```

In another terminal, pull the model into the Ollama volume:

```bash
docker compose -f docker-compose.yml -f docker-compose.ollama.yml exec ollama ollama pull llama3.1:8b
```

Open:

```text
http://127.0.0.1:8050
```

## Option C: Docker App With Host Ollama

Use this option when Ollama already runs on the host machine and the model is
already downloaded there. This is the fastest path for recording a local video
because the app container calls the host Ollama runtime:

```bash
OLLAMA_BASE_URL=http://host.docker.internal:11434 \
OLLAMA_MODEL=qwen2.5:latest \
OLLAMA_TIMEOUT_SECONDS=60 \
docker compose -f docker-compose.yml -f docker-compose.ollama.yml up -d
```

Verify from inside the app container:

```bash
docker compose -f docker-compose.yml -f docker-compose.ollama.yml exec smart-dispatch python -c "from app.adapters.stages.ollama_analyze import build_analyze_stage_from_environment; payload={'schema_version':'v1','configuration_version':'analysis-v1','work_order':{'incident_text':'Urgente: corte electrico general en cafeteria, salto la termica principal y no funcionan las maquinas.','address':'Direccion privada para demo local','zone':'Belgrano','context':None}}; result=build_analyze_stage_from_environment().execute(payload); import json; print(json.dumps(result['adapter_metadata'], ensure_ascii=False, indent=2))"
```

Expected:

```json
{
  "kind": "llm",
  "provider": "ollama",
  "model": "qwen2.5:latest"
}
```

## Suggested Video Flow

1. Show that `render.yaml` has no Ollama variables.
2. Start the local Ollama demo with one of the commands above.
3. Run `tools/run_ollama_analyze_demo.py` and show `adapter_metadata.kind = llm`.
4. Log in with `admin` / `smart2026AI`.
5. Create or select an order with descriptive free text.
6. Run dispatch and show the canonical state chips reaching `WAIT_FOR_DECISION`.
7. Stop Ollama or use an invalid model name, rerun the script, and show fallback to `adapter_metadata.kind = local`.

## Local-Only Guardrails

- Do not add Ollama variables to `render.yaml`.
- Keep `SMART_DISPATCH_ANALYZE_ADAPTER` unset in Render.
- Keep deterministic analyze as the default path.
- Do not let the model select the final technician.
- Do not let the model bypass hard constraints, scoring, confidence, or state transitions.
