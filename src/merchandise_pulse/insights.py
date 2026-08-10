from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"


@dataclass(frozen=True)
class InsightBrief:
    headline: str
    situation: str
    interpretation: str
    recommendation: str
    confidence: str
    evidence_ids: list[str]


def build_evidence(
    *,
    net_sales: float,
    sales_growth: float | None,
    gross_margin_pct: float | None,
    availability_pct: float | None,
    forecast_accuracy_pct: float | None,
    forecast_bias_pct: float | None,
    otif_pct: float | None,
    lost_sales: float,
    weakest_supplier: str | None,
    weakest_supplier_otif: float | None,
    period: str,
) -> list[dict[str, Any]]:
    """Create the small, aggregated fact set supplied to the language model."""
    facts = [
        {"id": "E1", "metric": "Net sales", "value": round(net_sales, 2), "display": f"${net_sales:,.0f}"},
        {"id": "E2", "metric": "Estimated lost-sales exposure", "value": round(lost_sales, 2), "display": f"${lost_sales:,.0f}"},
    ]
    optional = [
        ("E3", "Sales growth", sales_growth, ".1%"),
        ("E4", "Gross margin", gross_margin_pct, ".1%"),
        ("E5", "Availability", availability_pct, ".1%"),
        ("E6", "Forecast accuracy", forecast_accuracy_pct, ".1%"),
        ("E7", "Forecast bias", forecast_bias_pct, ".1%"),
        ("E8", "Supplier OTIF", otif_pct, ".1%"),
        ("E9", f"{weakest_supplier} OTIF" if weakest_supplier else "Lowest supplier OTIF", weakest_supplier_otif, ".1%"),
    ]
    for evidence_id, metric, value, format_spec in optional:
        if value is not None:
            numeric_value = float(value)
            if abs(numeric_value) < 0.0005:
                numeric_value = 0.0
            facts.append({
                "id": evidence_id,
                "metric": metric,
                "value": round(numeric_value, 4),
                "display": format(numeric_value, format_spec),
            })
    for fact in facts:
        fact["period"] = period
    return facts


def template_brief(evidence: list[dict[str, Any]]) -> InsightBrief:
    by_id = {item["id"]: item for item in evidence}
    supplier = by_id.get("E9") or by_id.get("E8")
    lost = by_id["E2"]
    accuracy = by_id.get("E6")

    if supplier and supplier["value"] < 0.90:
        headline = "Supplier service is the clearest near-term intervention"
        situation = (
            f"The lowest supplier service result is {supplier['display']}, while estimated "
            f"lost-sales exposure is {lost['display']}."
        )
        interpretation = "The two measures point to a service constraint worth investigating, but do not prove the supplier caused all lost sales."
        recommendation = "Review late and incomplete order lines, then match affected SKUs to store-level availability before agreeing recovery dates."
        ids = [supplier["id"], "E2"]
    elif accuracy and accuracy["value"] < 0.80:
        headline = "Forecast performance should lead the next merchandise review"
        situation = f"Forecast accuracy is {accuracy['display']} and estimated lost-sales exposure is {lost['display']}."
        interpretation = "Accuracy is below a practical 80% review threshold, suggesting that exceptions should be prioritised at SKU level."
        recommendation = "Separate over-forecast and under-forecast SKUs, then adjust replenishment only after checking promotion and supply effects."
        ids = ["E6", "E2"]
    else:
        availability = by_id.get("E5")
        headline = "Trading is stable; focus on the remaining availability exceptions"
        situation = f"Estimated lost-sales exposure is {lost['display']}" + (
            f" with availability at {availability['display']}." if availability else "."
        )
        interpretation = "The aggregate view is healthy, although individual SKU and supplier exceptions may still be commercially material."
        recommendation = "Work through the highest-value exceptions in the Action Centre and confirm an owner for each item."
        ids = ["E2"] + (["E5"] if availability else [])

    return InsightBrief(headline, situation, interpretation, recommendation, "Medium", ids)


def _schema() -> dict[str, Any]:
    fields = {
        "headline": {"type": "string"},
        "situation": {"type": "string"},
        "interpretation": {"type": "string"},
        "recommendation": {"type": "string"},
        "confidence": {"type": "string", "enum": ["High", "Medium", "Low"]},
        "evidence_ids": {"type": "array", "items": {"type": "string"}, "minItems": 1},
    }
    return {"type": "object", "properties": fields, "required": list(fields), "additionalProperties": False}


