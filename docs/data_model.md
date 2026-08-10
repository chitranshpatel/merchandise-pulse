# Merchandise Pulse — Data Model Contract

## 1. Modelling principles

The application uses a small dimensional model with conformed product, store,
supplier, promotion, and calendar dimensions. Facts retain the lowest useful
business grain so that aggregate dashboard results can be traced back to their
drivers.

Design rules:

- Surrogate-style string identifiers are stable and human-readable.
- Monetary values are in Australian dollars and exclude GST.
- Dates use ISO format and weeks start on Monday.
- Percentages are stored as decimals between 0 and 1 unless noted otherwise.
- All application metrics are calculated from facts rather than embedded in raw
  source files.
- No customer, patient, prescription, or personally identifiable data exists.

## 2. Relationship overview

```text
dim_date ───────────────┬──────── fact_sales_weekly
                       ├──────── fact_inventory_weekly
                       └──────── fact_forecast_weekly

dim_store ──────────────┬──────── fact_sales_weekly
                       ├──────── fact_inventory_weekly
                       └──────── fact_forecast_weekly

dim_product ────────────┬──────── fact_sales_weekly
      │                ├──────── fact_inventory_weekly
      │                ├──────── fact_forecast_weekly
      │                ├──────── fact_purchase_order_lines
      │                └──────── bridge_promotion_products
      │
      └── supplier_id ──────────── dim_supplier

dim_promotion ──────────────────── bridge_promotion_products
```

The promotion bridge allows one promotion to contain many products and a
product to participate in many promotions over time.

## 3. Dimensions

### 3.1 `dim_date`

**Grain:** one row per calendar date.

| Column | Type | Constraint | Description |
|---|---|---|---|
| `date` | date | primary key | Calendar date |
| `week_start` | date | not null | Monday containing the date |
| `week_end` | date | not null | Sunday containing the date |
| `year` | integer | not null | Calendar year |
| `quarter` | string | not null | `Q1`–`Q4` |
| `month_number` | integer | 1–12 | Calendar month |
| `month_name` | string | not null | Full month name |
| `week_of_year` | integer | 1–53 | ISO week number |
| `season` | string | controlled value | Australian season |

The weekly fact tables join using `week_start`. The daily dimension remains
useful for validating promotion and purchase-order dates.

### 3.2 `dim_supplier`

**Grain:** one row per supplier.

| Column | Type | Constraint | Description |
|---|---|---|---|
| `supplier_id` | string | primary key | Stable identifier such as `SUP001` |
| `supplier_name` | string | unique, not null | Fictional supplier name |
| `supplier_tier` | string | `Strategic`, `Core`, `Emerging` | Relationship segment |
| `primary_category` | string | not null | Main supplied category |
| `standard_lead_time_days` | integer | positive | Contracted lead time |
| `otif_target` | decimal | 0–1 | Supplier-specific target |
| `active_flag` | boolean | not null | Current supplier status |

### 3.3 `dim_product`

**Grain:** one row per SKU.

| Column | Type | Constraint | Description |
|---|---|---|---|
| `product_id` | string | primary key | Stable identifier such as `SKU0001` |
| `product_name` | string | not null | Fictional product name |
| `brand` | string | not null | Fictional brand |
| `category` | string | not null | Merchandise category |
| `subcategory` | string | not null | Merchandise subcategory |
| `supplier_id` | string | foreign key | Owning supplier |
| `unit_cost` | decimal | non-negative | Standard landed unit cost |
| `regular_unit_price` | decimal | positive | Standard selling price |
| `launch_date` | date | not null | Product ranging date |
| `private_label_flag` | boolean | not null | Private-label indicator |
| `active_flag` | boolean | not null | Current range status |

Supplier history is not modelled as a slowly changing dimension in the MVP.

### 3.4 `dim_store`

**Grain:** one row per physical store or digital fulfilment node.

