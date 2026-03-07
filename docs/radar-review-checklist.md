# Radar Review Checklist

Use this checklist when reviewing a quarterly radar run or its generated summary artifact.

## Credibility

- Do the top technologies look plausible for the current ecosystem?
- Are there obvious false positives in `adopt` or `trial`?
- Are any `adopt`/`trial` entries actually books, awesome lists, roadmaps, APIs directories, tutorials, or utility repos?
- Are major technologies missing from the main radar?

## Ring Quality

- Are `adopt` entries clearly stronger than `trial` entries?
- Do `trial` and `assess` represent meaningful distinctions?
- Are weak-signal items promoted to strong rings?

## Change Review

- Do newly added technologies make sense?
- Do dropped technologies look intentional rather than accidental churn?
- If shadow gate is `warn`, are pending leader transitions reasonable?

## Watchlist Quality

- Is the watchlist useful for next-cycle monitoring?
- Is it too noisy or too conservative?
- Are suggested actions and review dates credible?
- Is watchlist semantically consistent with ring expectations?

## Follow-Up

- If suspicious items exist, should thresholds/scoring heuristics be adjusted?
- If suspicious items are resource-like repositories, should editorial filtering be tightened?
- If summary looks weak but gates passed, record it as a product-quality issue (not only ETL).

---

## Current Status (2026-03-07)

### What is confirmed

- The run is **real** (live GitHub/HN signals + real ETL execution).
- Editorial filters for `books/awesome/roadmap/apis/gitignore` are applied in both `technologies` and `watchlist`.
- The missing-evidence leak is closed: `go` and `Python` now carry atomic signal evidence and no longer publish with `missingEvidence`.
- Shadow quality gate is currently passing with strong margins on overlap and leader coverage.

### Quality verdict

- Results are publication-safe from a pipeline-quality perspective (`shadowGate=pass`, `publishReadiness=pass`).
- Editorial quality is improved but still requires human sanity checks for top picks (e.g., utility-heavy repos that can still score high).
- Remaining bias is structural: strong GitHub popularity influence and limited source diversity.

### Immediate recommended actions

1. Recalibrate GitHub scoring to reduce saturation/double-weight effects.
2. Tighten `adopt` eligibility for utility-style repos even when momentum is high.
3. Keep watchlist hygiene strict: no entries that would serialize with `missingEvidence`.
4. Add deterministic rules for known noisy repo families (utility/educational/reference clusters).
5. Maintain a small golden set (expected good/bad items) for regression control.
