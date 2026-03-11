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


def test_lane_editor_prefers_synthetic_openai_compatible_config(monkeypatch):
    from etl.editorial_llm.lane_editor import resolve_llm_config

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
    from etl.editorial_llm.lane_editor import resolve_llm_config

    monkeypatch.delenv("SYNTHETIC_API_KEY", raising=False)
    monkeypatch.setenv("OPENAI_API_KEY", "openai-test")
    monkeypatch.setenv("OPENAI_API_URL", "https://api.openai.com/v1")
    monkeypatch.setenv("OPENAI_MODEL", "gpt-4o-mini")

    config = resolve_llm_config()

    assert config is None


def test_lane_prompt_requests_exact_schema_and_enums():
    from etl.contracts import LaneEditorialInput
    from etl.editorial_llm.prompts import build_lane_prompt

    prompt = build_lane_prompt(LaneEditorialInput(lane="frameworks", candidates=[]))

    assert '"ring": "adopt|trial|assess|hold"' in prompt
    assert '"trend": "up|down|stable|new"' in prompt
    assert '"confidence": 0.0-1.0' in prompt


def test_lane_editor_retries_same_synthetic_config_on_invalid_first_response(monkeypatch):
    import sys
    import types

    from etl.contracts import LaneEditorialInput, MarketEntity
    from etl.editorial_llm.lane_editor import _try_llm_lane_decision

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

    result = _try_llm_lane_decision(
        LaneEditorialInput(
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
    )

    assert result is not None
    assert result.included[0].ring == "adopt"
    assert len(calls) == 2
