# Revision of 24 November 2026

- Reproduced the original seasonal naive and SARIMA results exactly before extending the comparison; see results/original_reproduction.json.
- Added the fixed additive growth-adjusted seasonal naive rule, using the latest 12 observed year-on-year changes at each cutoff. Same adjustment at horizons 1-3, no within-block updating and no tuning on 2025.
- Pooled 2025 MAE: original naive 0.435, growth-adjusted naive 0.161, SARIMA 0.343 TWh. RMSE: 0.483, 0.217, 0.418 TWh. Mean error: 0.435, 0.036, 0.270 TWh.
- Updated the abstract, results and conclusion. SARIMA does not beat the growth-adjusted benchmark on 2025. This is explicitly a follow-up comparison prompted by original results, not an untouched confirmatory test.
- Added horizon-specific scores, one visual chronological split and the April-June worked example. Main slides 1-12 are split evenly among four speakers; seven technical backups follow.
- Corrected the 2025 figure to monthly tick labels and separated tick spacing from quarterly refitting. Made the plot and three-model table the main results slide.
- Clarified exact-MAE tie handling consistently in code, notebook, report and slides. AICc is used only within common (d,D); otherwise retain enumeration. No ties occurred, so selection is unchanged.
- Retained the 2018 source audit, sensitivity and observed SARIMA interval coverage: 9/12 at 80% nominal and 10/12 at 95% nominal.
- All source files and frozen data needed for this revision were found. No official rubric was attached.

## Start here

Open report_ams_style/main.pdf and presentation/main.pdf. Editable LaTeX is beside each PDF; templates and shared-table generation are under scripts/. See README.md for commands. Nothing has been committed or pushed.
