# models and tiny stats helper to keep data shapes explicit and reusable across the app

from dataclasses import dataclass
from typing import List

@dataclass(frozen=True)
class Forecast:
    # immutable value object for a single day max temperature
    max_temp: float

@dataclass(frozen=True)
class CityResult:
    # output value object used by consumers and cli
    city: str
    average_max_temp: float

def mean(values: List[float]) -> float:
    # simple average that returns NaN on empty input to avoid zero division
    return sum(values) / len(values) if values else float("nan")
