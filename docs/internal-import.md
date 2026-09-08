# Internal Data Import (git-ignored, never committed)

Shipped content is public and generic. When you want to try real (internal)
content **locally** without risking it in the repository:

1. Create the `internal/` directory at the repo root — it is in `.gitignore`,
   so it will never be committed:

   ```bash
   mkdir -p internal
   ```

2. Drop one or more Turtle files there, using the same `bc:`/`ex:` vocabulary
   and card conventions as `ontology/seed-corpora.ttl` (labels, `skos:definition`,
   attributes). Example `internal/my-notes.ttl`:

   ```turtle
   @prefix bc: <https://ontology.example/banking-core#> .
   @prefix ex: <https://ontology.example/seed#> .
   @prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
   @prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .

   ex:MyInternalNote a bc:Product ;
       rdfs:label "内部备注示例"@zh, "Internal note example"@en ;
       bc:riskLevel "中" .
   ```

3. Verify parsing and counts **without** shipping the data:

   ```bash
   make load-internal
   ```

4. The demo server (`make api`) intentionally loads only `ontology/*.ttl`, so
   internal data never leaks into the demo API by accident.

Guardrails: never `git add -f internal/`; keep internal content out of
`ontology/seed-corpora.ttl`; when sharing the repo, delete or rotate any
internal files first.
