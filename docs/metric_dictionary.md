# Merchandise Pulse — Metric Dictionary

## 1. Calculation conventions

- Metrics respect the active application filters unless explicitly stated.
- Ratio metrics are calculated as ratios of aggregate numerators and
  denominators, not averages of row-level percentages.
- Divide-by-zero results return null and display as `N/A`.
- Currency is Australian dollars excluding GST.
- A percentage-point change is distinct from a percentage change.
- Sales comparisons use matched prior periods where possible.
- Returns are already reflected in `units_sold`; `returns_units` is diagnostic.

## 2. Commercial metrics

### Net sales

```text
Net Sales = SUM(net_sales)
```

### Units sold

```text
Units Sold = SUM(units_sold)
```

### Gross profit

```text
Gross Profit = SUM(net_sales) - SUM(cost_of_goods)
```

Supplier funding is excluded from headline gross profit and added only in the
promotion investment view to avoid overstating ordinary product margin.

### Gross margin percentage

```text
Gross Margin % = Gross Profit / Net Sales
```

### Sales growth

```text
Sales Growth % = (Current Net Sales - Comparison Net Sales)
                 / Comparison Net Sales
```

The UI must label the comparison explicitly as previous period or previous year.

## 3. Inventory and availability metrics

### Availability percentage

```text
Availability % = SUM(in_stock_days for ranged records)
                 / (7 × COUNT(ranged store-SKU-week records))
```

Unranged records are excluded.

### Stock-out rate

```text
Stock-out Rate = 1 - Availability %
```

### Average weekly demand

For stock-cover calculations:

```text
Average Weekly Demand = mean units sold across the previous 8 complete weeks
```

Only ranged weeks are included. Current-week demand is excluded.

### Weeks of cover

At the latest selected weekly snapshot:

```text
Weeks of Cover = Closing Stock Units / Average Weekly Demand
```

If average demand is zero, weeks of cover is null rather than infinite.

### Estimated lost units

For a ranged store–SKU-week with fewer than seven in-stock days:

```text
Expected Daily Units = MAX(
    prior 8-week average units / 7,
    official forecast units / 7
)

Estimated Lost Units = Expected Daily Units × (7 - in_stock_days)
```

The result is floored at zero. Using the larger of recent demand and forecast
avoids automatically treating a constrained sales week as low demand.

### Estimated lost sales

```text
Estimated Lost Sales = Estimated Lost Units × Regular Unit Price
```

This is an opportunity estimate, not recognised revenue, and must be labelled as
such throughout the app.

## 4. Forecast metrics

`Actual` refers to `units_sold` at the same store–SKU-week grain.

### Forecast error

```text
Forecast Error = Forecast Units - Actual Units
```

Positive error represents over-forecasting.

### Forecast bias

```text
Forecast Bias % = SUM(Forecast Units - Actual Units) / SUM(Actual Units)
```

Interpretation:

- Positive: systematic over-forecasting
- Negative: systematic under-forecasting
- Near zero: balanced error, which does not necessarily mean accurate forecasts

### WMAPE

```text
WMAPE = SUM(ABS(Forecast Units - Actual Units)) / SUM(Actual Units)
```

### Forecast accuracy

```text
Forecast Accuracy % = MAX(0, 1 - WMAPE)
```

Forecast accuracy is capped at zero on the lower end for scorecard readability.
WMAPE remains available for detailed diagnosis.

## 5. Supplier service metrics

Purchase-order delivery events are first aggregated by `po_line_id`. Ordered
units are taken once per line, while received units are summed across its
delivery events.

### On-time flag

```text
On Time = final required receipt date <= expected delivery date
```

An order line is not on time if the quantity required to make it complete
arrives after the expected date. Open overdue lines are failures; open lines not
yet due are excluded.

### In-full flag

```text
In Full = total received units >= ordered units
```

### On-time delivery percentage

```text
On-time % = on-time completed/due order lines / completed/due order lines
```

### In-full percentage

```text
In-full % = in-full completed/due order lines / completed/due order lines
```

### OTIF

```text
OTIF % = order lines that are both on time and in full
         / completed/due order lines
```

OTIF is line-weighted for the MVP. A unit-weighted view may be added later but
must be named separately.

### Average delivery delay

```text
Delivery Delay Days = MAX(0, final required receipt date - expected date)
Average Delay = mean Delivery Delay Days across completed/due lines
```

## 6. Promotion metrics

Promotion analysis is performed at product and eligible-channel level.

### Baseline units

```text
Weekly Baseline Units = median weekly units across the 8 eligible,
non-promotional weeks immediately preceding the campaign

Campaign Baseline Units = Weekly Baseline Units × campaign duration in weeks
```

