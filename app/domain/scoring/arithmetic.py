from contextlib import contextmanager
from decimal import (
    Context,
    DivisionByZero,
    FloatOperation,
    InvalidOperation,
    Overflow,
    ROUND_HALF_EVEN,
    localcontext,
)
from typing import Iterator

from app.domain.scoring.rules import ScoringConfiguration


ROUNDING_MODES = {
    "ROUND_HALF_EVEN": ROUND_HALF_EVEN,
}


def scoring_context(configuration: ScoringConfiguration) -> Context:
    try:
        rounding = ROUNDING_MODES[configuration.decimal_rounding]
    except KeyError as error:
        raise ValueError("unsupported scoring Decimal rounding mode") from error
    context = Context(
        prec=configuration.decimal_precision,
        rounding=rounding,
    )
    for signal in (
        InvalidOperation,
        DivisionByZero,
        Overflow,
        FloatOperation,
    ):
        context.traps[signal] = True
    return context


@contextmanager
def scoring_scope(
    configuration: ScoringConfiguration,
) -> Iterator[Context]:
    with localcontext(scoring_context(configuration)) as context:
        yield context


def clamp(value, configuration: ScoringConfiguration):
    return min(
        configuration.clamp_maximum,
        max(configuration.clamp_minimum, value),
    )

