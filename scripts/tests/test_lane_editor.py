import pytest


def test_lane_editor_parses_editorial_decisions_from_llm_output():
    from etl.editorial_llm.lane_editor import parse_lane_decision

    payload = parse_lane_decision(
        {
            "lane": "frameworks",
            "included": [],
            "excluded": [],
        }
    )

    assert payload.lane == "frameworks"


def test_lane_editor_rejects_invalid_json_payloads():
    from etl.editorial_llm.lane_editor import parse_lane_decision_json

    with pytest.raises(ValueError):
        parse_lane_decision_json("{not-json")


def test_lane_editor_normalizes_synthetic_variant_fields():
    from etl.editorial_llm.lane_editor import parse_lane_decision

    payload = parse_lane_decision(
        {
            "lane": "frameworks",
            "included": [
                {
                    "name": "React",
                    "ring": "ADOPT",
                    "description": "UI library",
                    "whyThisRing": "Strong usage and maturity.",
                    "whyNow": "Still dominant.",
                    "confidence": "high",
                    "trend": "rising",
                }
            ],
            "excluded": [],
        }
    )

    assert payload.included[0].ring == "adopt"
    assert payload.included[0].confidence == 0.9
    assert payload.included[0].trend == "up"


def test_lane_editor_normalizes_numeric_percentage_confidence():
    from etl.editorial_llm.lane_editor import parse_lane_decision

    payload = parse_lane_decision(
        {
            "lane": "frameworks",
            "included": [
                {
                    "name": "React",
                    "ring": "ADOPT",
                    "description": "UI library",
                    "confidence": 95,
                    "trend": "rising",
                }
            ],
            "excluded": [],
        }
    )

    assert payload.included[0].confidence == 0.95


def test_lane_editor_prefers_synthetic_openai_compatible_config(monkeypatch):
    from etl.editorial_llm.client import resolve_llm_config

    monkeypatch.setenv("SYNTHETIC_API_KEY", "syn-test")
    monkeypatch.setenv("SYNTHETIC_API_URL", "https://api.synthetic.new/v1")
    monkeypatch.setenv("SYNTHETIC_MODEL", "hf:MiniMaxAI/MiniMax-M2.5")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    config = resolve_llm_config()

    assert config == {
        "api_key": "syn-test",
        "base_url": "https://api.synthetic.new/v1",
        "model": "hf:MiniMaxAI/MiniMax-M2.5",
    }


def test_lane_editor_does_not_fall_back_to_openai_provider(monkeypatch):
    from etl.editorial_llm.client import resolve_llm_config

    monkeypatch.delenv("SYNTHETIC_API_KEY", raising=False)
    monkeypatch.setenv("OPENAI_API_KEY", "openai-test")
    monkeypatch.setenv("OPENAI_API_URL", "https://api.openai.com/v1")
    monkeypatch.setenv("OPENAI_MODEL", "gpt-4o-mini")

    config = resolve_llm_config()

    assert config is None


def test_lane_prompt_requests_exact_schema_and_enums():
    from etl.contracts import LaneEditorialInput
    from etl.editorial_llm.prompts import build_lane_prompt

    prompt = build_lane_prompt(LaneEditorialInput(lane="frameworks", candidates=[]), max_items=15)

    assert '"ring": "adopt|trial|assess|hold"' in prompt
    assert '"trend": "up|down|stable|new"' in prompt
    assert '"confidence": 0.0-1.0' in prompt
    assert "Include at most 15 items" in prompt


def test_lane_editor_retries_same_synthetic_config_on_invalid_first_response(monkeypatch):
    import sys
    import types

    from etl.contracts import LaneEditorialInput, MarketEntity
    from etl.editorial_llm.client import request_lane_decision

    calls = []

    class FakeCompletions:
        def create(self, **kwargs):
            calls.append(kwargs)
            content = "{bad-json" if len(calls) == 1 else '{"lane":"frameworks","included":[{"name":"React","ring":"ADOPT","description":"UI library","whyThisRing":"Strong usage.","whyNow":"Current demand.","confidence":"high","trend":"rising"}],"excluded":[]}'
            message = types.SimpleNamespace(content=content)
            choice = types.SimpleNamespace(message=message)
            return types.SimpleNamespace(choices=[choice])

    class FakeOpenAI:
        def __init__(self, **kwargs):
            self.chat = types.SimpleNamespace(completions=FakeCompletions())

    monkeypatch.setenv("SYNTHETIC_API_KEY", "syn-test")
    monkeypatch.setenv("SYNTHETIC_API_URL", "https://api.synthetic.new/v1")
    monkeypatch.setenv("SYNTHETIC_MODEL", "hf:MiniMaxAI/MiniMax-M2.5")
    monkeypatch.setitem(sys.modules, "openai", types.SimpleNamespace(OpenAI=FakeOpenAI))

    lane_input = LaneEditorialInput(
        lane="frameworks",
        candidates=[
            MarketEntity(
                canonical_name="React",
                canonical_slug="react",
                editorial_kind="framework",
                topic_family="ui",
            )
        ],
    )
    result = request_lane_decision(
        lane_input=lane_input,
        prompt="Return JSON",
        parser=lambda payload: __import__("etl.editorial_llm.lane_editor", fromlist=["parse_lane_decision_json"]).parse_lane_decision_json(payload),
    )

    assert result is not None
    assert result.included[0].ring == "adopt"
    assert len(calls) == 2


def test_lane_editor_enriches_llm_decision_with_scored_entity_fields(monkeypatch):
    from etl.contracts import LaneEditorialDecision, LaneEditorialInput, EditorialBlip, MarketEntity
    from etl.editorial_llm import lane_editor
    from etl.signals.scoring import score_entity

    entity = MarketEntity(
        canonical_name="React",
        canonical_slug="react",
        editorial_kind="framework",
        topic_family="ui",
        source_evidence=[
            {"source": "github_trending", "metric": "github_stars", "normalized_value": 90.0},
            {"source": "deps_dev", "metric": "reverse_dependents", "normalized_value": 100.0},
            {"source": "deps_dev", "metric": "default_version", "normalized_value": 100.0},
        ],
        implementation_languages=["typescript"],
        ecosystems=["npm"],
    )
    scored_entity = score_entity(entity)
    lane_input = LaneEditorialInput(lane="frameworks", candidates=[scored_entity])
    llm_decision = LaneEditorialDecision(
        lane="frameworks",
        included=[
            EditorialBlip(
                id="react",
                name="React",
                quadrant="frameworks",
                ring="hold",
                description="LLM description",
                trend="stable",
                confidence=0.5,
                updatedAt="2026-04-01T00:00:00+00:00",
            )
        ],
        excluded=[],
    )
    monkeypatch.setattr(lane_editor, "_try_llm_lane_decision", lambda lane_input, max_items: llm_decision)

    decision = lane_editor.decide_lane(lane_input)
    blip = decision.included[0]

    assert blip.ring == "adopt"
    assert blip.marketScore == lane_editor.market_score(scored_entity)
    assert blip.signals["adoption"] == scored_entity.adoption_signals["adoption"]
    assert blip.evidenceSummary is not None
    assert blip.evidenceSummary["hasExternalAdoption"] is True
    assert blip.evidence == [
        "github_trending:github_stars",
        "deps_dev:reverse_dependents",
        "deps_dev:default_version",
    ]
