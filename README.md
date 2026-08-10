# Merchandise Pulse

Merchandise Pulse is a portfolio project demonstrating retail merchandise
analytics, supplier performance reporting, and workflow automation in
Streamlit.

The application will use fictional, synthetic health-and-beauty retail data.
It is inspired by common Australian retail problems and is not affiliated with,
endorsed by, or built from proprietary data belonging to Wesfarmers Health.

## Current status

The core interface is complete: Executive Overview, Supplier Scorecard,
Promotion Analysis, Forecast & Inventory, Action Centre, AI Insight Brief,
and Data Health.

Project documentation:

- [`docs/project_scope.md`](docs/project_scope.md) — agreed product brief
- [`docs/data_model.md`](docs/data_model.md) — grains, keys, relationships, and
  validation rules
- [`docs/metric_dictionary.md`](docs/metric_dictionary.md) — formulas, targets,
  score weights, and calculation conventions

The application and synthetic data will be developed incrementally in later
steps.

## Planned capabilities

- Executive merchandise performance overview
- Supplier performance scorecards
- Promotion effectiveness analysis
- Forecast and inventory exceptions
- Prioritised, explainable action recommendations
- Data-quality monitoring and self-service exports
- Evidence-grounded AI summaries through OpenRouter, with a local fallback

## Planned technical approach

- Python
- Streamlit
- pandas
- Plotly
- pytest

## Generate the data

```bash
python3 scripts/generate_data.py
```

Generated files are written to `data/generated/`. They are ignored by Git
because they can be reproduced from the fixed seed in the script.

## Local setup

The project uses `uv` for its local environment:

```bash
uv sync --extra dev
python3 scripts/generate_data.py
uv run pytest -q
```

Metric code lives in `src/merchandise_pulse/`. Dashboard pages will call these
functions rather than defining their own versions of the calculations.

Run the dashboard with:

```bash
uv run streamlit run app.py
```

The AI Insight Brief works without a key in template mode. For live generation,
paste an OpenRouter key into the password field or set it locally:

```bash
export OPENROUTER_API_KEY="your-key"
```

Do not add keys to the repository. `.env` and `.streamlit/secrets.toml` are
already ignored by Git.

## Proposed structure

```text
.
├── app.py
├── pages/
├── src/
├── data/
│   ├── raw/
│   └── processed/
├── tests/
├── docs/
└── .streamlit/
```

Folders will be introduced when their contents are built, avoiding empty
scaffolding and premature implementation.
