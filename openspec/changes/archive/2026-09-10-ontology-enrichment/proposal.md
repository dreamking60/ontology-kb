## Why

The phase-1 ontology (20 classes, 13 individuals) was authored from scratch and its FIBO alignment notes used best-effort IRIs that were never verified against the real FIBO distribution. Now that the KB, RAG and agent surfaces all read from `openspec/specs/knowledge-content`, enriching and hardening the ontology directly improves every consumer: search recall (more synonyms/hierarchy), RAG passages (more definitions/attributes), agent tools (more structured content to query), and the reasoning demo (more individuals to classify). This change **enriches and optimizes the ontology** using authoritative public sources — primarily the EDM Council's FIBO (Financial Industry Business Ontology) — under a strict boundary: external content is used only for term/hierarchy alignment and source citation; definitions stay self-authored; FIBO is never imported; verified term IRIs replace the previous best-effort ones.

## What Changes

- **Moderate expansion (per approved scope):** curated classes ~20 → **≥ 50**, corpus individuals ~13 → **~ 35–40**, deepening the existing deposit/loan/wealth-management/account/party branches and adding adjacent concept areas: rate & pricing concepts and account/transaction event concepts.
- **Verified FIBO alignment (replaces best-effort mapping):** during implementation, download the pinned FIBO release modules, extract real class IRIs/labels, and rebuild `ontology/fibo-alignment.ttl` so every `bc:alignedToFibo` annotation resolves to an actually-existing FIBO term; record module + verification in `docs/fibo-alignment.md`. FIBO remains annotation-only (never `owl:imports`).
- **Self-authored, provenance-tracked content:** every new class/card gets bilingual labels, definition, attributes where applicable, and a `skos:editorialNote` marking it as public/generic with its source type; external source URLs and license notes go into a new research dossier `docs/reference/ontology-sources.md`.
- **Correction of known modeling gaps** surfaced by FIBO review, e.g. deposit/account duality (存款 arrangements vs 账户), term deposits vs transaction deposits, savings sub-classes, loan security types, and 客户 role subclasses.
- **Governance & regression:** expanded corpus stays consistent (HermiT satisfiability gate + structural checks green), all existing spec scenarios (search/browse/reasoning/rag/agent) keep passing, and the reasoning rule and synonym examples remain valid.
- No API/UI contract changes; no new dependencies; no internal bank data.

## Capabilities

### New Capabilities

_(none — this change grows content governed by the existing `knowledge-content` capability and adds no new system surface.)_

### Modified Capabilities

- `knowledge-content`: Adds requirements for an expanded, source-verified corpus — coverage targets (≥ 50 curated classes across an extended category set), verified FIBO alignment annotations tied to a pinned release, per-entry provenance and external-source notes, and backward-compatible regression of the existing quality gates.

## Impact

- **Data files**: `ontology/banking-core.ttl` (TBox grows ~30 classes and new object/datatype properties as needed), `ontology/seed-corpora.ttl` (individuals ~13 → ~35–40), `ontology/fibo-alignment.ttl` (rebuilt from verified IRIs).
- **Docs**: `docs/fibo-alignment.md` regenerated (module-level mapping with verification notes); new `docs/reference/ontology-sources.md` research dossier (sources, URLs, licenses, verification date).
- **Tests**: `tests/test_knowledge_content.py` updated for the new coverage minimums/categories and alignment verification; new checks that external alignment IRIs exist in the pinned FIBO snapshot (downloaded under `ontology/reference/fibo-*` during verification, kept out of the commit or pinned by checksum as decided in design).
- **Code**: none of the runtime modules (`kb`, `search`, `reasoning`, `rag`, `agent`, `api`, `ui`) change behavior; only content and tests change.
- **Sources** (verified during planning; pinned during implementation): edmcouncil/fibo on GitHub (`master`) and its release ontology IRIs under `https://spec.edmcouncil.org/fibo/ontology/…`; FIBO module files carry a permissive MIT-style notice permitting use/copy/modification with attribution (each module's `dct:license`).
