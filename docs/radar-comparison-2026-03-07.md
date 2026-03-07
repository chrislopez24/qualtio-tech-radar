# Radar Comparison (2026-03-07)

## Inputs

- Our output: `src/data/data.ai.json`
- Thoughtworks: Volume 33 CSV (Nov 2025)
- Zalando: `docs/config.json` from `zalando/tech-radar`

## Method

1. Normalize names to lowercase.
2. Compare exact-name overlap sets (no semantic fuzzy matching).
3. Review ring distribution and strong ring composition (`adopt` + `trial`).

## Results

- Our technologies: `13`
- Thoughtworks blips (vol 33): `114`
- Zalando entries: `77`

Exact-name overlap:

- With Thoughtworks: `1` (`langflow`)
- With Zalando: `3` (`go`, `python`, `typescript`)

Our strong rings at run time:

- `adopt` (`5`): `transformers`, `yt-dlp`, `langchain`, `pytorch`, `django`
- `trial` (`7`): `TypeScript`, `go`, `Python`, `open-webui`, `youtube-dl`, `langflow`, `react`
- `assess` (`1`): `next.js`

## Interpretation

- Low exact overlap with Thoughtworks is expected: Thoughtworks radar emphasizes practices, tooling patterns, and directional picks, not only mainstream stack anchors.
- Moderate overlap with Zalando on foundational languages/platforms is still present and confirms baseline relevance.
- Our radar is intentionally more GitHub/package-evidence-driven than expert-panel-curated radars.

## Decision

- Keep this benchmark as a sanity check, not as a hard quality gate.
- Continue using external evidence quality gates (`sourceCoverage`, `evidenceSummary`, `review_radar_output`) as primary publication controls.
