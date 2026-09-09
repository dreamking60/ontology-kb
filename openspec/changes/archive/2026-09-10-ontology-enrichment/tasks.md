## 1. Source research and verification pipeline

- [x] 1.1 Record the pinned upstream source snapshot: fetch `edmcouncil/fibo` `master` commit SHA and the module IRI list (ClientsAndAccounts, FinancialProductsAndServices, FinancialServicesEntities, DebtAndEquities/Debt, FND/ProductsAndServices, LOAN/LoansGeneral+LoansSpecific, RealEstateLoans); verify each module file downloads and parse
- [x] 1.2 Extract real `owl:Class`/`owl:NamedIndividual` IRIs + labels from the downloaded modules into a local reference index (`ontology/reference/fibo-index.json`, git-ignored alongside the raw files); verify the index contains the anchor terms (DepositAccount, TimeDepositAccount, Account, Bank, Loan classes, ...)
- [x] 1.3 Author `docs/reference/ontology-sources.md` dossier: per source name/type/URL/verified date/license notice, plus the statement that definitions here are self-authored; verify every source referenced later in corpus notes appears in the dossier

## 2. Ontology TBox enrichment (banking-core.ttl)

- [x] 2.1 Deepen deposit + account branches per design D1 (e.g. 通知存款/协定存款/结构性存款 with editorial notes; 存款账户-side classes kept distinct from 产品 classes) with bilingual labels, definitions, and synonyms; verify parse + bilingual/definition checks pass on the new classes
- [x] 2.2 Deepen loan branch (消费贷款/经营贷款/汽车贷款/流动资金贷款/固定资产贷款; security classes 抵押/质押/保证) and wealth-management branch (混合类/权益类), bilingual + defined; verify new classes appear under the right parents in `kb.tree()`
- [x] 2.3 Add rate & pricing and account/transaction-event areas (利率/固定/浮动、基准利率(LPR 参考注释)、交易事件/账户事件 with 开户/存取款/转账/结息/到期/提前支取/展期 subclasses); verify each has zh/en labels + definitions and the extended category set is fully covered
- [x] 2.4 Add/refine object and datatype properties needed by new cards (e.g. loan security relation, interest reference) within declared entities; verify referential-integrity test stays green and ontology remains OWL2-RL-friendly (owlrl runs clean)

## 3. Corpus ABox enrichment (seed-corpora.ttl)

- [x] 3.1 Add curated public/generic individuals (~20+) for the new classes with bilingual labels, definitions, attributes, `skos:editorialNote` provenance (source-id per design D3); verify every new individual passes bilingual/definition/note checks and no-internal-data markers stay absent
- [x] 3.2 Keep the existing anchor individuals (示例十年期定期存款 etc.) untouched so the demo rule and RAG/agent fixtures remain valid; verify full corpus ≥ 30 individuals and ≥ 50 classes with the coverage test
- [x] 3.3 Extend synonyms where domain vocabulary exists (定存 etc. plus new ones) and verify synonym search still passes for old and new terms

## 4. Verified alignment rebuild

- [x] 4.1 Rebuild `docs/fibo-alignment.md` mapping table (source of truth) using the verified FIBO index from 1.2, mapping existing and new bc: classes to real FIBO IRIs with module + date; verify every row's IRI exists in the reference index
- [x] 4.2 Add `scripts/verify_fibo_alignment.py` + `make check-alignment` that reads the mapping and re-checks every IRI against the downloaded modules, failing with the unresolved list; verify it passes and fails loudly on a deliberately broken IRI
- [x] 4.3 Regenerate `ontology/fibo-alignment.ttl` from the verified mapping; verify a SPARQL sample shows `bc:Deposit`/new classes annotated with resolvable FIBO IRIs and no stale best-effort IRI remains (old `FND/ProductsAndServices/FinancialProductsAndServices/Deposit` style rows gone)

## 5. Tests and governance

- [x] 5.1 Update `tests/test_knowledge_content.py` for the new minimums (≥50 classes, ≥30 individuals, extended category set) and alignment checks; verify the updated suite passes against the enriched corpus
- [x] 5.2 Add alignment-verification tests (every `bc:alignedToFibo` IRI resolvable in the pinned index; doc lists module + date) and regression tests confirming no legacy unverified IRI pattern remains; verify they pass
- [x] 5.3 Run the full suite (search/browser/reasoning/rag/agent tests unchanged) and `make check-consistency`; verify everything green and no inconsistent classes

## 6. Documentation and integration acceptance

- [x] 6.1 Update `docs/fibo-alignment.md` header (verification date/commit, license note, alignment-only statement) and `README.md` corpus stats + sources pointer; verify rendering
- [x] 6.2 Run `make load`, the demo queries (search 定存/按揭, browse 大额存单, reasoning demo, chat fallback, agent fallback) and `openspec validate --specs --strict`; verify all scenarios in the delta spec and the unchanged capability specs are demonstrably met before requesting archive
