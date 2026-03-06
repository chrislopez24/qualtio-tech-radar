# Radar Review Checklist

Use this checklist when reviewing a quarterly radar run or its generated summary artifact.

## Credibility

- Do the top technologies look plausible for the current ecosystem?
- Are there obvious false positives in `adopt` or `trial`?
- Are major technologies missing from the main radar?

## Ring Quality

- Are `adopt` entries clearly stronger than `trial` entries?
- Do `trial` and `assess` feel like meaningful distinctions instead of noise?
- Are any technologies sitting in a strong ring with weak signals?

## Change Review

- Do the newly added technologies make sense?
- Do the dropped technologies look intentional rather than accidental churn?
- If the shadow gate is `warn`, do the pending leader transitions look reasonable?

## Watchlist Quality

- Is the watchlist interesting enough to monitor next cycle?
- Is the watchlist too noisy or too conservative?
- Are the suggested actions and review dates credible?

## Follow-Up

- If there are suspicious items, should thresholds or scoring heuristics be adjusted?
- If the summary looks weak but thresholds passed, record the issue as a product-quality problem, not only an ETL problem.
