from __future__ import annotations

from collections.abc import Mapping


DEFAULT_WEIGHTS = {
    "otif": 0.25,
    "availability": 0.20,
    "sales_growth": 0.15,
    "gross_margin": 0.15,
    "forecast_accuracy": 0.10,
    "promotion_roti": 0.10,
    "data_quality": 0.05,
}

THRESHOLDS = {
    "otif": (0.75, 0.95),
    "availability": (0.85, 0.97),
    "sales_growth": (-0.10, 0.05),
    "gross_margin": (0.20, 0.40),
    "forecast_accuracy": (0.55, 0.85),
    "promotion_roti": (-0.25, 0.50),
    "data_quality": (0.90, 1.00),
}


def component_score(actual: float, floor: float, target: float) -> float:
    if target <= floor:
        raise ValueError("Target must be greater than floor")
    return max(0.0, min(100.0, 100 * (actual - floor) / (target - floor)))


def supplier_score(
    values: Mapping[str, float | None],
    weights: Mapping[str, float] = DEFAULT_WEIGHTS,
) -> float:
    if abs(sum(weights.values()) - 1.0) > 1e-9:
        raise ValueError("Supplier score weights must sum to 1")
    available = {name: value for name, value in values.items() if value is not None}
    available_weight = sum(weights[name] for name in available)
    if not available or available_weight == 0:
        raise ValueError("At least one score component is required")
    result = 0.0
    for name, actual in available.items():
        floor, target = THRESHOLDS[name]
        adjusted_weight = weights[name] / available_weight
        result += component_score(float(actual), floor, target) * adjusted_weight
    return result


def performance_band(score: float) -> str:
    if score >= 85:
        return "Leading"
    if score >= 70:
        return "Performing"
    if score >= 55:
        return "Watch"
    return "Action required"

