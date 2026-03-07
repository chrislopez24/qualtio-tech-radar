from types import SimpleNamespace

from etl.quadrant_logic import infer_quadrant


def make_tech(name, description="", language="", topics=None):
    return SimpleNamespace(
        name=name,
        description=description,
        language=language,
        topics=topics or [],
    )


def test_infer_quadrant_keeps_actual_language_in_languages():
    tech = make_tech(
        "TypeScript",
        description="A programming language for building large JavaScript applications",
        language="TypeScript",
    )

    assert infer_quadrant(tech) == "languages"


def test_infer_quadrant_does_not_treat_framework_language_as_language():
    tech = make_tech(
        "PyTorch",
        description="Machine learning framework for Python",
        language="Python",
        topics=["framework", "machine-learning"],
    )

    assert infer_quadrant(tech) == "tools"


def test_infer_quadrant_does_not_treat_ui_shell_language_as_language():
    tech = make_tech(
        "open-webui",
        description="Self-hosted AI web interface and UI shell",
        language="Python",
        topics=["ui", "tooling"],
    )

    assert infer_quadrant(tech) == "tools"


def test_infer_quadrant_does_not_treat_cli_language_as_language():
    tech = make_tech(
        "youtube-dl",
        description="Command-line tool for downloading videos",
        language="Python",
        topics=["cli", "tool"],
    )

    assert infer_quadrant(tech) == "tools"


def test_infer_quadrant_keeps_language_named_resource_in_techniques():
    tech = make_tech(
        "Rust async patterns",
        description="A guide to async architecture and patterns in Rust",
        language="Rust",
        topics=["patterns", "architecture", "guide"],
    )

    assert infer_quadrant(tech) == "techniques"


def test_infer_quadrant_does_not_promote_language_ecosystem_topic_to_language():
    tech = make_tech(
        "Python packaging ecosystem",
        description="Overview of the Python language ecosystem for packaging practices",
        language="Python",
        topics=["ecosystem", "packaging", "reference"],
    )

    assert infer_quadrant(tech) == "techniques"
