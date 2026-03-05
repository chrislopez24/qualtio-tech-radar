from pathlib import Path


def test_workflow_uses_expected_secrets_and_commands():
    text = Path(".github/workflows/quarterly-update.yml").read_text()
    assert "GH_TOKEN" in text
    assert "src/data/data.ai.json" in text
    assert "data.ai.full.json" not in text


def test_workflow_persists_history_file_and_public_ai_data():
    text = Path(".github/workflows/quarterly-update.yml").read_text()
    assert "src/data/data.ai.history.json" in text
    assert "src/data/data.ai.json" in text


def test_docs_reference_llm_optimization_controls():
    """Documentation should reference llm_optimization configuration"""
    runbook_path = Path("docs/etl-ops-runbook.md")
    assert runbook_path.exists(), "etl-ops-runbook.md must exist"

    text = runbook_path.read_text()
    assert "llm_optimization" in text, "Documentation must reference llm_optimization"
    assert "selective" in text.lower() and "llm" in text.lower(), \
        "Documentation must describe selective LLM policy"


def test_docs_reference_shadow_mode():
    """Documentation should reference shadow mode"""
    runbook_path = Path("docs/etl-ops-runbook.md")
    assert runbook_path.exists(), "etl-ops-runbook.md must exist"

    text = runbook_path.read_text()
    assert "shadow" in text.lower(), "Documentation must reference shadow mode"
    assert "shadow-baseline" in text or "shadow_baseline" in text, \
        "Documentation must describe shadow baseline parameter"


def test_docs_reference_cache_config():
    """Documentation should reference cache configuration"""
    runbook_path = Path("docs/etl-ops-runbook.md")
    assert runbook_path.exists(), "etl-ops-runbook.md must exist"

    text = runbook_path.read_text()
    assert "cache_enabled" in text or "cache-enabled" in text, \
        "Documentation must reference cache_enabled configuration"
    assert "cache_drift" in text.lower(), \
        "Documentation must reference cache drift threshold"


def test_architecture_docs_reference_selective_llm():
    """Architecture documentation should describe selective LLM"""
    arch_path = Path("docs/etl-architecture.md")
    assert arch_path.exists(), "etl-architecture.md must exist"

    text = arch_path.read_text()
    assert "selective" in text.lower(), "Architecture must describe selective LLM"
    assert "borderline" in text.lower(), "Architecture must describe borderline candidates"
    assert "core" in text.lower() and "watchlist" in text.lower(), \
        "Architecture must describe core and watchlist candidates"


def test_architecture_docs_reference_shadow_eval():
    """Architecture documentation should describe shadow evaluation"""
    arch_path = Path("docs/etl-architecture.md")
    assert arch_path.exists(), "etl-architecture.md must exist"

    text = arch_path.read_text()
    assert "shadow" in text.lower(), "Architecture must reference shadow mode"
    assert "core_overlap" in text or "core overlap" in text.lower(), \
        "Architecture must describe core_overlap metric"
    assert "leader_coverage" in text or "leader coverage" in text.lower(), \
        "Architecture must describe leader_coverage metric"


def test_readme_references_selective_llm():
    """README should mention selective LLM optimization"""
    readme_path = Path("README.md")
    assert readme_path.exists(), "README.md must exist"

    text = readme_path.read_text()
    assert "selective" in text.lower(), "README must reference selective LLM"
    assert "70" in text or "reduction" in text.lower(), \
        "README should mention LLM call reduction"


def test_readme_references_quality_evaluation():
    """README should mention quality evaluation features"""
    readme_path = Path("README.md")
    assert readme_path.exists(), "README.md must exist"

    text = readme_path.read_text()
    assert "shadow" in text.lower() or "quality" in text.lower(), \
        "README must reference quality evaluation"
    assert "go/no-go" in text.lower() or "quality gate" in text.lower(), \
        "README should mention quality gates"


def test_quarterly_workflow_supports_shadow_eval_gate():
    """Quarterly workflow should support shadow evaluation gate"""
    workflow_path = Path(".github/workflows/quarterly-update.yml")
    assert workflow_path.exists(), "quarterly-update.yml must exist"

    yml = workflow_path.read_text()
    assert "shadow" in yml.lower(), "Workflow must reference shadow mode"
    assert "shadow-baseline" in yml.lower() or "baseline" in yml.lower(), \
        "Workflow must reference baseline for comparison"
    assert "core_overlap" in yml.lower() or "leader_coverage" in yml.lower(), \
        "Workflow must check quality thresholds"


def test_quarterly_workflow_exposes_shadow_status_outputs():
    """Workflow should expose shadow gate outputs for downstream control"""
    yml = Path(".github/workflows/quarterly-update.yml").read_text()
    assert "shadow_gate_status" in yml
    assert "shadow_gate_pass" in yml
    assert "Resolve Shadow Gate Status" in yml


def test_quarterly_workflow_commits_data_only_on_gate_pass():
    """Data commit step should be gated by shadow gate pass"""
    yml = Path(".github/workflows/quarterly-update.yml").read_text()
    assert "if: ${{ steps.shadow-status.outputs.gate_pass == 'true' }}" in yml


def test_quarterly_workflow_restores_validated_data_on_gate_non_pass():
    """Workflow should restore validated baseline data when gate is not pass"""
    yml = Path(".github/workflows/quarterly-update.yml").read_text()
    assert "restoring validated data snapshot" in yml
    assert "cp artifacts/baseline.json src/data/data.ai.json" in yml
