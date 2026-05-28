# Presentation assets

Charts, diagrams, and visualizations for the Lighthouse Data Engineer case presentation.

## Regenerate all images

```bash
pip install matplotlib
python scripts/generate_presentation_assets.py
```

## Files

| File | Used on slide | Description |
|---|---|---|
| `01_architecture_overview.png` | 5 | End-to-end pipeline architecture |
| `02_market_insight_dashboard.png` | 2, 10 | Composite dashboard (case mockup style) |
| `03_arrival_date_popularity.png` | 10 | Search level / arrival date chart |
| `04_country_trends.png` | 10 | Top countries with % and avg LOS |
| `05_los_distribution.png` | 10 | LOS1–LOS8-14 distribution |
| `06_medallion_layers.png` | 8 | Bronze / silver / gold model |
| `07_validation_layers.png` | 11 | Three-layer validation strategy |
| `08_cost_breakdown.png` | 14 | Monthly cost bar chart |
| `09_mvp_phasing.png` | 16 | MVP phases cost & timeline |
| `10_lambda_layers.png` | 17 | Speed / batch / serving layers |
| `11_throughput_volume.png` | 3 | 100 req/s volume infographic |
| `12_sample_json_payload.png` | 6 | Inbound JSON payload example |
| `13_orchestration_dag.png` | 12 | Airflow DAG task flow |

Import into Google Slides or PowerPoint from [`slides.md`](../slides.md).
