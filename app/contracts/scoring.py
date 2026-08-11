from decimal import Decimal, InvalidOperation
import re
from typing import Any, Literal
from uuid import UUID

from pydantic import ConfigDict, Field, field_validator, model_validator

from app.contracts.common import StrictContract
from app.contracts.eligibility import EligibilityCandidateV1, EligibilityOutputV1
from app.domain.scoring.models import ScoringResult, ScoringTechnician
from app.domain.scoring.policy import ScoringPolicy
from app.domain.scoring.rules import (
    COMPONENT_ORDER,
    PENALTY_ORDER,
    QUALITY_WARNING,
    SCORING_CONFIGURATION,
    canonical_decimal,
)
from app.domain.scoring.arithmetic import clamp, scoring_scope


DECIMAL_PATTERN = re.compile(r"-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?$")


def _parse_uuid(value: Any) -> Any:
    return UUID(value) if isinstance(value, str) else value


def _canonical_decimal_text(value: Any) -> str:
    if (
        not isinstance(value, str)
        or len(value) > SCORING_CONFIGURATION.maximum_decimal_text_length
        or DECIMAL_PATTERN.fullmatch(value) is None
    ):
        raise ValueError("decimal values must be canonical strings")
    try:
        parsed = Decimal(value)
    except InvalidOperation as error:
        raise ValueError("invalid decimal") from error
    canonical = canonical_decimal(parsed)
    if value != canonical:
        raise ValueError("decimal string is not canonical")
    return value


class FrozenScoringContract(StrictContract):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)


class ScoringTechnicianV1(FrozenScoringContract):
    technician_id: UUID
    eta_minutes: int = Field(
        strict=True,
        ge=SCORING_CONFIGURATION.eta_minutes_minimum,
        le=SCORING_CONFIGURATION.eta_minutes_maximum,
    )
    distance_meters: int = Field(
        strict=True,
        ge=SCORING_CONFIGURATION.distance_meters_minimum,
        le=SCORING_CONFIGURATION.distance_meters_maximum,
    )
    projected_work_minutes: int = Field(
        strict=True,
        ge=SCORING_CONFIGURATION.projected_work_minutes_minimum,
        le=SCORING_CONFIGURATION.projected_work_minutes_maximum,
    )
    quality_rating_0_to_5: str | None = Field(
        default=None,
        max_length=SCORING_CONFIGURATION.maximum_decimal_text_length,
    )

    _uuid = field_validator("technician_id", mode="before")(_parse_uuid)

    @field_validator("quality_rating_0_to_5")
    @classmethod
    def valid_quality(cls, value: str | None) -> str | None:
        if value is None:
            return None
        _canonical_decimal_text(value)
        if not (
            SCORING_CONFIGURATION.quality_rating_minimum
            <= Decimal(value)
            <= SCORING_CONFIGURATION.quality_rating_maximum
        ):
            raise ValueError("quality rating must be between 0 and 5")
        return value

    def to_domain(self) -> ScoringTechnician:
        return ScoringTechnician(
            technician_id=self.technician_id,
            eta_minutes=self.eta_minutes,
            distance_meters=self.distance_meters,
            projected_work_minutes=self.projected_work_minutes,
            quality_rating_0_to_5=(
                None
                if self.quality_rating_0_to_5 is None
                else Decimal(self.quality_rating_0_to_5)
            ),
        )


