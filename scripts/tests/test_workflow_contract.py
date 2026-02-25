from pathlib import Path


def test_workflow_uses_expected_secrets_and_commands():
    text = Path(".github/workflows/weekly-update.yml").read_text()
    assert "GH_TOKEN" in text
    assert "src/data/data.ai.json" in text
    assert "data.ai.full.json" not in text


def test_workflow_persists_history_file_and_public_ai_data():
    text = Path(".github/workflows/weekly-update.yml").read_text()
    assert "src/data/data.ai.history.json" in text
    assert "src/data/data.ai.json" in text
