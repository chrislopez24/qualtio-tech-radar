def test_history_store_retains_rolling_weeks_and_returns_previous_snapshot(tmp_path):
    from etl.history_store import HistoryStore

    store = HistoryStore(tmp_path / "history.json", max_weeks=2)
    store.append_snapshot({"technologies": [{"id": "react", "ring": "trial"}]})
    store.append_snapshot({"technologies": [{"id": "react", "ring": "adopt"}]})

    prev = store.get_previous_snapshot()
    assert prev is not None
