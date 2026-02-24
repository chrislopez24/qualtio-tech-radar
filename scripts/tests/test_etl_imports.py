def test_etl_package_imports():
    from etl.pipeline import RadarPipeline
    assert RadarPipeline is not None