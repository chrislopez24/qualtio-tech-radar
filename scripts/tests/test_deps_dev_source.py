from unittest.mock import Mock, patch

import requests

from etl.config import DepsDevSource as DepsDevConfig
from etl.sources.deps_dev import DepsDevSource


def test_deps_dev_source_maps_package_to_reverse_dependents_evidence(tmp_path):
    config = DepsDevConfig(
        enabled=True,
        cache_file=str(tmp_path / "deps-dev-cache.json"),
    )
    source = DepsDevSource(config)

    with patch.object(source.session, "get") as mock_get:
        package_response = Mock()
        package_response.raise_for_status.return_value = None
        package_response.json.return_value = {
            "defaultVersionKey": {
                "system": "npm",
                "name": "typescript",
                "version": "5.4.0",
            }
        }

        dependents_response = Mock()
        dependents_response.raise_for_status.return_value = None
        dependents_response.json.return_value = {"totalCount": 1234}

        mock_get.side_effect = [package_response, dependents_response]

        evidence = source.fetch(["npm:typescript"])

    assert len(evidence) == 2
    reverse_dependents = next(record for record in evidence if record.metric == "reverse_dependents")
    default_version = next(record for record in evidence if record.metric == "default_version")
    assert reverse_dependents.source == "deps_dev"
    assert reverse_dependents.subject_id == "npm:typescript"
    assert reverse_dependents.raw_value == 1234
    assert default_version.subject_id == "npm:typescript@5.4.0"
    assert default_version.raw_value == "5.4.0"


def test_deps_dev_source_supports_v3alpha_real_response_shapes(tmp_path):
    config = DepsDevConfig(
        enabled=True,
        cache_file=str(tmp_path / "deps-dev-cache.json"),
    )
    source = DepsDevSource(config)

    with patch.object(source.session, "get") as mock_get:
        package_response = Mock()
        package_response.raise_for_status.return_value = None
        package_response.json.return_value = {
            "packageKey": {"system": "NPM", "name": "react"},
            "versions": [
                {
                    "versionKey": {"system": "NPM", "name": "react", "version": "19.2.4"},
                    "isDefault": True,
                }
            ],
        }

        dependents_response = Mock()
        dependents_response.raise_for_status.return_value = None
        dependents_response.json.return_value = {"dependentCount": 246}

        mock_get.side_effect = [package_response, dependents_response]

        evidence = source.fetch(["npm:react"])

    assert len(evidence) == 2
    reverse_dependents = next(record for record in evidence if record.metric == "reverse_dependents")
    default_version = next(record for record in evidence if record.metric == "default_version")
    assert reverse_dependents.subject_id == "npm:react"
    assert reverse_dependents.raw_value == 246
    assert default_version.subject_id == "npm:react@19.2.4"
    assert default_version.raw_value == "19.2.4"


def test_deps_dev_source_ignores_unparseable_subjects():
    config = DepsDevConfig(enabled=True)
    source = DepsDevSource(config)

    assert source.fetch(["not-a-valid-subject"]) == []


def test_deps_dev_source_url_encodes_scoped_package_names(tmp_path):
    config = DepsDevConfig(
        enabled=True,
        cache_file=str(tmp_path / "deps-dev-cache.json"),
    )
    source = DepsDevSource(config)

    with patch.object(source.session, "get") as mock_get:
        package_response = Mock()
        package_response.raise_for_status.return_value = None
        package_response.json.return_value = {
            "defaultVersionKey": {
                "system": "npm",
                "name": "@types/node",
                "version": "22.0.0",
            }
        }

        dependents_response = Mock()
        dependents_response.raise_for_status.return_value = None
        dependents_response.json.return_value = {"totalCount": 42}

        mock_get.side_effect = [package_response, dependents_response]

        source.fetch(["npm:@types/node"])

    first_url = mock_get.call_args_list[0].args[0]
    assert "%40types%2Fnode" in first_url


def test_deps_dev_source_reuses_persistent_cache_across_instances(tmp_path):
    config = DepsDevConfig(
        enabled=True,
        cache_file=str(tmp_path / "deps-dev-cache.json"),
    )

    first = DepsDevSource(config)
    with patch.object(first.session, "get") as mock_get:
        package_response = Mock()
        package_response.raise_for_status.return_value = None
        package_response.json.return_value = {
            "defaultVersionKey": {"system": "npm", "name": "typescript", "version": "5.4.0"}
        }

        dependents_response = Mock()
        dependents_response.raise_for_status.return_value = None
        dependents_response.json.return_value = {"totalCount": 1234}

        mock_get.side_effect = [package_response, dependents_response]
        evidence = first.fetch(["npm:typescript"])

    assert len(evidence) == 2
    assert mock_get.call_count == 2

    second = DepsDevSource(config)
    with patch.object(second.session, "get") as mock_get:
        mock_get.side_effect = AssertionError("persistent cache should avoid network")
        evidence = second.fetch(["npm:typescript"])

    assert len(evidence) == 2
    assert mock_get.call_count == 0


def test_deps_dev_source_negative_cache_skips_repeat_failures(tmp_path):
    config = DepsDevConfig(
        enabled=True,
        cache_file=str(tmp_path / "deps-dev-cache.json"),
    )

    first = DepsDevSource(config)
    with patch.object(first.session, "get") as mock_get:
        error = requests.HTTPError("404")
        error.response = Mock(status_code=404)
        mock_get.side_effect = error
        assert first.fetch(["npm:typescript"]) == []
        assert mock_get.call_count == 1

    second = DepsDevSource(config)
    with patch.object(second.session, "get") as mock_get:
        mock_get.side_effect = AssertionError("negative cache should avoid network")
        assert second.fetch(["npm:typescript"]) == []
        assert mock_get.call_count == 0


def test_deps_dev_source_does_not_persist_rate_limit_failures(tmp_path):
    config = DepsDevConfig(
        enabled=True,
        cache_file=str(tmp_path / "deps-dev-cache.json"),
    )

    first = DepsDevSource(config)
    with patch.object(first.session, "get") as mock_get:
        error = requests.HTTPError("429")
        error.response = Mock(status_code=429)
        mock_get.side_effect = error
        assert first.fetch(["npm:typescript"]) == []
        assert mock_get.call_count == 1

    second = DepsDevSource(config)
    with patch.object(second.session, "get") as mock_get:
        package_response = Mock()
        package_response.raise_for_status.return_value = None
        package_response.json.return_value = {
            "defaultVersionKey": {"system": "npm", "name": "typescript", "version": "5.4.0"}
        }

        dependents_response = Mock()
        dependents_response.raise_for_status.return_value = None
        dependents_response.json.return_value = {"totalCount": 1234}

        mock_get.side_effect = [package_response, dependents_response]
        evidence = second.fetch(["npm:typescript"])

    assert len(evidence) == 2
    assert mock_get.call_count == 2
