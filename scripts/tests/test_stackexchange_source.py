from unittest.mock import Mock, patch

from etl.config import StackExchangeSource as StackExchangeConfig
from etl.sources.stackexchange import StackExchangeSource


def test_stackexchange_source_normalizes_tag_activity():
    config = StackExchangeConfig(enabled=True, site="stackoverflow")
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


def test_stackexchange_source_url_encodes_special_tags():
    config = StackExchangeConfig(enabled=True, site="stackoverflow")
    source = StackExchangeSource(config)

    with patch.object(source.session, "get") as mock_get:
        response = Mock()
        response.raise_for_status.return_value = None
        response.json.return_value = {"items": [{"name": "c#", "count": 1000}]}
        mock_get.return_value = response

        source.fetch(["c#"])

    assert "/tags/c%23/info" in mock_get.call_args.args[0]
