def test_ring_assignment_avoids_all_adopt_distribution():
    from etl.ring_assignment import assign_rings

    items = [{"id": str(i), "market_score": 70 + (i % 3)} for i in range(24)]
    assigned = assign_rings(items, previous=None)
    rings = {item["ring"] for item in assigned}
    assert len(rings) > 1


def test_ring_assignment_can_enforce_minimum_ring_presence():
    from etl.ring_assignment import assign_rings

    items = [{"id": str(i), "market_score": 92.0} for i in range(8)]
    assigned = assign_rings(
        items,
        previous=None,
        guardrail={"enabled": True, "max_ring_ratio": 1.0, "min_ring_count": 1},
    )
    rings = {item["ring"] for item in assigned}
    assert {"hold", "assess", "trial", "adopt"}.issubset(rings)
