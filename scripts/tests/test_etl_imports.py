def test_new_market_radar_modules_are_importable():
    import etl.discovery
    import etl.canonical
    import etl.signals
    import etl.lanes
    import etl.editorial_llm
    import etl.publish

    assert etl.discovery is not None