class ScoringInputV1(FrozenScoringContract):
    schema_version: Literal["v1"] = "v1"
    configuration_version: Literal["scoring-v1"] = "scoring-v1"
    eligibility_evaluation_set_id: UUID
    sla_minutes: int = Field(
        strict=True,
        ge=SCORING_CONFIGURATION.sla_minutes_minimum,
        le=SCORING_CONFIGURATION.sla_minutes_maximum,
    )
    eligibility_output: EligibilityOutputV1
    technicians: tuple[ScoringTechnicianV1, ...] = Field(max_length=100)

    _evaluation_uuid = field_validator(
        "eligibility_evaluation_set_id", mode="before"
    )(_parse_uuid)
    @model_validator(mode="after")
    def canonical_roster(self):
        roster = [str(item.technician_id) for item in self.technicians]
        eligible = [
            str(item) for item in self.eligibility_output.eligible_technician_ids
        ]
        ineligible = [
            str(item) for item in self.eligibility_output.ineligible_technician_ids
        ]
        if roster != sorted(set(roster)):
            raise ValueError("technicians must be unique and sorted")
        if eligible != sorted(set(eligible)) or ineligible != sorted(set(ineligible)):
            raise ValueError("eligibility partitions must be unique and sorted")
        if set(eligible) & set(ineligible):
            raise ValueError("eligibility partitions must be disjoint")
        if set(roster) != set(eligible) | set(ineligible):
            raise ValueError("eligibility partitions must exactly match roster")
        distances = {
            item.technician_id: item.distance_meters
            for item in self.eligibility_output.candidates
        }
        eligibility_candidates = {
            item.technician_id: item
            for item in self.eligibility_output.candidates
        }
        if any(
            distances[item.technician_id] != item.distance_meters
            for item in self.technicians
        ):
            raise ValueError("scoring distance must match eligibility evidence")
        for item in self.technicians:
            evidence = eligibility_candidates[item.technician_id]
            shift = evidence.checks[2]
            maximum_workday = evidence.checks[3]
            if (
                item.eta_minutes != shift.evidence.travel_minutes
                or item.projected_work_minutes
                != maximum_workday.evidence.projected_workday_minutes
            ):
                raise ValueError(
                    "scoring travel/workload must match eligibility evidence"
                )
        return self

    def to_domain_eligible_technicians(self) -> tuple[ScoringTechnician, ...]:
        eligible = set(self.eligibility_output.eligible_technician_ids)
        return tuple(
            item.to_domain()
            for item in self.technicians
            if item.technician_id in eligible
        )


class ScoringQualitySupplementV1(FrozenScoringContract):
    technician_id: UUID
    quality_rating_0_to_5: str | None = Field(
        default=None,
        max_length=SCORING_CONFIGURATION.maximum_decimal_text_length,
    )

    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)
    _uuid = field_validator("technician_id", mode="before")(_parse_uuid)

    @field_validator("quality_rating_0_to_5")
    @classmethod
    def valid_quality(cls, value: str | None) -> str | None:
        return ScoringTechnicianV1.valid_quality(value)


class ScoringQualitySupplementsV1(FrozenScoringContract):
    technicians: tuple[ScoringQualitySupplementV1, ...] = Field(max_length=100)

    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)

    @model_validator(mode="after")
    def canonical_supplements(self):
        identifiers = [str(item.technician_id) for item in self.technicians]
        if identifiers != sorted(set(identifiers)):
            raise ValueError("quality supplements must be unique and sorted")
        return self


