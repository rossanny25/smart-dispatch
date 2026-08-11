from decimal import Decimal
from uuid import UUID

from app.domain.scoring.models import (
    ScoreComponent,
    ScoredTechnician,
    ScorePenalty,
    ScoringResult,
    ScoringTechnician,
    ScoringWarning,
)
from app.domain.scoring.rules import (
    QUALITY_WARNING,
    ScoringConfiguration,
    canonical_decimal,
)
from app.domain.scoring.arithmetic import clamp, scoring_context, scoring_scope


ZERO = Decimal("0")


class ScoringPolicy:
    def __init__(self, configuration: ScoringConfiguration) -> None:
        if sum((weight for _, weight in configuration.weights), ZERO) != Decimal(
            "1.00"
        ):
            raise ValueError("scoring weights must sum to exactly 1.00")
        if configuration.component_order != tuple(
            name for name, _ in configuration.weights
        ):
            raise ValueError("component order and weight order must match")
        if configuration.penalty_order != ("distance_penalty",):
            raise ValueError("scoring-v1 supports only distance_penalty")
        scoring_context(configuration)
        self._configuration = configuration

    def evaluate(
        self,
        *,
        sla_minutes: int,
        technicians: tuple[ScoringTechnician, ...],
    ) -> ScoringResult:
        if type(sla_minutes) is not int or not (
            self._configuration.sla_minutes_minimum
            <= sla_minutes
            <= self._configuration.sla_minutes_maximum
        ):
            raise ValueError("sla_minutes must be positive")
        if type(technicians) is not tuple or any(
            not isinstance(item, ScoringTechnician) for item in technicians
        ):
            raise TypeError("technicians must be an immutable scoring tuple")
        identifiers = [str(item.technician_id) for item in technicians]
        if len(identifiers) != len(set(identifiers)):
            raise ValueError("technician identifiers must be unique")
        with scoring_scope(self._configuration):
            unranked = [
                self._score(technician, sla_minutes)
                for technician in technicians
            ]
            ordered = sorted(
                unranked,
                key=lambda item: (
                    -item.objective_score,
                    -item.components[0].normalized_value,
                    -item.components[3].normalized_value,
                    item.eta_minutes,
                    str(item.technician_id),
                ),
            )
            ranked = tuple(
                ScoredTechnician(
                    technician_id=item.technician_id,
                    rank=index,
                    objective_score=item.objective_score,
                    components=item.components,
                    penalties=item.penalties,
                    warnings=item.warnings,
                    eta_minutes=item.eta_minutes,
                )
                for index, item in enumerate(ordered, start=1)
            )
        return ScoringResult(
            schema_version=self._configuration.contract_version,
            configuration_version=self._configuration.version,
            candidates=ranked,
        )

    def _score(
        self,
        technician: ScoringTechnician,
        sla_minutes: int,
    ) -> ScoredTechnician:
        if not isinstance(technician.technician_id, UUID):
            raise TypeError("technician_id must be a UUID")
        integer_fields = (
            (
                "eta_minutes",
                technician.eta_minutes,
                self._configuration.eta_minutes_minimum,
                self._configuration.eta_minutes_maximum,
            ),
            (
                "distance_meters",
                technician.distance_meters,
                self._configuration.distance_meters_minimum,
                self._configuration.distance_meters_maximum,
            ),
            (
                "projected_work_minutes",
                technician.projected_work_minutes,
                self._configuration.projected_work_minutes_minimum,
                self._configuration.projected_work_minutes_maximum,
            ),
        )
        for name, value, minimum, maximum in integer_fields:
            if type(value) is not int or not (minimum <= value <= maximum):
                raise TypeError(f"{name} must be a bounded integer")
        rating = technician.quality_rating_0_to_5
        if rating is not None and (
            not isinstance(rating, Decimal)
            or not (
                self._configuration.quality_rating_minimum
                <= rating
                <= self._configuration.quality_rating_maximum
            )
        ):
            raise ValueError("quality rating must be between 0 and 5")

        eta = Decimal(technician.eta_minutes)
        sla = Decimal(sla_minutes)
        distance_km = (
            Decimal(technician.distance_meters)
            / self._configuration.distance_meters_per_km
        )
        projected_hours = (
            Decimal(technician.projected_work_minutes)
            / self._configuration.minutes_per_hour
        )
        fallback_used = rating is None
        normalized = {
            "sla": clamp(
                self._configuration.clamp_maximum
                * (Decimal("1") - eta / sla),
                self._configuration,
            ),
            "proximity": clamp(
                self._configuration.clamp_maximum
                - self._configuration.proximity_points_per_km * distance_km,
                self._configuration,
            ),
            "workload_balance": clamp(
                self._configuration.clamp_maximum
                * (
                    Decimal("1")
                    - projected_hours
                    / self._configuration.maximum_workday_hours
                ),
                self._configuration,
            ),
            "quality": (
                self._configuration.neutral_quality
                if fallback_used
                else clamp(
                    self._configuration.quality_points_per_rating * rating,
                    self._configuration,
                )
            ),
            "memory": self._configuration.neutral_memory,
        }
        raw_inputs = {
            "sla": (
                ("eta_minutes", str(technician.eta_minutes)),
                ("sla_minutes", str(sla_minutes)),
            ),
            "proximity": (
                ("distance_meters", str(technician.distance_meters)),
                ("distance_km", canonical_decimal(distance_km)),
            ),
            "workload_balance": (
                ("projected_work_minutes", str(technician.projected_work_minutes)),
                ("projected_work_hours", canonical_decimal(projected_hours)),
                (
                    "maximum_workday_hours",
                    canonical_decimal(
                        self._configuration.maximum_workday_hours
                    ),
                ),
            ),
            "quality": (
                (
                    "quality_rating_0_to_5",
                    "unavailable" if rating is None else canonical_decimal(rating),
                ),
                ("fallback_used", "true" if fallback_used else "false"),
            ),
            "memory": (
                (
                    "active_applicable_effect_count",
                    str(
                        self._configuration
                        .memory_active_applicable_effect_count
                    ),
                ),
            ),
        }
        components = tuple(
            ScoreComponent(
                name=name,
                raw_inputs=raw_inputs[name],
                normalized_value=normalized[name],
                weight=self._configuration.weight_for(name),
                weighted_contribution=(
                    normalized[name] * self._configuration.weight_for(name)
                ),
                configuration_version=self._configuration.version,
            )
            for name in self._configuration.component_order
        )
        distance_penalty = min(
            self._configuration.distance_penalty_cap,
            max(
                self._configuration.clamp_minimum,
                distance_km
                - self._configuration.distance_penalty_threshold_km,
            ),
        )
        penalties = (
            ScorePenalty(
                name="distance_penalty",
                version=self._configuration.version,
                raw_inputs=(
                    ("distance_km", canonical_decimal(distance_km)),
                    (
                        "threshold_km",
                        canonical_decimal(
                            self._configuration.distance_penalty_threshold_km
                        ),
                    ),
                    (
                        "cap",
                        canonical_decimal(
                            self._configuration.distance_penalty_cap
                        ),
                    ),
                ),
                amount=distance_penalty,
                impact=self._configuration.distance_penalty_impact,
            ),
        )
        objective_score = clamp(
            sum(
                (component.weighted_contribution for component in components),
                ZERO,
            )
            - distance_penalty,
            self._configuration,
        )
        warnings = ()
        if fallback_used:
            warnings = (
                ScoringWarning(
                    code=QUALITY_WARNING["code"],
                    severity=QUALITY_WARNING["severity"],
                    technician_id=technician.technician_id,
                    source=QUALITY_WARNING["source"],
                    quality=QUALITY_WARNING["quality"],
                    freshness=QUALITY_WARNING["freshness"],
                    fallback=QUALITY_WARNING["fallback"],
                    impact=QUALITY_WARNING["impact"],
                    configuration_version=self._configuration.version,
                ),
            )
        return ScoredTechnician(
            technician_id=technician.technician_id,
            rank=0,
            objective_score=objective_score,
            components=components,
            penalties=penalties,
            warnings=warnings,
            eta_minutes=technician.eta_minutes,
        )
