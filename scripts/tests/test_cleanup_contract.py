from pathlib import Path


def test_obsolete_pipeline_modules_are_not_imported_by_main():
    content = Path("scripts/main.py").read_text()

    assert "RadarPipeline" not in content
    assert not Path("scripts/etl/pipeline.py").exists()
