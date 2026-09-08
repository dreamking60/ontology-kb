# FIBO Alignment (banking-core → FIBO terms)

This note lists every class-to-FIBO mapping declared in
`ontology/fibo-alignment.ttl` (`bc:alignedToFibo` annotations). Alignment is
**annotation only** — FIBO is never imported, so loading the demo never touches
the network and carries no FIBO licensing weight.

> **Verification caveat (MVP):** term IRIs below follow the
> `https://spec.edmcouncil.org/fibo/ontology/...` pattern and are best-effort
> for the demo. Before production use, verify each IRI against the current
> FIBO 2.0 release and adjust the annotation values — the ontology structure
> does not depend on these strings.

| banking-core class | FIBO term (IRI) |
|---|---|
| `bc:Deposit` (存款) | https://spec.edmcouncil.org/fibo/ontology/FND/ProductsAndServices/FinancialProductsAndServices/Deposit |
| `bc:DemandDeposit` (活期存款) | …/FinancialProductsAndServices/Deposit |
| `bc:TimeDeposit` (定期存款) | …/FinancialProductsAndServices/Deposit |
| `bc:CertificateOfDeposit` (大额存单) | …/FinancialProductsAndServices/Deposit |
| `bc:Loan` (贷款) | https://spec.edmcouncil.org/fibo/ontology/FND/ProductsAndServices/FinancialProductsAndServices/Loan |
| `bc:HousingLoan` (住房贷款) | …/FinancialProductsAndServices/Loan |

Classes not listed (e.g. accounts, parties, wealth management) are deliberately
**not mapped** in this MVP — a FIBO term for them was not pinned down yet. The
machine-readable source of truth is `ontology/fibo-alignment.ttl`.
