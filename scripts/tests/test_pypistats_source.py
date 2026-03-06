from unittest.mock import Mock, patch

from etl.config import PyPIStatsSource as PyPIStatsConfig
from etl.sources.pypistats import PyPIStatsSource


def test_pypistats_source_maps_recent_downloads_to_evidence():
    config = PyPIStatsConfig(enabled=True)
    source = PyPIStatsSource(config)

    with patch.object(source.session, "get") as mock_get:
        response = Mock()
        response.raise_for_status.return_value = None
        response.json.return_value = {
            "data": {
                "last_day": 12000,
                "last_week": 90000,
                "last_month": 320000,
            }
        }
        mock_get.return_value = response

        evidence = source.fetch(["fastapi"])

    assert len(evidence) == 1
    assert evidence[0].source == "pypistats"
    assert evidence[0].metric == "downloads_last_month"
    assert evidence[0].subject_id == "fastapi"
    assert evidence[0].raw_value == 320000


def test_pypistats_source_skips_invalid_subjects():
    config = PyPIStatsConfig(enabled=True)
    source = PyPIStatsSource(config)

    assert source.fetch(["fast api"]) == []