def _request_openrouter(body: dict[str, Any], *, api_key: str, timeout: int) -> dict[str, Any]:
    request = Request(
        OPENROUTER_URL,
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "http://localhost:8501",
            "X-Title": "Merchandise Pulse",
        },
        method="POST",
    )
    try:
        with urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        error = RuntimeError(f"OpenRouter returned HTTP {exc.code}: {detail[:300]}")
        error.status_code = exc.code
        raise error from exc
    except (URLError, TimeoutError) as exc:
        raise RuntimeError(f"OpenRouter request failed: {exc}") from exc


def _parse_brief_content(content: str) -> InsightBrief:
    try:
        parsed = json.loads(content)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", content, flags=re.DOTALL)
        if not match:
            raise RuntimeError("The model did not return a JSON insight brief.")
        try:
            parsed = json.loads(match.group(0))
        except json.JSONDecodeError as exc:
            raise RuntimeError("The model returned malformed JSON.") from exc

    try:
        brief = InsightBrief(**parsed)
    except (TypeError, KeyError) as exc:
        raise RuntimeError("The model returned an incomplete insight brief.") from exc
    if brief.confidence not in {"High", "Medium", "Low"}:
        raise RuntimeError("The model returned an invalid confidence level.")
    if not all([brief.headline, brief.situation, brief.interpretation, brief.recommendation]):
        raise RuntimeError("The model returned an incomplete insight brief.")
    return brief


def generate_openrouter_brief(
    evidence: list[dict[str, Any]],
    *,
    api_key: str,
    model: str,
    audience: str,
    timeout: int = 30,
) -> InsightBrief:
    allowed_ids = {item["id"] for item in evidence}
    prompt = (
        f"Prepare a concise weekly merchandise insight brief for a {audience} audience. "
        "Use only the evidence supplied. Do not invent causes, targets, events or financial impacts. "
        "Keep facts separate from interpretation. The recommendation must be a practical next step. "
        "Cite the relevant evidence IDs in evidence_ids.\n\n"
        f"Return one JSON object matching this schema exactly:\n{json.dumps(_schema())}\n\n"
        f"EVIDENCE:\n{json.dumps(evidence, indent=2)}"
    )
    base_body = {
        "model": model,
        "temperature": 0.2,
        "max_completion_tokens": 550,
        "messages": [
            {"role": "system", "content": "You are a careful retail merchandise analyst. Return valid JSON only."},
            {"role": "user", "content": prompt},
        ],
    }
    structured_body = {
        **base_body,
        "response_format": {
            "type": "json_schema",
            "json_schema": {"name": "merchandise_insight_brief", "strict": True, "schema": _schema()},
        },
        "provider": {"require_parameters": True},
    }
    try:
        result = _request_openrouter(structured_body, api_key=api_key, timeout=timeout)
    except RuntimeError as exc:
        if getattr(exc, "status_code", None) not in {400, 404}:
            raise
        result = _request_openrouter(base_body, api_key=api_key, timeout=timeout)

    try:
        content = result["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise RuntimeError("OpenRouter returned an unexpected response.") from exc
    brief = _parse_brief_content(content)

    if not brief.evidence_ids or not set(brief.evidence_ids).issubset(allowed_ids):
        raise RuntimeError("The generated brief cited evidence that was not supplied.")
    return brief


def brief_as_markdown(brief: InsightBrief, evidence: list[dict[str, Any]], *, mode: str) -> str:
    lines = [
        f"# {brief.headline}", "", f"**Mode:** {mode}", "",
        "## Situation", "", brief.situation, "", "## Interpretation", "", brief.interpretation, "",
        "## Recommended action", "", brief.recommendation, "", f"**Confidence:** {brief.confidence}", "",
        "## Supporting evidence", "",
    ]
    by_id = {item["id"]: item for item in evidence}
    for evidence_id in brief.evidence_ids:
        item = by_id[evidence_id]
        lines.append(f"- {evidence_id}: {item['metric']} — {item['display']} ({item['period']})")
    lines.extend(["", "_Generated from synthetic portfolio data. Interpretation should be reviewed by a merchandise analyst._", ""])
    return "\n".join(lines)


def brief_to_dict(brief: InsightBrief) -> dict[str, Any]:
    return asdict(brief)
