import json


def test_publisher_writes_frontend_contract_from_editorial_decision(tmp_path):
    from etl.publish.publisher import publish_radar

    result = publish_radar({"blips": []}, tmp_path / "data.ai.json")

    assert result["technologies"] == []
    assert json.loads((tmp_path / "data.ai.json").read_text())["technologies"] == []


def test_publisher_maps_frameworks_to_public_tools_quadrant(tmp_path):
    from etl.publish.publisher import publish_radar

    result = publish_radar(
        {
            "blips": [
                {
                    "id": "react",
                    "name": "React",
                    "quadrant": "frameworks",
                    "ring": "adopt",
                    "description": "UI framework",
                    "trend": "stable",
                    "confidence": 0.9,
                    "updatedAt": "2026-03-11T00:00:00+00:00",
                }
            ]
        },
        tmp_path / "data.ai.json",
    )

    assert result["technologies"][0]["quadrant"] == "tools"


def test_publisher_omits_null_optional_fields_from_public_items(tmp_path):
    from etl.publish.publisher import publish_radar

    result = publish_radar(
        {
            "blips": [
                {
                    "id": "react",
                    "name": "React",
                    "quadrant": "frameworks",
                    "ring": "adopt",
                    "description": "UI framework",
                    "trend": "stable",
                    "confidence": 0.9,
                    "updatedAt": "2026-03-11T00:00:00+00:00",
                    "owner": None,
                    "nextStep": None,
                    "nextReviewAt": None,
                }
            ]
        },
        tmp_path / "data.ai.json",
    )

    item = result["technologies"][0]
    assert "owner" not in item
    assert "nextStep" not in item
    assert "nextReviewAt" not in item
