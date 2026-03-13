# Market Radar Rethink Design

**Goal:** Replace the current repo-centric ETL with a market-first pipeline that discovers a broad cross-section of the software landscape, then uses an LLM as the final editorial decision-maker to publish a coherent quarterly radar into `src/data/data.ai.json`.

**Problem:** The current pipeline mixes discovery, scoring, and editorial judgment too early. It overweights GitHub/package-style signals, under-represents techniques and mature platforms, and produces a main radar that is structurally too small even when the appendix is repaired. The system is reproducible, but it does not yet behave like a Thoughtworks-style radar with broad market awareness and clear editorial intent.

**Decision:** Rebuild the backend as a two-layer system:

- a broad internal `market snapshot` for discovery and trend understanding
- an `editorial radar` produced by LLM decisions per lane, followed by a small global harmonization pass

The frontend contract stays stable: the only public artifact remains `src/data/data.ai.json`.

## Product Model

The system publishes one quarterly artifact but internally maintains multiple stages.

### 1. Market Snapshot

An internal, wide dataset of canonical entities with structured signals and metadata. This is not optimized for UI consumption; it is optimized for coverage and explainability.

Each entity should answer:

- what it is
- what lane it belongs to
- what ecosystem/languages it lives in
- what evidence supports its presence
- whether its current motion is hype, adoption, or steady relevance

### 2. Editorial Radar

The radar is a selective, opinionated artifact. It is not a leaderboard and not a raw market dump.

Each published blip must have:

- a stable canonical identity
- a single editorial lane
- a clear description
- a reason to be in this quarter's radar
- a ring with an explicit thesis

### 3. LLM Editorial Review

The LLM is the final decision-maker, but only after deterministic preprocessing has assembled a coherent candidate pack. The model does not scrape, infer aliases from thin air, or operate over raw source noise.

The LLM is responsible for:

- final inclusion or exclusion
- ring proposal
- editorial phrasing
- redundancy elimination
- comparative judgment inside each lane

## Core Principle

**Discovery is deterministic. Editorial judgment is LLM-driven. Publication is contract-validated.**

This gives the LLM maximum leverage where it is strongest, while keeping the data pipeline understandable and debuggable.

## Lane Model

The editorial process runs by lanes to keep prompts small and comparisons meaningful:

- `languages`
- `frameworks`
- `tools`
- `platforms`
- `techniques`

The LLM decides lane results independently first, then a small harmonization pass resolves cross-lane conflicts.

## Entity Model

Each internal entity should contain at least:

- `canonical_name`
- `canonical_slug`
- `aliases`
- `editorial_kind`
- `topic_family`
- `implementation_languages`
- `ecosystems`
- `source_evidence`
- `adoption_signals`
- `momentum_signals`
- `maturity_signals`
- `risk_signals`
- `candidate_reason_inputs`

Two concepts must stay distinct:

- `implementation context`: what language/runtime/ecosystem the thing is built in or distributed through
- `editorial kind`: what the thing is for the radar (`language`, `framework`, `tool`, `platform`, `technique`)

This avoids category mistakes like treating "made with TypeScript" as "is a language" or treating a runtime as a framework.

## Data Flow

### Stage 1: Source Collection

Each source is a thin connector that emits raw signals only.

No editorial logic belongs here.

Expected source classes:

- package ecosystems and registries
- dependency graph or dependent-count sources
- community/question sources
- code-hosting sources
- curated editorial corpora

### Stage 2: Canonicalization

Raw entities from sources are merged into canonical subjects.

Responsibilities:

- alias resolution
- package/repo/product consolidation
- lane assignment
- ecosystem tracking
- dedupe

### Stage 3: Signal Assembly

The system computes simple, interpretable features:

- adoption
- momentum
- maturity
- breadth
- stability
- risk

No rings are assigned here.

### Stage 4: Lane Candidate Packs

The snapshot is split into lane-specific editorial packs. Each pack should be compact enough for a single LLM decision call.

Each lane pack should include:

- candidate list
- structured signals
- competing adjacent entities
- suggested rationale inputs
- exclusions or ambiguity notes

### Stage 5: Lane Editorial Decisions

One LLM call per lane.

The model decides:

- include/exclude
- ring
- definition
- thesis for inclusion
- merge/redundancy notes

### Stage 6: Global Harmonization

A final pass resolves:

- duplicate appearance across lanes
- inconsistent terminology
- over-concentration
- mismatched ring language

This pass is lighter than lane review and should not re-discover the whole market.

### Stage 7: Publication

The final editorial decision is mapped into `src/data/data.ai.json`.

The frontend data contract stays stable even if internal stages change.

## Source Strategy

### Languages

Use:

- seeds
- community discussion signals
- GitHub popularity/momentum as secondary signal
- editorial corpus references

Avoid relying on package downloads as primary evidence for languages.

### Frameworks and Tools

Use:

- npm registry
- PyPI
- Maven Central
- crates.io
- dependency/dependent signals
- community usage signals
- GitHub as secondary support

### Platforms

Use:

- seeds
- official/open-source repos
- ecosystem and SDK presence
- package and ecosystem validation
- editorial corpus

Platforms should not depend on "trending repo" discovery to exist.

### Techniques

Use a separate discovery track:

- seeded techniques catalog
- public engineering radars
- engineering blogs
- technical conference/program trends
- community discussion as weak support only

Techniques must be semantically clustered, not package-scored.

## LLM Use Policy

The LLM gets significant authority, but calls stay efficient:

- no one-call-per-entity flow
- one call per lane
- one small harmonization call

The total editorial call budget should stay near:

- 5 lane calls
- 1 harmonization call

Optional retries only for invalid output.

## Validation Rules

Before publication, deterministic checks must enforce:

- valid JSON contract
- no duplicate canonical subjects across lanes
- every published blip has a definition
- every published blip has a thesis
- every blip has a valid lane and ring
- no unresolved alias collision
- no empty quarterly radar section caused by malformed editorial output

## Repository Cleanup

This redesign is also a simplification project.

Expected cleanup:

- remove old ETL code paths that mix editorial logic into discovery
- remove dead tests for obsolete scoring/distribution assumptions
- remove dead config keys tied to the current pipeline shape
- reduce artifact sprawl
- make module responsibilities obvious from path names

## Success Criteria

This redesign is successful when:

- the internal snapshot is broad and market-aware
- the final radar is coherent and thesis-driven
- each blip feels intentionally selected rather than accidentally scored
- the LLM works over structured candidate packs, not raw noise
- `src/data/data.ai.json` remains stable for the frontend
- the repo is simpler after the rewrite, not more layered
