def test_canonical_resolver_separates_editorial_kind_from_implementation_context():
    from etl.canonical.resolver import resolve_market_entity

    entity = resolve_market_entity("React", {"ecosystem": "npm"})

    assert entity.editorial_kind == "framework"
    assert "javascript" in entity.implementation_languages or "typescript" in entity.implementation_languages
