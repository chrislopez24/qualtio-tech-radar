import os
import pytest
from etl.deep_scanner import DeepScanner

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "fixtures")


class TestDeepScanner:
    """Test suite for deep scanner module"""

    def test_deep_scanner_extracts_extra_technologies_from_tree(self):
        """Extract technologies from repository tree structure"""
        scanner = DeepScanner()
        techs = scanner.scan_tree(os.path.join(FIXTURES_DIR, "tree.txt"))
        assert "argocd" in techs

    def test_deep_scanner_returns_empty_for_nonexistent_file(self):
        """Return empty list for non-existent tree file"""
        scanner = DeepScanner()
        techs = scanner.scan_tree(os.path.join(FIXTURES_DIR, "nonexistent.txt"))
        assert techs == []

    def test_deep_scanner_scans_infrastructure_repo(self):
        """Scan infrastructure repository and extract tech"""
        scanner = DeepScanner()
        techs = scanner.scan_tree(os.path.join(FIXTURES_DIR, "infra_repo_tree.txt"))
        assert "terraform" in techs or "kubernetes" in techs

    def test_deep_scanner_respects_repo_allowlist(self):
        """Only scan repos in allowlist when configured"""
        scanner = DeepScanner(allowed_repos=["my-infra-repo"])
        assert scanner.is_repo_allowed("my-infra-repo") is True
        assert scanner.is_repo_allowed("other-repo") is False