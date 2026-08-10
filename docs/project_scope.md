# Merchandise Pulse — MVP Product Brief

## 1. Purpose

Build a compact, interview-ready Streamlit application that demonstrates how an
Insights & Automation Analyst can combine retail data into trusted reporting,
identify commercial exceptions, and guide Merchandise teams toward action.

The project is a decision-support product, not merely a collection of charts.

## 2. Intended users

### Primary user: Merchandise analyst

Needs to monitor trading performance, investigate exceptions, and prepare clear
recommendations for weekly reviews.

### Secondary user: Merchandise or supplier manager

Needs a concise view of supplier, promotion, forecast, and inventory performance
without manually combining multiple spreadsheets.

## 3. Decisions supported

The MVP must help users decide:

1. Which supplier needs attention first?
2. Which products or stores are driving the issue?
3. What is the estimated sales or margin impact?
4. Which promotions created profitable incremental demand?
5. Where should forecasts or replenishment assumptions be reviewed?
6. What action should be taken next, and why?

## 4. Core business questions

- Are sales and gross margin on target and improving?
- Which suppliers are missing service or commercial expectations?
- Are stock-outs constraining otherwise healthy demand?
- Where are forecasts persistently biased?
- Which promotions deliver incremental gross profit after discount and funding?
- Which exceptions have the greatest estimated commercial impact?
- Is the underlying reporting data complete, valid, and current?

## 5. MVP pages

### 5.1 Executive Overview

- Sales, units, gross profit, gross margin, and sales growth
- Availability, forecast accuracy, and supplier OTIF
- Trends and target comparisons
- Highest-priority commercial exceptions
- Shared filters for period, channel, state, category, and supplier

### 5.2 Supplier Scorecard

- Ranked composite supplier score
- Performance against target by component
- Sales, margin, availability, OTIF, forecast accuracy, and promotion return
- Supplier trend and SKU-level drivers
- Downloadable filtered scorecard

### 5.3 Promotion Analysis

- Baseline and promotional sales
- Incremental units, revenue, and gross profit
- Supplier funding and return on trade investment
- Stock-outs during promotion
- Clear separation of high-volume and genuinely profitable promotions

### 5.4 Action Centre

- Explainable, rule-based exceptions
- Priority, issue, affected entity, estimated impact, and recommendation
- Filters and downloadable action list
- Links back to the supporting analysis

### 5.5 Data Health

- Missing product or supplier mappings
- Duplicate records
- Invalid dates or values
- Referential-integrity failures
- Data freshness and validation status

## 6. Initial metric set

The formulas are documented in `metric_dictionary.md`. The MVP will include:

- Net sales
- Units sold
- Gross profit and gross margin percentage
- Sales growth
- Product availability
- Stock-out rate
- Weeks of cover
- Estimated lost sales
- Forecast bias and WMAPE
- On-time delivery, in-full delivery, and OTIF
- Promotional uplift
- Incremental gross profit
- Return on trade investment
- Composite supplier score

## 7. Automation approach

The MVP will use transparent rules before any generative AI. Each exception must
show the calculation or threshold that caused it.

Example patterns:

- Low supplier OTIF combined with material estimated lost sales
- Positive promotional sales uplift but negative incremental gross profit
- Positive forecast bias combined with excessive weeks of cover
- High demand combined with poor availability

An AI-written weekly summary may be added later as an optional enhancement. It
must only summarise calculated, displayed metrics and the app must work without
an API key.

## 8. Synthetic retail scenario

The fictional business will represent a health-and-beauty retailer with:

- Pharmacy retail, beauty retail, and digital channels
- Multiple Australian states and store formats
- Health, wellness, skincare, cosmetics, haircare, and personal-care categories
- Suppliers with intentionally different service and commercial profiles
- Seasonal demand, promotions, new products, stock-outs, and forecast bias

All data will be synthetic and reproducible using a fixed random seed.

## 9. MVP boundaries

The first release will not include:

- Real Wesfarmers Health, Priceline, atomica, supplier, or customer data
- Customer-level or patient-level data
- A planogram or space-optimisation engine
- Production replenishment recommendations
- Live ERP, POS, Power BI, or Power Automate integrations
- Unverifiable AI-generated recommendations
- User authentication or a production database

These exclusions keep the portfolio credible and achievable while retaining a
clear path for future extensions.

## 10. Acceptance criteria

The MVP is complete when a user can:

1. Filter the application consistently across business dimensions.
2. Identify the most important supplier or merchandise exception.
3. Drill from a headline KPI into its product, store, or supplier drivers.
4. Quantify the exception using a documented metric.
5. See an explainable recommended action.
6. Evaluate promotion profitability rather than sales uplift alone.
7. Inspect data-quality results and metric definitions.
8. Download a useful supplier scorecard or action list.
9. Run the app locally from documented setup instructions.
10. Verify core calculations through automated tests.

## 11. Interview narrative

> I built a self-service merchandise decision tool that combines sales,
> inventory, forecasts, promotions, and supplier delivery data into a governed
> reporting model. It identifies commercial exceptions, estimates their impact,
> and recommends the next action using transparent business rules.

## 12. Next step

The data generator now produces a repeatable 78-week retail dataset and checks
its keys, mappings, arithmetic and intended business patterns. Step 4 will turn
the documented formulas into reusable, tested Python functions.
