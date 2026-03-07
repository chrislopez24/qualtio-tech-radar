from etl.canonical_mapping import deps_dev_subject_for, pypistats_subject_for, stackexchange_tags_for


def test_stackexchange_tags_for_known_aliases():
    assert stackexchange_tags_for("next.js") == ["next.js", "nextjs"]
    assert stackexchange_tags_for("node") == ["node", "node.js", "nodejs"]


def test_deps_dev_subject_for_uses_explicit_package_overrides():
    assert deps_dev_subject_for("Next.js", ecosystem="npm") == "npm:next"
    assert deps_dev_subject_for("Django", ecosystem="pypi") == "pypi:django"
    assert deps_dev_subject_for("PyTorch", ecosystem="pypi") == "pypi:torch"
    assert deps_dev_subject_for("LangChain", ecosystem="pypi") == "pypi:langchain"


def test_deps_dev_subject_for_avoids_naive_fallbacks_for_go_repositories():
    assert deps_dev_subject_for("kubernetes", ecosystem="go") is None
    assert deps_dev_subject_for("ollama", ecosystem="go") is None


def test_pypistats_subject_for_only_returns_canonical_or_plausible_packages():
    assert pypistats_subject_for("Django") == "django"
    assert pypistats_subject_for("PyTorch") == "torch"
    assert pypistats_subject_for("LangFlow") == "langflow"
    assert pypistats_subject_for("Python") is None
    assert pypistats_subject_for("AutoGPT") is None