Median reduces distortion from isolated demand spikes. Promotions with fewer
than four eligible baseline weeks are marked `Insufficient baseline`.

### Incremental units

```text
Incremental Units = Promotional Units - Campaign Baseline Units
```

### Promotional uplift

```text
Promotional Uplift % = Incremental Units / Campaign Baseline Units
```

### Baseline unit margin

```text
Baseline Unit Margin = Regular Unit Price - Unit Cost
```

### Incremental gross profit before funding

```text
Promotion Gross Profit = Promotional Net Sales - Promotional Cost of Goods
Baseline Gross Profit = Campaign Baseline Units × Baseline Unit Margin

Incremental Gross Profit Before Funding =
    Promotion Gross Profit - Baseline Gross Profit
```

### Incremental gross profit after funding

```text
Incremental Gross Profit After Funding =
    Incremental Gross Profit Before Funding + Supplier Funding Allocation
```

### Return on trade investment

```text
ROTI = Incremental Gross Profit After Funding
       / (Discount Value + Supplier Funding Allocation)
```

If total investment is zero, ROTI is null. Both before-funding and after-funding
profit remain visible so funding does not conceal weak customer economics.

### Promotion stock-out exposure

```text
Promotion Stock-out Exposure = Estimated Lost Sales during promotion weeks
```

## 7. Supplier score

The supplier score combines normalised components on a 0–100 scale.

### Default weights

| Component | Weight | Direction |
|---|---:|---|
| OTIF | 25% | Higher is better |
| Availability | 20% | Higher is better |
| Sales growth | 15% | Higher is better |
| Gross margin percentage | 15% | Higher is better |
| Forecast accuracy | 10% | Higher is better |
| Promotion ROTI | 10% | Higher is better |
| Data-quality score | 5% | Higher is better |
| **Total** | **100%** | |

### Normalisation

Each component is scored relative to a floor and target:

```text
Component Score = CLAMP(
    100 × (Actual - Floor) / (Target - Floor),
    0,
    100
)
```

Default thresholds:

| Component | Floor | Target |
|---|---:|---:|
| OTIF | 75% | supplier target, default 95% |
| Availability | 85% | 97% |
| Sales growth | -10% | 5% |
| Gross margin | 20% | 40% |
| Forecast accuracy | 55% | 85% |
| Promotion ROTI | -0.25 | 0.50 |
| Data quality | 90% | 100% |

The sidebar may allow weight changes, but weights must always sum to 100%.
Thresholds remain fixed in the MVP so rankings are comparable between users.

### Composite calculation

```text
Supplier Score = SUM(Component Score × Component Weight)
```

If a component is genuinely not applicable, its weight is redistributed
proportionally across available components. Missing data caused by a quality
failure is not treated as not applicable; it reduces the data-quality score.

### Performance bands

| Score | Band |
|---:|---|
| 85–100 | Leading |
| 70–84.99 | Performing |
| 55–69.99 | Watch |
| Below 55 | Action required |

## 8. Data-quality score

The score starts at 100 and applies capped penalties over the selected period:

| Failure | Penalty |
|---|---:|
| Duplicate business-grain record | 5 points each, capped at 25 |
| Missing dimension mapping | 5 points each, capped at 25 |
| Invalid negative value | 3 points each, capped at 15 |
| Invalid date sequence | 3 points each, capped at 15 |
| Stale required fact table | 20 points |

```text
Data-quality Score = MAX(0, 100 - total penalties)
```

The validation page will also show raw failure counts so the score does not hide
the nature of the problem.

## 9. Headline targets

| Metric | Default target |
|---|---:|
| Sales growth | >= 5% |
| Gross margin | >= 40% |
| Availability | >= 97% |
| OTIF | >= 95% or supplier-specific target |
| Forecast accuracy | >= 85% |
| Absolute forecast bias | <= 5% |
| Promotion ROTI | >= 0.50 |
| Data-quality score | >= 98 |

Targets are fictional portfolio assumptions, not Wesfarmers Health targets.

## 10. Metric ownership in code

Step 4 will implement each formula once in a dedicated metrics module. Streamlit
pages will consume those functions and must not duplicate business logic.

Planned separation:

```text
src/
├── metrics/
│   ├── commercial.py
│   ├── inventory.py
│   ├── forecast.py
│   ├── supplier.py
│   └── promotion.py
├── validation.py
└── scoring.py
```

Every metric with non-trivial logic will have unit tests covering normal cases,
zero denominators, missing values, and aggregation behaviour.
