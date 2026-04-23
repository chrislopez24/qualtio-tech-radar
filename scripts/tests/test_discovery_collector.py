def test_discovery_collector_aggregates_records_from_multiple_sources():
    from etl.discovery.collector import DiscoveryCollector

    class SourceOne:
        name = "one"

        def fetch(self):
            return [{"name": "React"}]

    class SourceTwo:
        name = "two"

        def fetch(self):
            return [{"name": "Python"}]

    collector = DiscoveryCollector([SourceOne(), SourceTwo()])
    records = collector.collect()

    assert [record["name"] for record in records] == ["React", "Python"]
    assert records[0]["source"] == "one"
    assert records[1]["source"] == "two"


def test_github_discovery_source_keeps_only_seeded_market_entities(monkeypatch):
    from etl.config import ETLConfig
    from etl.discovery.collector import GitHubTrendingDiscoverySource
    from etl.models import TechnologySignal

    def fake_fetch(self):
        return [
            TechnologySignal(
                name="awesome",
                source="github_trending",
                signal_type="github_stars",
                score=8.0,
                raw_data={"name": "awesome", "description": "Awesome list"},
            ),
            TechnologySignal(
                name="next",
                source="github_trending",
                signal_type="github_stars",
                score=9.0,
                raw_data={"name": "next", "description": "The React framework"},
            ),
        ]

    monkeypatch.setattr("etl.discovery.collector.GitHubTrendingSource.fetch", fake_fetch)

    source = GitHubTrendingDiscoverySource(ETLConfig().sources.github_trending)
    records = source.fetch()

    assert [record["name"] for record in records] == ["Next.js"]


def test_hackernews_discovery_source_scans_broad_story_window():
    from etl.config import ETLConfig
    from etl.discovery.collector import HackerNewsDiscoverySource

    source = HackerNewsDiscoverySource(ETLConfig().sources.hackernews)

    assert source.source.max_stories_scan == 500


def test_hackernews_discovery_source_matches_aliases_on_token_boundaries(monkeypatch):
    from etl.config import ETLConfig
    from etl.discovery.collector import HackerNewsDiscoverySource
    from etl.sources.hackernews import HackerNewsItem

    def fake_fetch(self):
        return [
            HackerNewsItem(
                id=1,
                title="Django and MongoDB deployment notes",
                url="https://example.com/google-cloud-notes",
                points=50,
                author="tester",
                created_at=0,
                comment_count=1,
                tech_score=4.0,
            )
        ]

    monkeypatch.setattr("etl.discovery.collector.HackerNewsSource.fetch", fake_fetch)

    source = HackerNewsDiscoverySource(ETLConfig().sources.hackernews)
    records = source.fetch()

    assert {record["name"] for record in records} == {"Django", "MongoDB", "Google Cloud"}
