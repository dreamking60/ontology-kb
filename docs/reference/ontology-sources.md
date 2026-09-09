# External Source Dossier

Sources used for **term/hierarchy alignment and taxonomy guidance** in the
`ontology-enrichment` change. Rule applied throughout: external ontologies are
used for alignment and citation only — every definition and label in this
repository is **self-authored**; no external definition text is copied into the
corpus.

| # | Source | Type | URL | Verified | License / notice |
|---|---|---|---|---|---|
| 1 | FIBO (Financial Industry Business Ontology) — EDM Council / OMG | OWL ontologies (module files) | https://github.com/edmcouncil/fibo (commit `119fa8c091aa4beece7d22aefa6fe138021a4355`); published module IRIs under https://spec.edmcouncil.org/fibo/ontology/… | 2026-09-09 | Each module's `dct:license` is a permissive notice (copyright EDM Council / OMG; "Permission is hereby granted, free of charge … to use, copy, modify, merge, publish, distribute …"; see https://opensource.org/licenses/MIT). Used for alignment only; definitions here are self-authored. |

Downloaded snapshot files (used once to build `docs/reference/fibo-verified.json`
and verify alignment IRIs) are kept under `ontology/reference/fibo/` and are
**git-ignored**; the compact verified index and the pinned commit SHA are
committed so verification stays reproducible offline.

## How each corpus entry is tied to a source

Every class/individual that was placed or refined using a source carries a
`skos:editorialNote` beginning with `Public generic …` and, where aligned,
references FIBO review and this dossier (e.g. `aligned per FIBO review
(ontology-enrichment); see docs/reference/ontology-sources.md`).
