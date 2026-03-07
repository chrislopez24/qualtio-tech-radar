from datetime import datetime, timedelta, timezone

from etl.source_cache import SourceCache


def test_source_cache_persists_positive_entries(tmp_path):
    cache_path = tmp_path / "stackexchange-cache.json"
    cache = SourceCache(cache_path)
    observed_at = datetime(2026, 3, 7, tzinfo=timezone.utc)

    cache.put("react", [{"count": 10}], ttl_seconds=3600, observed_at=observed_at)

    reloaded = SourceCache(cache_path)
    hit = reloaded.get("react", now=observed_at + timedelta(minutes=10))

    assert hit is not None
    assert hit.negative is False
    assert hit.value == [{"count": 10}]


def test_source_cache_persists_negative_entries(tmp_path):
    cache_path = tmp_path / "pypistats-cache.json"
    cache = SourceCache(cache_path)
    observed_at = datetime(2026, 3, 7, tzinfo=timezone.utc)

    cache.put_negative("unknown-package", ttl_seconds=86400, observed_at=observed_at)

    reloaded = SourceCache(cache_path)
    hit = reloaded.get("unknown-package", now=observed_at + timedelta(hours=1))

    assert hit is not None
    assert hit.negative is True
    assert hit.value is None


def test_source_cache_expires_entries_after_ttl(tmp_path):
    cache_path = tmp_path / "deps-dev-cache.json"
    cache = SourceCache(cache_path)
    observed_at = datetime(2026, 3, 7, tzinfo=timezone.utc)

    cache.put("npm:react", [{"version": "19.0.0"}], ttl_seconds=60, observed_at=observed_at)

    reloaded = SourceCache(cache_path)

    assert reloaded.get("npm:react", now=observed_at + timedelta(seconds=59)) is not None
    assert reloaded.get("npm:react", now=observed_at + timedelta(seconds=61)) is None
