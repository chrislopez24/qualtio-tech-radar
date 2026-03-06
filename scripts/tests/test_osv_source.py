from unittest.mock import Mock, patch

from etl.config import OSVSource as OSVConfig
from etl.sources.osv_source import OSVSource


def test_osv_source_maps_querybatch_results_to_vulnerability_evidence():
    config = OSVConfig(enabled=True)
    source = OSVSource(config)

    with patch.object(source.session, "post") as mock_post:
        response = Mock()
        response.raise_for_status.return_value = None
        response.json.return_value = {
            "results": [
                {
                    "vulns": [
                        {"id": "OSV-2026-1"},
                        {"id": "OSV-2026-2"},
                    ]
                }
            ]
        }
        mock_post.return_value = response

        evidence = source.fetch(["pypi:fastapi@0.110.0"])

    assert len(evidence) == 1
    assert evidence[0].source == "osv"
    assert evidence[0].metric == "known_vulnerabilities"
    assert evidence[0].subject_id == "pypi:fastapi@0.110.0"
    assert evidence[0].raw_value == 2


def test_osv_source_requires_versioned_subjects():
    config = OSVConfig(enabled=True)
    source = OSVSource(config)

    assert source.fetch(["pypi:fastapi"]) == []


def test_osv_source_maps_known_ecosystem_names_for_api_queries():
    config = OSVConfig(enabled=True)
    source = OSVSource(config)

    with patch.object(source.session, "post") as mock_post:
        response = Mock()
        response.raise_for_status.return_value = None
        response.json.return_value = {"results": [{"vulns": []}]}
        mock_post.return_value = response

        source.fetch(["pypi:fastapi@0.110.0"])

    payload = mock_post.call_args.kwargs["json"]
    assert payload["queries"][0]["package"]["ecosystem"] == "PyPI"
