# Data

The app uses synthetic health and beauty retail data. Nothing in this folder
comes from Wesfarmers Health or any other retailer.

Generate the files from the project root:

```bash
python3 scripts/generate_data.py
```

The script uses a fixed seed, so each run produces the same result. Output goes
to `data/generated/`, which is not committed to Git.

The dataset contains 78 weeks of sales, inventory and forecasts, plus products,
stores, suppliers, promotions and purchase-order deliveries. A validation report
is written alongside the CSV files. The command exits with an error if a check
fails.

Some patterns are intentional. For example, one supplier's delivery performance
drops late in the period, Cosmetics are over-forecast, and Vitamins are
under-forecast. These give the dashboard useful problems to investigate.