class ScoreComponentV1(FrozenScoringContract):
    name: Literal["sla", "proximity", "workload_balance", "quality", "memory"]
    raw_inputs: dict[str, str]
    normalized_value: str
    weight: str
    weighted_contribution: str
    configuration_version: Literal["scoring-v1"]

    _decimals = field_validator(
        "normalized_value", "weight", "weighted_contribution"
    )(_canonical_decimal_text)

    @model_validator(mode="after")
    def semantic_component(self):
        expected_keys = {
            "sla": {"eta_minutes", "sla_minutes"},
            "proximity": {"distance_meters", "distance_km"},
            "workload_balance": {
                "projected_work_minutes",
                "projected_work_hours",
                "maximum_workday_hours",
            },
            "quality": {"quality_rating_0_to_5", "fallback_used"},
            "memory": {"active_applicable_effect_count"},
        }[self.name]
        if set(self.raw_inputs) != expected_keys:
            raise ValueError("component raw evidence is incomplete")
        if any(
            not isinstance(value, str)
            or len(value)
            > SCORING_CONFIGURATION.maximum_decimal_text_length
            for value in self.raw_inputs.values()
        ):
            raise ValueError("component raw evidence is invalid")
        expected_weight = canonical_decimal(
            SCORING_CONFIGURATION.weight_for(self.name)
        )
        if self.weight != expected_weight:
            raise ValueError("component weight is inconsistent")
        with scoring_scope(SCORING_CONFIGURATION):
            value = Decimal(self.normalized_value)
            if not (
                SCORING_CONFIGURATION.clamp_minimum
                <= value
                <= SCORING_CONFIGURATION.clamp_maximum
            ):
                raise ValueError("component value is outside 0-100")
            expected_value = self._recompute_value()
            if value != expected_value:
                raise ValueError("component normalized value is inconsistent")
            if (
                Decimal(self.weighted_contribution)
                != value * Decimal(self.weight)
            ):
                raise ValueError("component contribution is inconsistent")
        return self

    @staticmethod
    def _integer_text(
        value: str,
        *,
        minimum: int,
        maximum: int,
    ) -> int:
        if not value.isascii() or not value.isdigit():
            raise ValueError("integer raw evidence is invalid")
        parsed = int(value)
        if value != str(parsed) or not (minimum <= parsed <= maximum):
            raise ValueError("integer raw evidence is noncanonical")
        return parsed

    def _recompute_value(self) -> Decimal:
        configuration = SCORING_CONFIGURATION
        if self.name == "sla":
            eta = self._integer_text(
                self.raw_inputs["eta_minutes"],
                minimum=configuration.eta_minutes_minimum,
                maximum=configuration.eta_minutes_maximum,
            )
            sla = self._integer_text(
                self.raw_inputs["sla_minutes"],
                minimum=configuration.sla_minutes_minimum,
                maximum=configuration.sla_minutes_maximum,
            )
            return clamp(
                configuration.clamp_maximum
                * (Decimal("1") - Decimal(eta) / Decimal(sla)),
                configuration,
            )
        if self.name == "proximity":
            distance_meters = self._integer_text(
                self.raw_inputs["distance_meters"],
                minimum=configuration.distance_meters_minimum,
                maximum=configuration.distance_meters_maximum,
            )
            distance_km = (
                Decimal(distance_meters)
                / configuration.distance_meters_per_km
            )
            if (
                self.raw_inputs["distance_km"]
                != canonical_decimal(distance_km)
            ):
                raise ValueError("distance conversion is inconsistent")
            return clamp(
                configuration.clamp_maximum
                - configuration.proximity_points_per_km * distance_km,
                configuration,
            )
        if self.name == "workload_balance":
            projected_minutes = self._integer_text(
                self.raw_inputs["projected_work_minutes"],
                minimum=configuration.projected_work_minutes_minimum,
                maximum=configuration.projected_work_minutes_maximum,
            )
            projected_hours = (
                Decimal(projected_minutes) / configuration.minutes_per_hour
            )
            if (
                self.raw_inputs["projected_work_hours"]
                != canonical_decimal(projected_hours)
                or self.raw_inputs["maximum_workday_hours"]
                != canonical_decimal(configuration.maximum_workday_hours)
            ):
                raise ValueError("workload conversion is inconsistent")
            return clamp(
                configuration.clamp_maximum
                * (
                    Decimal("1")
                    - projected_hours / configuration.maximum_workday_hours
                ),
                configuration,
            )
        if self.name == "quality":
            fallback = self.raw_inputs["fallback_used"]
            rating = self.raw_inputs["quality_rating_0_to_5"]
            if fallback == "true" and rating == "unavailable":
                return configuration.neutral_quality
            if fallback != "false":
                raise ValueError("quality fallback evidence is inconsistent")
            _canonical_decimal_text(rating)
            parsed = Decimal(rating)
            if not (
                configuration.quality_rating_minimum
                <= parsed
                <= configuration.quality_rating_maximum
            ):
                raise ValueError("quality evidence is outside bounds")
            return clamp(
                configuration.quality_points_per_rating * parsed,
                configuration,
            )
        if (
            self.raw_inputs["active_applicable_effect_count"]
            != str(configuration.memory_active_applicable_effect_count)
        ):
            raise ValueError("scoring-v1 memory must be neutral")
        return configuration.neutral_memory


