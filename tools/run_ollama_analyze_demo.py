from __future__ import annotations

import json

from app.adapters.stages.ollama_analyze import build_analyze_stage_from_environment


DEMO_PAYLOAD = {
    "schema_version": "v1",
    "configuration_version": "analysis-v1",
    "work_order": {
        "incident_text": (
            "Urgente: corte electrico general en cafeteria, salto la termica "
            "principal y no funcionan las maquinas."
        ),
        "address": "Direccion privada para demo local",
        "zone": "Belgrano",
        "context": None,
    },
}


def main() -> None:
    stage = build_analyze_stage_from_environment()
    result = stage.execute(DEMO_PAYLOAD)
    print(
        json.dumps(
            {
                "adapter_metadata": result["adapter_metadata"],
                "requirements": result["requirements"],
                "warnings": result["warnings"],
            },
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
