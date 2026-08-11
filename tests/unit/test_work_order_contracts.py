import pytest
from pydantic import ValidationError

from app.contracts.work_orders import WorkOrderCreateV1


def test_required_strings_reject_blank_without_normalizing_valid_values() -> None:
    value = "  información significativa  "

    contract = WorkOrderCreateV1(
        incident_text=value,
        address=value,
        zone=value,
    )

    assert contract.incident_text == value
    assert contract.address == value
    assert contract.zone == value

    with pytest.raises(ValidationError) as error:
        WorkOrderCreateV1(incident_text=" \t", address="A", zone="Z")
    assert error.value.errors()[0]["type"] == "string_blank"


def test_contract_forbids_unknown_top_level_fields_and_requires_context_object() -> None:
    with pytest.raises(ValidationError) as extra:
        WorkOrderCreateV1(
            incident_text="I",
            address="A",
            zone="Z",
            unsupported=True,
        )
    assert extra.value.errors()[0]["type"] == "extra_forbidden"

    with pytest.raises(ValidationError) as context:
        WorkOrderCreateV1(
            incident_text="I",
            address="A",
            zone="Z",
            context=["not", "an", "object"],
        )
    assert context.value.errors()[0]["loc"] == ("context",)
