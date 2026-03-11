# Radar Review Checklist

Use this checklist after a real pipeline run has written the internal artifacts and `src/data/data.ai.json`.

## Snapshot Quality

- Does `artifacts/market-snapshot.json` cover all five editorial lanes?
- Are major market anchors present even when they are not trending on GitHub today?
- Are techniques and platforms represented as first-class entities rather than repo side effects?

## Lane Decisions

- Does each lane in `artifacts/editorial-decisions.json` show a credible include/exclude cut?
- Are weak candidates excluded because of narrow evidence, duplication, or poor editorial value?
- Are lane prompts and nearby alternatives small enough to remain comparable?

## Harmonization

- Does `artifacts/editorial-harmonized.json` remove duplicates across lanes?
- Are frameworks published to the public `tools` quadrant as intended by the frontend contract?
- Does the final mix avoid over-concentration in one lane or ring?

## Public Artifact

- Does `src/data/data.ai.json` keep the stable frontend keys?
- Does every published blip have a clear description and ring thesis?
- Are `watchlist` items actionable and scheduled for review?

## Editorial Sanity Checks

- Are there any obvious false positives such as awesome lists, learning repos, or generic reference collections?
- Does the output feel market-aware rather than repo-trending-only?
- Are the top `adopt` entries clearly stronger than the `trial` and `assess` entries?

## Follow-Up

- If a false positive escaped, add a regression test before patching the collector or resolver.
- If a major market anchor is missing, add or refine the seed catalog entry in `scripts/etl/canonical/seeds.py`.
- If lane cuts feel weak, inspect lane pack size and editorial scoring before widening publication counts.
