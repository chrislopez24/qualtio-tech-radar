from unittest.mock import Mock, patch

import requests

from etl.config import StackExchangeSource as StackExchangeConfig
from etl.sources.stackexchange import StackExchangeSource


def test_stackexchange_source_normalizes_tag_activity(tmp_path):
    config = StackExchangeConfig(
        enabled=True,
        site="stackoverflow",
        cache_file=str(tmp_path / "stackexchange-cache.json"),
    )
    source = StackExchangeSource(config)

    with patch.object(source.session, "get") as mock_get:
        response = Mock()
        response.raise_for_status.return_value = None
        response.json.return_value = {
            "items": [
                {
                    "name": "typescript",
                    "count": 150000,
                }
            ]
        }
        mock_get.return_value = response

        evidence = source.fetch(["typescript"])

    assert len(evidence) == 1
    assert evidence[0].source == "stackexchange"
    assert evidence[0].metric == "tag_activity"
    assert evidence[0].subject_id == "typescript"
    assert evidence[0].raw_value == 150000


def test_stackexchange_source_skips_empty_subjects():
    config = StackExchangeConfig(enabled=True)
    source = StackExchangeSource(config)

    assert source.fetch(["", "   "]) == []


def test_stackexchange_source_url_encodes_special_tags(tmp_path):
    config = StackExchangeConfig(
        enabled=True,
        site="stackoverflow",
        cache_file=str(tmp_path / "stackexchange-cache.json"),
    )
    source = StackExchangeSource(config)

    with patch.object(source.session, "get") as mock_get:
        response = Mock()
        response.raise_for_status.return_value = None
        response.json.return_value = {"items": [{"name": "c#", "count": 1000}]}
        mock_get.return_value = response

        source.fetch(["c#"])

    assert "/tags/c%23/info" in mock_get.call_args.args[0]


def test_stackexchange_source_reuses_persistent_cache_across_instances(tmp_path):
    config = StackExchangeConfig(
        enabled=True,
        site="stackoverflow",
        cache_file=str(tmp_path / "stackexchange-cache.json"),
    )

    first = StackExchangeSource(config)
    with patch.object(first.session, "get") as mock_get:
        response = Mock()
        response.raise_for_status.return_value = None
        response.json.return_value = {"items": [{"name": "react", "count": 200000}]}
        mock_get.return_value = response

        evidence = first.fetch(["react"])

    assert len(evidence) == 1
    assert mock_get.call_count == 1

    second = StackExchangeSource(config)
    with patch.object(second.session, "get") as mock_get:
        mock_get.side_effect = AssertionError("persistent cache should avoid network")
        evidence = second.fetch(["react"])

    assert len(evidence) == 1
    assert mock_get.call_count == 0


def test_stackexchange_source_negative_cache_skips_repeat_failures(tmp_path):
    config = StackExchangeConfig(
        enabled=True,
        site="stackoverflow",
        cache_file=str(tmp_path / "stackexchange-cache.json"),
    )

    first = StackExchangeSource(config)
    with patch.object(first.session, "get") as mock_get:
        response = Mock()
        response.raise_for_status.return_value = None
        response.json.return_value = {"items": []}
        mock_get.return_value = response
        assert first.fetch(["react"]) == []
        assert mock_get.call_count == 1

    second = StackExchangeSource(config)
    with patch.object(second.session, "get") as mock_get:
        mock_get.side_effect = AssertionError("negative cache should avoid network")
        assert second.fetch(["react"]) == []
        assert mock_get.call_count == 0


def test_stackexchange_source_does_not_persist_rate_limit_failures(tmp_path):
    config = StackExchangeConfig(
        enabled=True,
        site="stackoverflow",
        cache_file=str(tmp_path / "stackexchange-cache.json"),
    )

    first = StackExchangeSource(config)
    with patch.object(first.session, "get") as mock_get:
        error = requests.HTTPError("429")
        error.response = Mock(status_code=429)
        mock_get.side_effect = error
        assert first.fetch(["react"]) == []
        assert mock_get.call_count == 1

    second = StackExchangeSource(config)
    with patch.object(second.session, "get") as mock_get:
        response = Mock()
        response.raise_for_status.return_value = None
        response.json.return_value = {"items": [{"name": "react", "count": 200000}]}
        mock_get.return_value = response
        evidence = second.fetch(["react"])

    assert len(evidence) == 1
    assert mock_get.call_count == 1


def test_stackexchange_source_does_not_persist_throttle_violation_400s(tmp_path):
    config = StackExchangeConfig(
        enabled=True,
        site="stackoverflow",
        cache_file=str(tmp_path / "stackexchange-cache.json"),
    )

    first = StackExchangeSource(config)
    with patch.object(first.session, "get") as mock_get:
        error = requests.HTTPError("400")
        error.response = Mock(status_code=400, headers={"x-error-name": "throttle_violation"})
        mock_get.side_effect = error
        assert first.fetch(["python"]) == []
        assert mock_get.call_count == 1

    second = StackExchangeSource(config)
    with patch.object(second.session, "get") as mock_get:
        response = Mock()
        response.raise_for_status.return_value = None
        response.json.return_value = {"items": [{"name": "python", "count": 500000}]}
        mock_get.return_value = response
        evidence = second.fetch(["python"])

    assert len(evidence) == 1
    assert mock_get.call_count == 1


def test_stackexchange_source_uses_aliases_for_known_tags(tmp_path):
    config = StackExchangeConfig(
        enabled=True,
        site="stackoverflow",
        cache_file=str(tmp_path / "stackexchange-cache.json"),
    )
    source = StackExchangeSource(config)

    with patch.object(source.session, "get") as mock_get:
        first = Mock()
        first.raise_for_status.return_value = None
        first.json.return_value = {"items": []}

        second = Mock()
        second.raise_for_status.return_value = None
        second.json.return_value = {"items": [{"name": "nextjs", "count": 180000}]}

        mock_get.side_effect = [first, second]
        evidence = source.fetch(["next.js"])

    assert len(evidence) == 1
    assert evidence[0].subject_id == "next.js"
    assert mock_get.call_count == 2
    assert "/tags/next.js/info" in mock_get.call_args_list[0].args[0]
    assert "/tags/nextjs/info" in mock_get.call_args_list[1].args[0]


def test_stackexchange_source_respects_api_backoff_for_remaining_subjects(tmp_path):
    config = StackExchangeConfig(
        enabled=True,
        site="stackoverflow",
        cache_file=str(tmp_path / "stackexchange-cache.json"),
    )
    source = StackExchangeSource(config)

    with patch.object(source.session, "get") as mock_get:
        response = Mock()
        response.raise_for_status.return_value = None
        response.json.return_value = {
            "items": [{"name": "react", "count": 200000}],
            "backoff": 10,
        }
        mock_get.return_value = response

        evidence = source.fetch(["react", "python"])

    assert len(evidence) == 1
    assert mock_get.call_count == 1


def test_stackexchange_source_stops_when_request_budget_is_exhausted(tmp_path):
    config = StackExchangeConfig(
        enabled=True,
        site="stackoverflow",
        cache_file=str(tmp_path / "stackexchange-cache.json"),
        request_budget=1,
    )
    source = StackExchangeSource(config)

    with patch.object(source.session, "get") as mock_get:
        response = Mock()
        response.raise_for_status.return_value = None
        response.json.return_value = {"items": [{"name": "react", "count": 200000}]}
        mock_get.return_value = response

        evidence = source.fetch(["react", "python"])

    assert len(evidence) == 1
    assert mock_get.call_count == 1
