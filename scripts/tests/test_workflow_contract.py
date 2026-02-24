from pathlib import Path


def test_workflow_uses_expected_secrets_and_commands():
    text = Path(".github/workflows/weekly-update.yml").read_text()
    assert "GH_TOKEN" in text