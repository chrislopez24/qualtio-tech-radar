from unittest.mock import Mock, patch

import requests

from etl.config import PyPIStatsSource as PyPIStatsConfig
from etl.sources.pypistats import PyPIStatsSource


def test_pypistats_source_maps_recent_downloads_to_evidence(tmp_path):
    config = PyPIStatsConfig(
        enabled=True,
        cache_file=str(tmp_path / "pypistats-cache.json"),
    )
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


def test_pypistats_source_reuses_persistent_cache_across_instances(tmp_path):
    config = PyPIStatsConfig(
        enabled=True,
        cache_file=str(tmp_path / "pypistats-cache.json"),
    )

    first = PyPIStatsSource(config)
    with patch.object(first.session, "get") as mock_get:
        response = Mock()
        response.raise_for_status.return_value = None
        response.json.return_value = {
            "data": {"last_day": 1, "last_week": 10, "last_month": 1000}
        }
        mock_get.return_value = response

        evidence = first.fetch(["fastapi"])

    assert len(evidence) == 1
    assert mock_get.call_count == 1

    second = PyPIStatsSource(config)
    with patch.object(second.session, "get") as mock_get:
        mock_get.side_effect = AssertionError("persistent cache should avoid network")
        evidence = second.fetch(["fastapi"])

    assert len(evidence) == 1
    assert mock_get.call_count == 0


def test_pypistats_source_negative_cache_skips_repeat_failures(tmp_path):
    config = PyPIStatsConfig(
        enabled=True,
        cache_file=str(tmp_path / "pypistats-cache.json"),
    )

    first = PyPIStatsSource(config)
    with patch.object(first.session, "get") as mock_get:
        error = requests.HTTPError("404")
        error.response = Mock(status_code=404)
        mock_get.side_effect = error
        assert first.fetch(["fastapi"]) == []
        assert mock_get.call_count == 1

    second = PyPIStatsSource(config)
    with patch.object(second.session, "get") as mock_get:
        mock_get.side_effect = AssertionError("negative cache should avoid network")
        assert second.fetch(["fastapi"]) == []
        assert mock_get.call_count == 0


def test_pypistats_source_does_not_persist_rate_limit_failures(tmp_path):
    config = PyPIStatsConfig(
        enabled=True,
        cache_file=str(tmp_path / "pypistats-cache.json"),
    )

    first = PyPIStatsSource(config)
    with patch.object(first.session, "get") as mock_get:
        error = requests.HTTPError("429")
        error.response = Mock(status_code=429)
        mock_get.side_effect = error
        assert first.fetch(["fastapi"]) == []
        assert mock_get.call_count == 1

    second = PyPIStatsSource(config)
    with patch.object(second.session, "get") as mock_get:
        response = Mock()
        response.raise_for_status.return_value = None
        response.json.return_value = {
            "data": {"last_day": 1, "last_week": 10, "last_month": 1000}
        }
        mock_get.return_value = response
        evidence = second.fetch(["fastapi"])

    assert len(evidence) == 1
    assert mock_get.call_count == 1
