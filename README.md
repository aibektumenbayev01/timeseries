# Forecasting Kazakhstan's Total Monthly Electricity Generation Using SARIMA

Revised 24 November 2026. Authors: Narlen Ualikan, Dariya Kuantay, Aibek Tumenbayev and Azhar Sarbassova, Nazarbayev University.

## Current finding

**SARIMA did not outperform the growth-adjusted seasonal naive benchmark on the 2025 test.** The original scores reproduce exactly. All errors below are TWh; mean error is actual minus forecast.

| Model | MAE | RMSE | Mean error |
|---|---:|---:|---:|
| Seasonal naive | 0.435 | 0.483 | 0.435 |
| Growth-adjusted seasonal naive | 0.161 | 0.217 | 0.036 |
| SARIMA | 0.343 | 0.418 | 0.270 |

SARIMA's 21.1% MAE improvement applies to the original seasonal naive comparison. The growth-adjusted rule has 53.1% lower MAE than SARIMA in this test, but was added as a follow-up prompted by the original results. It was not tuned on 2025; a new period is needed for an independent assessment. There is only one test year, four origins, and four observations per horizon.

## What to use

- `report_ams_style/main.tex` and `main.pdf`: primary current report, preserving the requested journal format.
- `presentation/main.tex` and `main.pdf`: updated 16:9 Beamer presentation; 12 main slides plus 7 technical backups.
- `materials/speaking_notes.txt` and `speaking_guide.pdf`: four speakers, three main slides each.
- `analysis.py` and `electricity_project.ipynb`: executable analysis and executed notebook.
- `results/test_predictions.csv`: 36 forecasts across the three models, with cutoffs and horizons.
- `results/growth_adjustments.csv`, `april_2025_block.csv`, `test_scores.csv`, `horizon_scores.csv`: benchmark and result details.
- `results/original_reproduction.json`: unmodified original-model rerun, before adding the benchmark; no discrepancy at tolerance 1e-10.
- `scripts/templates/report.tex` and `slides.tex`: editable prose/layout templates. `build_documents.py` fills numerical tables from CSVs. Direct edits to generated main.tex will be overwritten by this builder.

`report/` and `report_revised/` are synchronized aliases of the primary current report. The old ReportLab builder is retired; `build_report.py` and `build_latex.py` forward to the current builder. No separate report variants are used in the current package.

## Evaluation and benchmark definition

Initial training: 2019–2023 (60 months). Model selection: 2024 (12 months, four three-month blocks). Test: 2025 (12 months, four blocks starting January, April, July and October). Preserve the selected SARIMA(1,0,0)(0,1,1)[12] with a constant. Refit using expanding histories through December 2024, March, June and September 2025. Forecast each three-month block together; earlier completed test blocks may enter later refits.

At cutoff T, average the latest twelve observed differences `y[t] - y[t-12]` for t=T-11,...,T. Add that one absolute TWh adjustment to each corresponding prior-year month. This requires 24 observed months. The additive form and 12-month averaging window are fixed; no growth-rule alternatives were tested or tuned on 2025. No prediction intervals are invented for this point-only benchmark.

Exact unrounded validation-MAE ties use initial-training AICc only when all tied candidates share (d,D); otherwise retain original candidate enumeration. No tie occurred, so clarifying this rule did not change selection. Cross-differencing AICc entries are descriptive only.

## Reproduce

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python scripts/reproduce.py --latex
```

The last command requires `pdflatex` on PATH. It verifies frozen inputs, extracts the national series, reads the original Samruk tables, executes all notebook cells, regenerates sources/figures/results, compiles the report and slides, and runs independent checks. Without `--latex`, only the numerical and editable-source stages are refreshed; PDFs remain unchanged. For Overleaf, upload each document's folder, retaining its images/ folder, and compile main.tex.

To run only analysis: `python analysis.py`. To regenerate editable report/slides from CSVs: `python scripts/build_documents.py`. To verify: `python scripts/verify_results.py` after compiling the PDFs.

## Frozen data and source audit

The original public Ember global CSV (about 28 MB), unchanged national extraction, and original Samruk January/Q1 2018 DOCX files are included under `data/`. URLs, hashes and filters are recorded in `data/provenance.json`. The snapshot was downloaded 18 November 2026; it contains 102 consecutive months, January 2018–June 2026. The main experiment has 84 observations, January 2019–December 2025. No missing values are interpolated or manually corrected.

Filter: Area=Kazakhstan; Electricity source=Total generation; target=Generation (TWh). Source: [Ember monthly electricity data](https://ember-energy.org/data/monthly-electricity-data/), CC BY 4.0; retain attribution. Original Samruk documents retain their own source attribution.

Ember gives 9.780 TWh in each of January–March 2018. Samruk's January table gives 10.3573 TWh; Q1 total gives 29.3392 versus Ember's 29.340. Quarterly averaging is plausible, but not proven for all observations. Excluding 2018 preserves the source values; adding it back without retuning gives SARIMA MAE 0.360 and RMSE 0.441 TWh. Both naive methods are unchanged because their recent-data inputs exclude 2018. The growth-adjusted method still has the lowest pooled error.

## Limitations

Only four forecasts per horizon; the growth comparison is a follow-up rather than an untouched confirmatory test. The frozen revised data differ from historical real-time vintages. Only part of the source chain was audited, and other repeated values remain. Weather, outages, trade and policy are omitted; generation is not demand. SARIMA interval coverage is 9/12 (75.0%) for nominal 80% intervals and 10/12 (83.3%) for nominal 95% intervals. Residual non-rejection does not establish interval calibration. Dated January–March 2026 forecasts use information through December 2025 and are not live November 2026 forecasts.

No official course rubric was attached. The supplied current report and prior style example guided the format.

## Method references

- [Ember methodology](https://files.ember-energy.org/public-downloads/ember_electricity_data_methodology.pdf)
- [Samruk analytical reports](https://samruk-energy.kz/en/press-center/analytical-review)
- Hyndman and Athanasopoulos (2021), [Forecasting: Principles and Practice](https://otexts.com/fpp3/), Chapters 5 and 9.
- [statsmodels SARIMAX](https://www.statsmodels.org/stable/generated/statsmodels.tsa.statespace.sarimax.SARIMAX.html)
