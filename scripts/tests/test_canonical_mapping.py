from etl.canonical_mapping import deps_dev_subject_for


def test_deps_dev_subject_for_uses_explicit_package_overrides():
    assert deps_dev_subject_for("Next.js", ecosystem="npm") == "npm:next"
    assert deps_dev_subject_for("Django", ecosystem="pypi") == "pypi:django"
    assert deps_dev_subject_for("PyTorch", ecosystem="pypi") == "pypi:torch"
    assert deps_dev_subject_for("LangChain", ecosystem="pypi") == "pypi:langchain"


def test_deps_dev_subject_for_avoids_naive_fallbacks_for_go_repositories():
    assert deps_dev_subject_for("kubernetes", ecosystem="go") is None
    assert deps_dev_subject_for("ollama", ecosystem="go") is None
