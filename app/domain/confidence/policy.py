from datetime import UTC, datetime
from decimal import (
    Context,
    Decimal,
    DivisionByZero,
    FloatOperation,
    InvalidOperation,
    Overflow,
    ROUND_HALF_EVEN,
    localcontext,
)
from uuid import UUID

from app.domain.confidence.models import (
    ConfidenceCandidate,
    ConfidenceExplanation,
    ConfidenceFactor,
    ConfidenceResult,
    ConfidenceWarning,
    GpsObservation,
    SourceObservation,
    SourceQuality,
)
from app.domain.confidence.rules import ConfidenceConfiguration
from app.domain.scoring.rules import canonical_decimal


ZERO = Decimal("0")


def _clamp(value: Decimal, configuration: ConfidenceConfiguration) -> Decimal:
    return min(
        configuration.clamp_maximum,
        max(configuration.clamp_minimum, value),
    )


def confidence_label(
    value: Decimal, configuration: ConfidenceConfiguration
) -> str:
    if value < configuration.low_upper_exclusive:
        return "low"
    if value < configuration.medium_upper_exclusive:
        return "medium"
    return "high"


class ConfidencePolicy:
    def __init__(self, configuration: ConfidenceConfiguration) -> None:
        if sum((weight for _, weight in configuration.weights), ZERO) != Decimal(
            "1.00"
        ):
            raise ValueError("confidence weights must sum to exactly 1.00")
        if tuple(name for name, _ in configuration.weights) != configuration.factor_order:
            raise ValueError("factor and weight order must match")
        if configuration.decimal_rounding != "ROUND_HALF_EVEN":
            raise ValueError("confidence-v1 requires ROUND_HALF_EVEN")
        self._configuration = configuration

    def evaluate(
        self,
        *,
        evaluated_at: datetime,
        candidates: tuple[ConfidenceCandidate, ...],
        gps_observations: tuple[GpsObservation, ...],
        traffic: SourceObservation,
        weather: SourceObservation,
        active_supporting_episode_count: int,
    ) -> ConfidenceResult:
        self._validate(
            evaluated_at,
            candidates,
            gps_observations,
            traffic,
            weather,
            active_supporting_episode_count,
        )
        if not candidates:
            return ConfidenceResult(
                schema_version=self._configuration.contract_version,
                configuration_version=self._configuration.version,
                candidates=(),
                recommended_technician_id=None,
                factors=(),
                sources=(),
                uncertain_conditions=(),
                warnings=(),
                value=None,
                label=None,
                explanation=ConfidenceExplanation(
                    template_id=(
                        "CONFIDENCE_UNAVAILABLE_NO_ELIGIBLE_CANDIDATE"
                    ),
                    leading_technician_id=None,
                    leading_objective_score=None,
                    confidence_value=None,
                    confidence_label=None,
                    first_score=None,
                    second_score=None,
                    limiting_factors=(),
                    warning_codes=(),
                ),
            )

        context = Context(
            prec=self._configuration.decimal_precision,
            rounding=ROUND_HALF_EVEN,
        )
        for signal in (
            InvalidOperation,
            DivisionByZero,
            Overflow,
            FloatOperation,
        ):
            context.traps[signal] = True
        with localcontext(context):
            sources = self._sources(
                evaluated_at,
                gps_observations,
                traffic,
                weather,
                active_supporting_episode_count,
            )
            data_quality = sum((item.value for item in sources), ZERO) / Decimal(
                len(sources)
            )
            historical = min(
                self._configuration.historical_cap,
                self._configuration.historical_multiplier
                * Decimal(active_supporting_episode_count),
            )
            if len(candidates) == 1:
                margin = self._configuration.single_candidate_margin
            else:
                difference = (
                    candidates[0].objective_score
                    - candidates[1].objective_score
                )
                if difference < ZERO:
                    raise ValueError("ranked scores produce a negative margin")
                margin = min(
                    self._configuration.margin_cap,
                    self._configuration.margin_multiplier * difference,
                )
            conditions = self._conditions(sources)
            certainty = _clamp(
                self._configuration.clamp_maximum
                - self._configuration.uncertain_condition_deduction
                * Decimal(len(conditions)),
                self._configuration,
            )
            values = {
                "data_quality": data_quality,
                "historical_evidence": historical,
                "score_margin": margin,
                "condition_certainty": certainty,
            }
            raw_inputs = {
                "data_quality": (
                    ("applicable_source_count", str(len(sources))),
                    (
                        "source_quality_values",
                        ",".join(canonical_decimal(item.value) for item in sources),
                    ),
                ),
                "historical_evidence": (
                    (
                        "active_supporting_episode_count",
                        str(active_supporting_episode_count),
                    ),
                ),
                "score_margin": (
                    ("eligible_candidate_count", str(len(candidates))),
                    ("first_score", canonical_decimal(candidates[0].objective_score)),
                    (
                        "second_score",
                        (
                            "unavailable"
                            if len(candidates) == 1
                            else canonical_decimal(candidates[1].objective_score)
                        ),
                    ),
                ),
                "condition_certainty": (
                    ("uncertain_condition_count", str(len(conditions))),
                    ("conditions", ",".join(conditions)),
                ),
            }
            factors = tuple(
                ConfidenceFactor(
                    name=name,
                    raw_inputs=raw_inputs[name],
                    value=values[name],
                    weight=self._configuration.weight_for(name),
                    weighted_contribution=(
                        values[name] * self._configuration.weight_for(name)
                    ),
                    configuration_version=self._configuration.version,
                )
                for name in self._configuration.factor_order
            )
            value = _clamp(
                sum(
                    (factor.weighted_contribution for factor in factors),
                    ZERO,
                ),
                self._configuration,
            )
        label = confidence_label(value, self._configuration)
        warnings = self._warnings(sources)
        limiting_factors = tuple(
            item.name
            for item in factors
            if item.value < self._configuration.clamp_maximum
        )
        return ConfidenceResult(
            schema_version=self._configuration.contract_version,
            configuration_version=self._configuration.version,
            candidates=candidates,
            recommended_technician_id=candidates[0].technician_id,
            factors=factors,
            sources=sources,
            uncertain_conditions=conditions,
            warnings=warnings,
            value=value,
            label=label,
            explanation=ConfidenceExplanation(
                template_id="CONFIDENCE_SUMMARY",
                leading_technician_id=candidates[0].technician_id,
                leading_objective_score=candidates[0].objective_score,
                confidence_value=value,
                confidence_label=label,
                first_score=candidates[0].objective_score,
                second_score=(
                    None if len(candidates) == 1 else candidates[1].objective_score
                ),
                limiting_factors=limiting_factors,
                warning_codes=tuple(item.code for item in warnings),
            ),
        )

    def _validate(
        self,
        evaluated_at: datetime,
        candidates: tuple[ConfidenceCandidate, ...],
        gps_observations: tuple[GpsObservation, ...],
        traffic: SourceObservation,
        weather: SourceObservation,
        episodes: int,
    ) -> None:
        self._require_utc(evaluated_at)
        if type(candidates) is not tuple or type(gps_observations) is not tuple:
            raise TypeError("candidate and GPS inputs must be tuples")
        if any(not isinstance(item, ConfidenceCandidate) for item in candidates):
            raise TypeError("candidates must contain ConfidenceCandidate values")
        if any(not isinstance(item, GpsObservation) for item in gps_observations):
            raise TypeError("GPS inputs must contain GpsObservation values")
        if not isinstance(traffic, SourceObservation) or not isinstance(
            weather, SourceObservation
        ):
            raise TypeError("environment inputs must be SourceObservation values")
        if type(episodes) is not int or not (
            0 <= episodes <= self._configuration.maximum_episode_count
        ):
            raise ValueError("episode count must be an integer from 0 to 10000")
        if traffic.source != "traffic" or weather.source != "weather":
            raise ValueError("environment source identity is invalid")
        if tuple(candidate.rank for candidate in candidates) != tuple(
            range(1, len(candidates) + 1)
        ):
            raise ValueError("candidate ranks must be consecutive")
        for candidate in candidates:
            if (
                not isinstance(candidate.technician_id, UUID)
                or type(candidate.rank) is not int
            ):
                raise TypeError("candidate UUID and rank types are invalid")
            if not isinstance(candidate.objective_score, Decimal):
                raise TypeError("objective score must be Decimal")
            if not ZERO <= candidate.objective_score <= Decimal("100"):
                raise ValueError("objective score is outside 0-100")
        expected = tuple(candidate.technician_id for candidate in candidates)
        actual = tuple(item.technician_id for item in gps_observations)
        if expected != actual:
            raise ValueError("GPS roster must match ranked candidate order")
        for observed in (*gps_observations, traffic, weather):
            if isinstance(observed, GpsObservation) and not isinstance(
                observed.technician_id, UUID
            ):
                raise TypeError("GPS technician_id must be UUID")
            if observed.observed_at is not None:
                self._require_utc(observed.observed_at)
                if observed.observed_at > evaluated_at:
                    raise ValueError("source timestamp cannot be in the future")

    @staticmethod
    def _require_utc(value: datetime) -> None:
        if (
            not isinstance(value, datetime)
            or value.tzinfo is None
            or value.utcoffset() != UTC.utcoffset(value)
        ):
            raise ValueError("timestamp must be timezone-aware UTC")

    def _quality(
        self,
        *,
        source: str,
        evaluated_at: datetime,
        observed_at: datetime | None,
        technician_id=None,
        last_known_zone: str | None = None,
    ) -> SourceQuality:
        if observed_at is None:
            age = None
        else:
            elapsed = evaluated_at - observed_at
            total_microseconds = (
                (elapsed.days * 86_400 + elapsed.seconds) * 1_000_000
                + elapsed.microseconds
            )
            age = Decimal(total_microseconds) / Decimal("60000000")
        current_max = (
            self._configuration.gps_current_max_minutes
            if source == "gps"
            else self._configuration.environment_current_max_minutes
        )
        stale_max = (
            self._configuration.gps_stale_max_minutes
            if source == "gps"
            else self._configuration.environment_stale_max_minutes
        )
        quality = (
            "unavailable"
            if age is None or age > stale_max
            else ("current" if age <= current_max else "stale")
        )
        fallback = "none"
        fallback_quality = "not_applicable"
        if quality == "unavailable":
            if source == "gps" and last_known_zone:
                fallback = f"last_known_zone:{last_known_zone}"
                fallback_quality = "estimated"
            elif source == "traffic":
                fallback = self._configuration.traffic_default
                fallback_quality = "defaulted"
            elif source == "weather":
                fallback = self._configuration.weather_default
                fallback_quality = "defaulted"
            elif source == "gps":
                fallback = self._configuration.warning_rule("gps").unavailable_fallback
                fallback_quality = "unavailable"
        rule = self._configuration.warning_rule(source)
        return SourceQuality(
            source=source,
            technician_id=technician_id,
            affected_field=rule.affected_field,
            observed_at=observed_at,
            age_minutes=age,
            quality=quality,
            value=self._configuration.quality_value(quality),
            fallback=fallback,
            fallback_quality=fallback_quality,
        )

    def _sources(
        self,
        evaluated_at,
        gps_observations,
        traffic,
        weather,
        episodes,
    ) -> tuple[SourceQuality, ...]:
        items = [
            self._quality(
                source="gps",
                evaluated_at=evaluated_at,
                observed_at=item.observed_at,
                technician_id=item.technician_id,
                last_known_zone=item.last_known_zone,
            )
            for item in gps_observations
        ]
        items.extend(
            [
                self._quality(
                    source="traffic",
                    evaluated_at=evaluated_at,
                    observed_at=traffic.observed_at,
                ),
                self._quality(
                    source="weather",
                    evaluated_at=evaluated_at,
                    observed_at=weather.observed_at,
                ),
                SourceQuality(
                    source="historical_evidence",
                    technician_id=None,
                    affected_field="history.active_supporting_episode_count",
                    observed_at=None,
                    age_minutes=None,
                    quality="current" if episodes else "unavailable",
                    value=self._configuration.quality_value(
                        "current" if episodes else "unavailable"
                    ),
                    fallback="none" if episodes else "no_history",
                    fallback_quality=(
                        "not_applicable" if episodes else "unavailable"
                    ),
                ),
            ]
        )
        return tuple(items)

    @staticmethod
    def _conditions(sources: tuple[SourceQuality, ...]) -> tuple[str, ...]:
        result = set()
        for item in sources:
            if item.source == "gps" and item.fallback.startswith("last_known_zone:"):
                result.add("gps_estimated")
            elif item.source == "traffic" and item.quality == "unavailable":
                result.add("traffic_defaulted")
            elif item.source == "weather" and item.quality == "unavailable":
                result.add("weather_defaulted")
            elif (
                item.source == "historical_evidence"
                and item.quality == "unavailable"
            ):
                result.add("historical_evidence_missing")
        return tuple(sorted(result))

    def _warnings(
        self, sources: tuple[SourceQuality, ...]
    ) -> tuple[ConfidenceWarning, ...]:
        warnings = []
        for item in sources:
            if item.quality == "current":
                continue
            rule = self._configuration.warning_rule(item.source)
            warnings.append(
                ConfidenceWarning(
                    code=f"{rule.code_prefix}_{item.quality.upper()}",
                    severity="warning",
                    source=item.source,
                    affected_field=item.affected_field,
                    quality=item.quality,
                    freshness=item.quality,
                    age_minutes=item.age_minutes,
                    fallback=item.fallback,
                    fallback_quality=item.fallback_quality,
                    impact=rule.impact,
                    technician_id=item.technician_id,
                    configuration_version=self._configuration.version,
                )
            )
        order = {name: index for index, name in enumerate(self._configuration.source_order)}
        return tuple(
            sorted(
                warnings,
                key=lambda item: (
                    order[item.source],
                    "" if item.technician_id is None else str(item.technician_id),
                    item.affected_field,
                    item.code,
                ),
            )
        )
