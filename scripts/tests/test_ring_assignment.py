def test_ring_assignment_avoids_all_adopt_distribution():
    from etl.ring_assignment import assign_rings

    items = [{"id": str(i), "market_score": 70 + (i % 3)} for i in range(24)]
    assigned = assign_rings(items, previous=None)
    rings = {item["ring"] for item in assigned}
    assert len(rings) > 1
