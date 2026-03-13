# External Source Limits and Access (2026-03-07)

## Purpose

Document practical limits/access constraints for the ETL sources used (or considered) in Radar V2.

## Current Production Sources

1. GitHub REST API
- Access: public endpoints without key; authenticated access with `GH_TOKEN`.
- Practical limit: unauthenticated `60 req/hour`; authenticated `5,000 req/hour`.
- Source: https://docs.github.com/en/rest/using-the-rest-api/rate-limits-for-the-rest-api

2. Hacker News API
- Access: public API, no API key required.
- Source: https://github.com/HackerNews/API

3. deps.dev API
- Access: no API key required.
- Source: https://docs.deps.dev/get-started/

4. OSV API
- Access: no API key required.
- Notes: supports batched querying (`/v1/querybatch`) for lower request pressure.
- Source: https://google.github.io/osv.dev/api/

## Free Alternatives Evaluated

1. OSS Insight Public API
- Access: no auth required for baseline usage.
- Limit: `600 requests/hour` per IP.
- Source: https://ossinsight.io/docs/api/

2. ecosyste.ms APIs
- Access: open API surface for package/dependency metadata.
- Source: https://ecosyste.ms/api

3. Libraries.io (optional only)
- Access: API key required.
- Source: https://libraries.io/api

## Decision

- Keep production ETL on: `github + hackernews` for discovery, `deps.dev + osv` for validation.
- Treat `ossinsight` and `ecosyste.ms` as next optional adapters for added corroboration.
- Do not block Radar V2 quality on `libraries.io` account availability.