| Column | Type | Constraint | Description |
|---|---|---|---|
| `store_id` | string | primary key | Identifier such as `STR001` |
| `store_name` | string | unique, not null | Fictional location name |
| `channel` | string | controlled value | `Pharmacy Retail`, `Beauty Retail`, `Digital` |
| `store_format` | string | controlled value | Format within channel |
| `state` | string | AU state/territory code | Geographic grouping |
| `region` | string | not null | Fictional operating region |
| `size_band` | string | `Small`, `Medium`, `Large` | Relative ranging capacity |
| `open_date` | date | not null | Trading commencement date |
| `active_flag` | boolean | not null | Current trading status |

Digital activity is represented as a node so the shared store key and filters
remain valid without pretending it is a physical shop.

### 3.5 `dim_promotion`

**Grain:** one row per promotion campaign.

| Column | Type | Constraint | Description |
|---|---|---|---|
| `promotion_id` | string | primary key | Identifier such as `PRM001` |
| `promotion_name` | string | not null | Fictional campaign name |
| `promotion_type` | string | controlled value | Percentage, multibuy, catalogue, launch |
| `start_date` | date | not null | First promotional date |
| `end_date` | date | >= start date | Final promotional date |
| `channel` | string | controlled value | Eligible channel |
| `supplier_funding_total` | decimal | non-negative | Agreed campaign funding |
| `status` | string | controlled value | Planned, Active, Complete |

### 3.6 `bridge_promotion_products`

**Grain:** one row per promotion–product combination.

| Column | Type | Constraint | Description |
|---|---|---|---|
| `promotion_id` | string | composite primary key | Promotion reference |
| `product_id` | string | composite primary key | Participating SKU |
| `promotional_unit_price` | decimal | positive | Advertised unit-equivalent price |
| `funding_allocation` | decimal | non-negative | Product share of supplier funding |

The sum of `funding_allocation` across a promotion must equal
`supplier_funding_total` within a one-cent tolerance.

## 4. Facts

### 4.1 `fact_sales_weekly`

**Grain:** one row per `week_start` × `store_id` × `product_id`.

| Column | Type | Constraint | Description |
|---|---|---|---|
| `week_start` | date | composite primary key | Trading week |
| `store_id` | string | composite primary key, FK | Selling location |
| `product_id` | string | composite primary key, FK | Sold SKU |
| `promotion_id` | string/null | foreign key | Dominant promotion, if any |
| `units_sold` | integer | non-negative | Net units after returns |
| `gross_sales` | decimal | non-negative | Units at pre-discount value |
| `discount_value` | decimal | non-negative | Markdown and promotion discount |
| `net_sales` | decimal | >= 0 | Gross sales less discount |
| `cost_of_goods` | decimal | non-negative | Cost associated with sold units |
| `returns_units` | integer | non-negative | Returned units recorded separately |

Only one dominant promotion is assigned to a weekly store–SKU record in the
MVP. Overlapping promotions for the same SKU, store, and week are prohibited.

### 4.2 `fact_inventory_weekly`

**Grain:** one row per `week_start` × `store_id` × `product_id`.

| Column | Type | Constraint | Description |
|---|---|---|---|
| `week_start` | date | composite primary key | Snapshot week |
| `store_id` | string | composite primary key, FK | Stock location |
| `product_id` | string | composite primary key, FK | Stocked SKU |
| `opening_stock_units` | integer | non-negative | Start-of-week stock |
| `receipts_units` | integer | non-negative | Units received in week |
| `closing_stock_units` | integer | non-negative | End-of-week stock |
| `in_stock_days` | integer | 0–7 | Days available for sale |
| `ranged_flag` | boolean | not null | SKU ranged at location |

Inventory reconciliation tolerance is one unit:

`opening stock + receipts - units sold + returns ≈ closing stock`

The tolerance acknowledges simplified weekly timing in the synthetic model.

### 4.3 `fact_forecast_weekly`

**Grain:** one row per `week_start` × `store_id` × `product_id` ×
`forecast_version`.

| Column | Type | Constraint | Description |
|---|---|---|---|
| `week_start` | date | composite primary key | Forecast demand week |
| `store_id` | string | composite primary key, FK | Forecast location |
| `product_id` | string | composite primary key, FK | Forecast SKU |
| `forecast_version` | string | composite primary key | Snapshot identifier |
| `forecast_created_date` | date | < week_start | Creation date |
| `forecast_units` | integer | non-negative | Expected units |

