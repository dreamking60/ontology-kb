## Context

This change enriches the phase-1 ontology governed by `openspec/specs/knowledge-content` (currently 20 classes / 13 individuals; best-effort, unverified FIBO alignment). Consumers all read that content: search (`search.py`), RAG passages, agent tools, reasoning demo. During planning we verified against the live FIBO repository (edmcouncil/fibo, `master`):

- Real module/IRI layout: e.g. `https://spec.edmcouncil.org/fibo/ontology/FBC/ProductsAndServices/ClientsAndAccounts/` (classes `Account`, `DepositAccount`, `TransactionDepositAccount`, `NonTransactionDepositAccount`, `TimeDepositAccount`, `TimeCertificateOfDepositAccount`, `TimeDepositOpenAccount`, `LoanOrCreditAccount`, `AccountHolder`, `RelationshipManager`, `LendingOfficer`, `IndividualTransaction`, …), `…/FBC/FunctionalEntities/FinancialServicesEntities/` (`Bank`, `DepositoryInstitution`, …), `…/FBC/DebtAndEquities/Debt/` (`CreditAgreement`), `…/FND/ProductsAndServices/ProductsAndServices/` (`Product`, `ContractualProduct`), plus the root `LOAN/` module tree for loans.
- FIBO module files carry a permissive notice (`dct:license`, MIT-style) allowing use/copy/modification with attribution. FIBO stays annotation-only in this project.

Approved scope: FIBO-anchored deepening; moderate scale (classes ≥ 50, individuals ~30–40); terms aligned + self-authored definitions + source citations. All shipped content remains public/generic.

## Goals / Non-Goals

**Goals:**

- Grow and re-balance the TBox: deepen deposit/loan/wealth/account/party branches and add rate-&-pricing and account/transaction-event concept areas (≥ 50 curated classes).
- Grow the ABox to ~30–40 curated public/generic individuals with bilingual labels, definitions, attributes, and provenance notes.
- Replace every best-effort alignment IRI with an IRI verified to exist in a pinned FIBO module; document module + date.
- Keep every existing behavior spec green (search/browse/reasoning/rag/agent) and the ontology consistent under the HermiT gate.

**Non-Goals:**

- No API/UI/endpoint contract changes; no new runtime dependencies; no changes to `kb/search/reasoning/rag/agent` behavior.
- No wholesale FIBO import, no copying of FIBO definition text into the corpus (self-authored definitions only).
- No expansion into market-events/ESG domains (that is a separate future change).
- No internal/confidential bank content; the `internal/` import area stays unused and git-ignored.

## Decisions

### D1: Taxonomy blueprint for the enrichment

Add/refine these branches (each entry self-authored, bilingual, with `skos:editorialNote`):

- **Deposit (存款)**: keep 活期存款/定期存款/大额存单; add 通知存款, 协定存款(企业), 结构性存款, 教育储蓄(optional) and — using FIBO's account-style lens — add account-side classes 存款账户 DepositAccount subtypes only where they add real queries (定期存款账户/活期存款账户) OR model as separate 账户 leafs (decide per naming clash during implementation; keep `Product`-side vs `Account`-side clearly separated in definitions).
- **Loan (贷款)**: 个人贷款 deepens with 消费贷款/经营贷款/汽车贷款/个人住房贷款(已有住房贷款+抵押); add security-typed classes 抵押贷款/质押贷款/保证贷款/信用贷款(已有); corporate side 流动资金贷款/固定资产贷款 as classes.
- **Wealth management (理财)**: add 混合类/权益类/结构性理财 per product classification norms (自撰定义, editorial note marks classification reference).
- **Account (账户)**: add 基本存款账户/一般存款账户/专用存款账户/临时存款账户 (对公结算语境) + 贷款账户; keep 储蓄账户/结算账户.
- **Party (主体)**: add roles 自然人客户/法人客户/同业客户/金融机构客户/员工(演示语境), and 借款人与贷款人 roles if needed for loan relationships.
- **New area — Rate & pricing (利率/定价)**: classes 利率, 固定利率, 浮动利率, 基准利率(LPR 为参考、自撰定义、明确为公开概念), 年化收益率(已有属性 → 提升为类或保持属性；以属性为准, 不加类 unless clean), 计息方式(单利/复利) — model only what queries need.
- **New area — Account/transaction events (账户事件/交易事件)**: classes 交易事件/账户事件 with subclasses 开户/销户/存取款/转账/结息/到期/提前支取/展期 (自撰、通用、无内部案例).

