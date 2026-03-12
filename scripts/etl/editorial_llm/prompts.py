from __future__ import annotations

from etl.contracts import LaneEditorialInput


def build_lane_prompt(lane_input: LaneEditorialInput, max_items: int) -> str:
    candidate_lines = [
        f"- {candidate.canonical_name}: adoption={candidate.adoption_signals.get('adoption', 0)}, momentum={candidate.momentum_signals.get('momentum', 0)}, maturity={candidate.maturity_signals.get('maturity', 0)}, risk={candidate.risk_signals.get('risk', 0)}"
        for candidate in lane_input.candidates
    ]
    schema = """Return JSON only, with this exact shape:
{
  "lane": "%s",
  "included": [
    {
      "id": "slug-string",
      "name": "display name",
      "quadrant": "%s",
      "ring": "adopt|trial|assess|hold",
      "description": "one short paragraph",
      "whyThisRing": "explicit ring thesis",
      "whyNow": "explicit current-quarter thesis",
      "confidence": 0.0-1.0,
      "trend": "up|down|stable|new",
      "updatedAt": "ISO-8601 timestamp"
    }
  ],
  "excluded": [
    {
      "id": "slug-string",
      "name": "display name",
      "reason": "short exclusion reason",
      "lane": "%s",
      "marketScore": 0.0
    }
  ]
}
Do not use uppercase enum values.
Do not use labels like high/medium/low for confidence.
Do not wrap JSON in markdown fences.""" % (lane_input.lane, lane_input.lane, lane_input.lane)
    return "\n".join(
        [
            f"You are editing the {lane_input.lane} lane for a technology radar.",
            "Return strict JSON with included and excluded arrays.",
            f"Include at most {max_items} items. Do not include every candidate if the lane would become noisy.",
            "Use the excluded list for candidates that look promising but are more appropriate for near-term watchlist review.",
            "Order excluded items with the strongest near-term adoption potential first.",
            "Each included item must have ring, description, whyThisRing, whyNow, confidence, and trend.",
            schema,
            *lane_input.prompt_context,
            "Candidates:",
            *candidate_lines,
        ]
    )