The MVP uses one official version created four weeks before the demand week.
The version column preserves a valid future path for forecast-lag analysis.

### 4.4 `fact_purchase_order_lines`

**Grain:** one row per purchase-order-line delivery event. An undelivered open
line has one placeholder event row with a null receipt date and zero received
units.

| Column | Type | Constraint | Description |
|---|---|---|---|
| `delivery_event_id` | string | primary key | Unique delivery event |
| `po_line_id` | string | not null | Stable order-line commitment identifier |
| `purchase_order_id` | string | not null | Parent purchase order |
| `supplier_id` | string | foreign key | Supplying organisation |
| `product_id` | string | foreign key | Ordered SKU |
| `destination_store_id` | string | foreign key | Receiving node |
| `order_date` | date | not null | Order creation date |
| `expected_delivery_date` | date | >= order date | Contracted delivery date |
| `actual_delivery_date` | date/null | >= order date | Receipt date; null if open |
| `ordered_units` | integer | positive | Ordered quantity |
| `received_units` | integer | non-negative | Quantity received in this event |
| `line_status` | string | controlled value | Open, Partially Received, Complete, Cancelled |

Split deliveries use multiple delivery-event rows sharing `po_line_id`.
`ordered_units`, supplier, product, destination, and commitment dates must be
identical across those rows. Supplier service metrics take `ordered_units` once
per `po_line_id`, sum its received events, and then evaluate on-time and in-full
status.

## 5. Controlled values

### Channels

- `Pharmacy Retail`
- `Beauty Retail`
- `Digital`

### Categories

- `Skincare`
- `Cosmetics`
- `Vitamins & Supplements`
- `Haircare`
- `Personal Care`
- `Wellness`
- `Pharmacy Essentials`

### Australian regions

The synthetic dataset will use `VIC`, `NSW`, `QLD`, `SA`, and `WA` for a useful
geographic mix without creating sparse territory-level segments.

## 6. Required validation rules

1. Primary and composite keys are unique and non-null.
2. Every fact foreign key maps to an active or historically valid dimension row.
3. No sales or inventory record predates the store opening or product launch.
4. Monetary and unit quantities are non-negative.
5. `net_sales = gross_sales - discount_value` within one cent.
6. Cost of goods cannot exceed gross sales by more than the deliberately
   generated loss-leading promotion cases.
7. `in_stock_days` is an integer from zero to seven.
8. Unranged products must not have sales, forecast, or stock records.
9. Promotion dates are valid and participating products exist.
10. Promotion funding allocations reconcile to the campaign total.
11. Purchase-order date order is logically valid.
12. Cancelled purchase orders are excluded from supplier service metrics.
13. Weekly fact tables contain only Monday `week_start` dates.
14. Duplicate business-grain records fail validation rather than being silently
    removed.

## 7. Planned dataset scale

| Entity | Planned volume |
|---|---:|
| Trading history | 78 weeks |
| Stores/nodes | 24 |
| Products | 96 |
| Suppliers | 12 |
| Promotions | 36–48 |
| Weekly store–SKU fact rows | approximately 100,000 |
| Purchase-order delivery events | approximately 2,500–3,000 |

Not every product is ranged in every location. Sparse ranging makes category,
format, and availability analysis more realistic and controls file size.

## 8. Synthetic scenario signals

The generator includes these reproducible scenarios:

- Winter growth in vitamins and selected pharmacy essentials.
- Summer growth in skincare and personal care.
- One strategic supplier with deteriorating OTIF in the final eight weeks.
- One supplier with strong service but declining margin performance.
- A beauty launch with strong sales in large stores and weak performance in
  small stores.
- Several high-uplift promotions that destroy incremental gross profit.
- Promotional stock-outs that create measurable lost-sales exposure.
- Systematic over-forecasting in one category and under-forecasting in another.
- A small, isolated set of deliberate data-quality failures stored separately
  from the clean application dataset.

These signals will support a coherent demonstration rather than random charts.
