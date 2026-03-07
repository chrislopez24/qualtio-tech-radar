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

- Our technologies: `35`
- Thoughtworks blips (vol 33): `114`
- Zalando entries: `77`

Exact-name overlap:

- With Thoughtworks: `2` (`langflow`, `n8n`)
- With Zalando: `5` (`go`, `javascript`, `kubernetes`, `python`, `typescript`)

Our strong rings at run time:

- `adopt` (`6`): `transformers`, `yt-dlp`, `langchain`, `pytorch`, `django`, `fastapi`
- `trial` (`8`): `TypeScript`, `go`, `Python`, `open-webui`, `youtube-dl`, `langflow`, `react`, `next.js`

## Interpretation

- Low exact overlap with Thoughtworks is expected: Thoughtworks radar emphasizes practices, tooling patterns, and directional picks, not only mainstream stack anchors.
- Moderate overlap with Zalando on foundational languages/platforms is healthy and confirms baseline relevance.
- Our radar is intentionally more GitHub/package-evidence-driven than expert-panel-curated radars.

## Decision

- Keep this benchmark as a sanity check, not as a hard quality gate.
- Continue using external evidence quality gates (`sourceCoverage`, `evidenceSummary`, `review_radar_output`) as primary publication controls.