Final list is pinned during implementation by task 1.2/2.x and must satisfy the ≥50/≥30 spec minimums and category coverage; exact leaf sets may vary within those bounds.

**Why FIBO-anchored**: verified FIBO gives us defensible term placement (deposit-account duality, transaction vs non-transaction deposits, loan security vocabulary) and correct IRIs to point at.

### D2: Verified alignment pipeline (replaces best-effort notes)

Implementation downloads the pinned FIBO modules (GitHub `edmcouncil/fibo` at a recorded commit; also mirrored at the spec.edmcouncil.org versioned IRIs like `…/FBC/20260701/ProductsAndServices/ClientsAndAccounts/`), then programmatically extracts `owl:Class`/`owl:NamedIndividual` `rdf:about` IRIs + `rdfs:label` to verify each mapping. `ontology/fibo-alignment.ttl` is regenerated with a small script (`scripts/verify_fibo_alignment.py`, committed) that:
  1. reads the mapping table in `docs/fibo-alignment.md` (source of truth edited by hand),
  2. checks every aligned IRI against the downloaded module files,
  3. fails with a clear list of unresolved IRIs, so a typo can never ship.

Downloaded FIBO snapshots live under `ontology/reference/fibo/` and are **git-ignored** (they are upstream material, several MB); the verification script and CI-friendly `make check-alignment` re-download (or reuse a cached copy) and re-run. `docs/fibo-alignment.md` records module IRI, verification date, and the upstream commit.

- **Alternatives considered**: keeping hand-written best-effort IRIs (the very problem this change fixes); importing FIBO wholesale (license-permitted but heavy and out of scope).

### D3: Provenance and sources dossier

Every entry's `skos:editorialNote` records `Public/generic demo data; aligned per <source-id> (see docs/reference/ontology-sources.md)`. A new dossier lists each source: name, type (FIBO module / public regulation / standard body), URL, verified date, license/copyright notice. Definitions remain self-authored and shorter than FIBO's; nothing is copied verbatim.

**Why**: gives reviewers an auditable chain from each concept back to the public source it was aligned against, satisfying the spec's provenance requirement without licensing risk.

### D4: Regression strategy

Content changes are additive; behavior tests must not be edited to fit content — only `tests/test_knowledge_content.py`'s coverage *numbers/categories* and the new alignment-verification tests are added/updated (they encode the new delta-spec minimums). All other test files run unchanged. The corpus keeps the existing anchors the specs name (存款/定期存款/活期存款/大额存单/信用贷款/住房贷款/理财产品/储蓄账户/结算账户/示例十年期定期存款 etc.), so hierarchy/expansion/synonym/reasoning scenarios stay valid.

## Risks / Trade-offs

- [FIBO IRIs drift across releases] → pin an upstream commit; verification script re-checks all IRIs; doc stores the date/commit.
- [Scope creep of taxonomy] → blueprint bounds the additions; spec caps via minimums + fixed category set; no unbounded "everything" branches.
- [Modeling clash: 产品 vs 账户 (deposit duality)] → definitions explicitly distinguish arrangement/product classes from account classes; where both exist the detail views disambiguate via editorialNote and naming.
- [Test regressions from content change] → D4 anchors preserved; run full suite before archive.
- [Licensing ambiguity] → only term/label alignment + own definitions; dossier quotes each source's notice; no verbatim copying.

## Migration Plan

No runtime migration: swap content files, regenerate alignment + docs, bump tests, `make test`, `make check-consistency`, `openspec validate --specs`. Rollback: revert the content commit — consumers are stateless over the file-backed dataset.

## Open Questions

- Exact FIBO commit/date to pin (choose newest `master` snapshot at implementation start and record it).
- Whether a handful of boundary classes (结构性存款, LPR 基准利率) carry an editorial note flagging them as public-normative references rather than institution-specific products (default: yes, note added).
- Keep downloaded FIBO snapshots cached locally vs re-download per run (default: cache under `ontology/reference/fibo`, git-ignored, `make check-alignment` refreshes on demand).