class ScorePenaltyV1(FrozenScoringContract):
    name: Literal["distance_penalty"]
    version: Literal["scoring-v1"]
    raw_inputs: dict[str, str]
    amount: str
    impact: str

    _amount = field_validator("amount")(_canonical_decimal_text)

    @model_validator(mode="after")
    def semantic_penalty(self):
        if set(self.raw_inputs) != {"distance_km", "threshold_km", "cap"}:
            raise ValueError("distance penalty evidence is incomplete")
        for value in self.raw_inputs.values():
            _canonical_decimal_text(value)
        distance = Decimal(self.raw_inputs["distance_km"])
        threshold = Decimal(self.raw_inputs["threshold_km"])
        cap = Decimal(self.raw_inputs["cap"])
        if (
            threshold
            != SCORING_CONFIGURATION.distance_penalty_threshold_km
            or cap != SCORING_CONFIGURATION.distance_penalty_cap
            or self.impact
            != SCORING_CONFIGURATION.distance_penalty_impact
        ):
            raise ValueError("distance penalty registry values are inconsistent")
        expected = min(
            cap,
            max(SCORING_CONFIGURATION.clamp_minimum, distance - threshold),
        )
        if Decimal(self.amount) != expected:
            raise ValueError("distance penalty amount is inconsistent")
        return self


class ScoringWarningV1(FrozenScoringContract):
    code: Literal["SCORING_QUALITY_FALLBACK"]
    severity: Literal["warning"]
    technician_id: UUID
    source: Literal["technician.quality_rating_0_to_5"]
    quality: Literal["unavailable"]
    freshness: Literal["not_applicable"]
    fallback: Literal["50"]
    impact: str
    configuration_version: Literal["scoring-v1"]

    _uuid = field_validator("technician_id", mode="before")(_parse_uuid)

    @model_validator(mode="after")
    def stable_template(self):
        for field in (
            "code",
            "severity",
            "source",
            "quality",
            "freshness",
            "fallback",
            "impact",
        ):
            if getattr(self, field) != QUALITY_WARNING[field]:
                raise ValueError("scoring warning does not match registry")
        return self


class ScoredTechnicianV1(FrozenScoringContract):
    technician_id: UUID
    rank: int = Field(strict=True, ge=1, le=100)
    objective_score: str
    components: tuple[ScoreComponentV1, ...] = Field(
        min_length=5, max_length=5
    )
    penalties: tuple[ScorePenaltyV1, ...] = Field(
        min_length=1, max_length=1
    )
    warnings: tuple[ScoringWarningV1, ...] = Field(max_length=1)
    eta_minutes: int = Field(strict=True, ge=0, le=1440)

    _uuid = field_validator("technician_id", mode="before")(_parse_uuid)
    _score = field_validator("objective_score")(_canonical_decimal_text)

    @model_validator(mode="after")
    def canonical_evidence(self):
        if tuple(item.name for item in self.components) != COMPONENT_ORDER:
            raise ValueError("components must use registry order")
        if tuple(item.name for item in self.penalties) != PENALTY_ORDER:
            raise ValueError("penalties must use registry order")
        if any(item.technician_id != self.technician_id for item in self.warnings):
            raise ValueError("warning technician mismatch")
        quality = self.components[3]
        fallback_used = quality.raw_inputs["fallback_used"] == "true"
        if quality.raw_inputs["fallback_used"] not in {"true", "false"}:
            raise ValueError("quality fallback flag is invalid")
        if fallback_used != bool(self.warnings):
            raise ValueError("quality warning and fallback must match")
        if fallback_used and (
            quality.raw_inputs["quality_rating_0_to_5"] != "unavailable"
            or quality.normalized_value != "50"
        ):
            raise ValueError("quality fallback evidence is inconsistent")
        with scoring_scope(SCORING_CONFIGURATION):
            weighted_total = sum(
                (
                    Decimal(item.weighted_contribution)
                    for item in self.components
                ),
                Decimal("0"),
            )
            penalty_total = sum(
                (Decimal(item.amount) for item in self.penalties),
                Decimal("0"),
            )
            expected_score = clamp(
                weighted_total - penalty_total,
                SCORING_CONFIGURATION,
            )
            if Decimal(self.objective_score) != expected_score:
                raise ValueError("objective score is inconsistent")
        return self


class IneligibleScoringCandidateV1(FrozenScoringContract):
    technician_id: UUID
    eligibility: EligibilityCandidateV1

    _uuid = field_validator("technician_id", mode="before")(_parse_uuid)

    @model_validator(mode="after")
    def exact_evidence(self):
        if (
            self.eligibility.technician_id != self.technician_id
            or self.eligibility.eligible
        ):
            raise ValueError("ineligible evidence is inconsistent")
        return self


