import json
from pathlib import Path


VALID_QUADRANTS = {"platforms", "techniques", "tools", "languages"}
VALID_RINGS = {"adopt", "trial", "assess", "hold"}
VALID_TRENDS = {"up", "down", "stable", "new"}


def _assert_public_item_shape(item: dict) -> None:
    assert isinstance(item["id"], str)
    assert isinstance(item["name"], str)
    assert item["quadrant"] in VALID_QUADRANTS
    assert item["ring"] in VALID_RINGS
    assert isinstance(item["description"], str)
    assert item["trend"] in VALID_TRENDS
    assert isinstance(item["confidence"], (int, float))
    assert isinstance(item["updatedAt"], str)

    if "moved" in item:
        assert isinstance(item["moved"], int)
    if "whyThisRing" in item:
        assert isinstance(item["whyThisRing"], str)
    if "whyNow" in item:
        assert isinstance(item["whyNow"], str)
    if "useCases" in item:
        assert isinstance(item["useCases"], list)
    if "avoidWhen" in item:
        assert isinstance(item["avoidWhen"], list)
    if "alternatives" in item:
        assert isinstance(item["alternatives"], list)
    if "entityType" in item:
        assert isinstance(item["entityType"], str)
    if "canonicalId" in item:
        assert isinstance(item["canonicalId"], str)
    if "sourceCoverage" in item:
        assert isinstance(item["sourceCoverage"], int)
    if "marketScore" in item:
        assert isinstance(item["marketScore"], (int, float))
    if "signals" in item:
        assert isinstance(item["signals"], dict)
    if "sourceFreshness" in item:
        assert isinstance(item["sourceFreshness"], dict)
    if "evidenceSummary" in item:
        assert isinstance(item["evidenceSummary"], dict)
    if "evidence" in item:
        assert isinstance(item["evidence"], list)


def test_frontend_contract_fields_remain_supported():
    payload = json.loads(Path("src/data/data.ai.json").read_text())

    assert isinstance(payload["updatedAt"], str)
    assert "technologies" in payload
    assert isinstance(payload["technologies"], list)

    for item in payload["technologies"]:
        _assert_public_item_shape(item)

    if "watchlist" in payload:
        assert isinstance(payload["watchlist"], list)
        for item in payload["watchlist"]:
            _assert_public_item_shape(item)

    if "meta" in payload:
        assert isinstance(payload["meta"], dict)
