# Radar ETL And Frontend Hardening Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Integrar `deps.dev` y `OSV` como validación del ETL, retirar las fuentes obsoletas y refactorizar el frontend para mejorar carga, UX y rendimiento sin degradar el output publicado.

**Architecture:** El discovery primario seguirá siendo `seed_catalog` + GitHub + Hacker News. `deps.dev` y `OSV` se conectarán como enriquecimiento por entidad ya canonizada para reforzar adopción/salud y riesgo, sin introducir nuevas candidatas por sí solos. En frontend, `page.tsx` pasará a server component que entrega datos estáticos a un shell cliente responsable de filtros, URL state y paneles.

**Tech Stack:** Python 3.12, Pydantic, requests, pytest, Next.js 16 App Router, React 19, TypeScript, Vitest, Tailwind CSS.

---

### Task 1: Proteger el ETL con tests de integración

**Files:**
- Modify: `scripts/tests/test_runner.py`
- Modify: `scripts/tests/test_source_cache.py`
- Create: `scripts/tests/test_validation_enrichment.py`

**Step 1: Write the failing tests**

Cubrir:
- `run_market_radar_pipeline` integra evidencias de `deps.dev` y `OSV` sin cambiar discovery primario.
- `SUPPORTED_SOURCE_NAMES` conserva solo discovery primario.
- `SourceCache` no hace flush inmediato en cada `put/get`.

**Step 2: Run tests to verify they fail**

Run: `pytest -q scripts/tests/test_runner.py scripts/tests/test_source_cache.py scripts/tests/test_validation_enrichment.py`

**Step 3: Write minimal implementation**

Implementar capa de enriquecimiento y caché diferida.

**Step 4: Run tests to verify they pass**

Run: `pytest -q scripts/tests/test_runner.py scripts/tests/test_source_cache.py scripts/tests/test_validation_enrichment.py`

### Task 2: Conectar deps.dev y OSV como validación

**Files:**
- Modify: `scripts/main.py`
- Modify: `scripts/etl/runner.py`
- Modify: `scripts/etl/contracts.py`
- Modify: `scripts/etl/canonical/resolver.py`
- Create or Modify: `scripts/etl/validation_enrichment.py`
- Modify: `scripts/etl/signals/snapshot_builder.py`

**Step 1: Preserve output contract**

Mantener discovery primario y añadir evidencia extra por entidad usando mappings canónicos.

**Step 2: Ensure safe fallback**

Si `deps.dev` u `OSV` fallan o no tienen mapping, no se cae el run ni desaparece la entidad.

**Step 3: Verify metadata stability**

El output público debe conservar campos requeridos y seguir publicando `src/data/data.ai.json`.

### Task 3: Eliminar fuentes retiradas

**Files:**
- Modify: `scripts/config.py`
- Modify: `scripts/config.yaml`
- Modify: `scripts/etl/source_registry.py`
- Delete retired source modules and tests.
- Modify: `README.md`
- Modify: `docs/*.md` as needed

**Step 1: Write failing doc/config tests if needed**

**Step 2: Remove code and references**

Quitar clases, config, docs y tests de fuentes retiradas.

**Step 3: Re-run ETL tests**

Run: `pytest -q scripts/tests`

### Task 4: Mover la carga de datos al servidor y estabilizar URL state

**Files:**
- Modify: `src/app/page.tsx`
- Create: `src/components/HomeClient.tsx`
- Delete or Modify: `src/hooks/useRadarData.ts`
- Create: `src/lib/url-state.ts`
- Modify: `src/lib/radar-view-state.ts` if needed
- Create: `src/lib/url-state.test.ts`

**Step 1: Write failing tests**

Cubrir:
- lectura/escritura de `q`, `rings`, `quadrants`, `trends`, `confidence` en URL.
- carga inicial de datos desde props en vez de hook cliente.

**Step 2: Implement minimal server/client split**

`page.tsx` importa `data.ai.json` en server y pasa props serializables al cliente.

**Step 3: Verify tests**

Run: `npm run test -- src/lib/url-state.test.ts`

### Task 5: Mejorar radar responsive y detalle móvil

**Files:**
- Modify: `src/lib/radar-config.ts`
- Modify: `src/components/Radar.tsx`
- Modify: `src/components/Blip.tsx`
- Modify: `src/components/DetailPanel.tsx`
- Add tests to: `src/components/DetailPanel.test.tsx`

**Step 1: Write failing tests**

Cubrir:
- anclaje proporcional sin `800/470` hardcodeado.
- overlay y sheet móvil visibles cuando hay selección.

**Step 2: Implement minimal responsive behavior**

Mantener el viewBox lógico pero anclar y renderizar según contenedor/porcentajes.

**Step 3: Verify tests**

Run: `npm run test -- src/components/DetailPanel.test.tsx`

### Task 6: Mejorar búsqueda, watchlist y primer viewport

**Files:**
- Modify: `src/lib/radar-search.ts`
- Create: `src/lib/radar-search.test.ts`
- Modify: `src/components/WatchlistPanel.tsx`
- Modify: `src/components/WatchlistPanel.test.tsx`
- Modify: `src/components/RadarSidebar.tsx`
- Modify: `src/components/Header.tsx`

**Step 1: Write failing tests**

Cubrir:
- búsqueda por `aliases`, `useCases`, `alternatives`, `evidence`, `owner`, `whyNow`.
- watchlist con fecha base estable desde metadata.

**Step 2: Implement minimal UX changes**

Subir explicación/presets al viewport principal y usar fecha base estable.

**Step 3: Verify tests**

Run: `npm run test -- src/lib/radar-search.test.ts src/components/WatchlistPanel.test.tsx`

### Task 7: Reducir coste tipográfico

**Files:**
- Modify: `src/app/layout.tsx`
- Modify: `src/app/globals.css`
- Modify: `package.json`

**Step 1: Replace fontsource imports**

Pasar a `next/font` con subsets y pesos limitados.

**Step 2: Verify build impact**

Run: `npm run build`

### Task 8: Verificación final

**Files:**
- No code changes expected

**Step 1: Run frontend verification**

Run: `npm run test`

**Step 2: Run lint**

Run: `npm run lint`

**Step 3: Run build**

Run: `npm run build`

**Step 4: Run ETL verification**

Run: `pytest -q scripts/tests`

**Step 5: Inspect output artifacts**

Verificar que `src/data/data.ai.json` mantiene contrato y no pierde campos ni cobertura básica.