class ScoringOutputV1(FrozenScoringContract):
    schema_version: Literal["v1"] = "v1"
    configuration_version: Literal["scoring-v1"] = "scoring-v1"
    eligible_candidates: tuple[ScoredTechnicianV1, ...] = Field(max_length=100)
    ineligible_candidates: tuple[IneligibleScoringCandidateV1, ...] = Field(
        max_length=100
    )

    @model_validator(mode="after")
    def canonical_output(self):
        if [item.rank for item in self.eligible_candidates] != list(
            range(1, len(self.eligible_candidates) + 1)
        ):
            raise ValueError("ranks must be consecutive")
        eligible = [str(item.technician_id) for item in self.eligible_candidates]
        ineligible = [
            str(item.technician_id) for item in self.ineligible_candidates
        ]
        if len(eligible) != len(set(eligible)):
            raise ValueError("eligible candidates must be unique")
        if ineligible != sorted(set(ineligible)):
            raise ValueError("ineligible candidates must be unique and sorted")
        if set(eligible) & set(ineligible):
            raise ValueError("output partitions must be disjoint")
        ranking_keys = [
            (
                -Decimal(item.objective_score),
                -Decimal(item.components[0].normalized_value),
                -Decimal(item.components[3].normalized_value),
                item.eta_minutes,
                str(item.technician_id),
            )
            for item in self.eligible_candidates
        ]
        if ranking_keys != sorted(ranking_keys):
            raise ValueError("eligible candidates are not in ranking order")
        return self

    @classmethod
    def from_domain(
        cls,
        result: ScoringResult,
        *,
        ineligible_candidates: list[EligibilityCandidateV1],
    ) -> "ScoringOutputV1":
        return cls.model_validate(
            {
                "schema_version": result.schema_version,
                "configuration_version": result.configuration_version,
                "eligible_candidates": tuple(
                    {
                        "technician_id": str(candidate.technician_id),
                        "rank": candidate.rank,
                        "objective_score": canonical_decimal(
                            candidate.objective_score
                        ),
                        "components": tuple(
                            {
                                "name": component.name,
                                "raw_inputs": dict(component.raw_inputs),
                                "normalized_value": canonical_decimal(
                                    component.normalized_value
                                ),
                                "weight": canonical_decimal(component.weight),
                                "weighted_contribution": canonical_decimal(
                                    component.weighted_contribution
                                ),
                                "configuration_version": (
                                    component.configuration_version
                                ),
                            }
                            for component in candidate.components
                        ),
                        "penalties": tuple(
                            {
                                "name": penalty.name,
                                "version": penalty.version,
                                "raw_inputs": dict(penalty.raw_inputs),
                                "amount": canonical_decimal(penalty.amount),
                                "impact": penalty.impact,
                            }
                            for penalty in candidate.penalties
                        ),
                        "warnings": tuple(
                            {
                                "code": warning.code,
                                "severity": warning.severity,
                                "technician_id": str(warning.technician_id),
                                "source": warning.source,
                                "quality": warning.quality,
                                "freshness": warning.freshness,
                                "fallback": warning.fallback,
                                "impact": warning.impact,
                                "configuration_version": (
                                    warning.configuration_version
                                ),
                            }
                            for warning in candidate.warnings
                        ),
                        "eta_minutes": candidate.eta_minutes,
                    }
                    for candidate in result.candidates
                ),
                "ineligible_candidates": tuple(
                    {
                        "technician_id": str(item.technician_id),
                        "eligibility": item.model_dump(mode="json"),
                    }
                    for item in ineligible_candidates
                ),
            }
        )


def validate_output_against_input(
    input_model: ScoringInputV1,
    output_model: ScoringOutputV1,
) -> None:
    expected = ScoringOutputV1.from_domain(
        ScoringPolicy(SCORING_CONFIGURATION).evaluate(
            sla_minutes=input_model.sla_minutes,
            technicians=input_model.to_domain_eligible_technicians(),
        ),
        ineligible_candidates=[
            item
            for item in input_model.eligibility_output.candidates
            if not item.eligible
        ],
    )
    if output_model.model_dump(mode="json") != expected.model_dump(mode="json"):
        raise ValueError("scoring output is inconsistent with scoring input")
