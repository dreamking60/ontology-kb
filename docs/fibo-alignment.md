# FIBO Alignment (banking-core → FIBO terms)

Every `bc:alignedToFibo` annotation maps a class in this ontology to a FIBO
class/named individual. This change (ontology-enrichment) **rebuilt the mapping
from best-effort IRIs to IRIs verified against a pinned FIBO snapshot**.

- Upstream pinned: edmcouncil/fibo commit
  `119fa8c091aa4beece7d22aefa6fe138021a4355` (see
  `docs/reference/fibo-upstream-commit.txt`); fetched/verified **2026-09-09**.
- Verification: `scripts/verify_fibo_alignment.py` (`make check-alignment`)
  resolves every annotation against the extracted module index
  (`docs/reference/fibo-verified.json`), and re-checks against the downloaded
  module files when present under `ontology/reference/fibo/`.
- Alignment is **annotation only** — FIBO is never imported into the dataset.
  FIBO module files carry a permissive (MIT-style) notice recorded in
  `docs/reference/ontology-sources.md`. Definitions in this repository are
  **self-authored**, not copied from FIBO.
- Notes: FIBO models deposits as *account* types (DepositAccount,
  TimeDepositAccount, …); our 产品-side deposit classes (存款/定期存款/…) are
  aligned to the nearest FIBO account-style term, and the account-side classes
  (定期存款账户/活期存款账户) align to the same FIBO terms they mirror.

| banking-core class | FIBO module | FIBO term (verified IRI) |
|---|---|---|
| `bc:Product` (产品) | FND/ProductsAndServices/ProductsAndServices | https://spec.edmcouncil.org/fibo/ontology/FND/ProductsAndServices/ProductsAndServices/Product |
| `bc:Account` (账户) | FBC/ProductsAndServices/ClientsAndAccounts | …/ClientsAndAccounts/Account |
| `bc:Deposit` (存款) | FBC/ProductsAndServices/ClientsAndAccounts | …/ClientsAndAccounts/DepositAccount |
| `bc:DemandDeposit` (活期存款) | FBC/ProductsAndServices/ClientsAndAccounts | …/ClientsAndAccounts/DemandDepositAccount |
| `bc:DemandDepositAccount` (活期存款账户) | FBC/ProductsAndServices/ClientsAndAccounts | …/ClientsAndAccounts/DemandDepositAccount |
| `bc:TimeDeposit` (定期存款) | FBC/ProductsAndServices/ClientsAndAccounts | …/ClientsAndAccounts/TimeDepositAccount |
| `bc:TimeDepositAccount` (定期存款账户) | FBC/ProductsAndServices/ClientsAndAccounts | …/ClientsAndAccounts/TimeDepositAccount |
| `bc:CertificateOfDeposit` (大额存单) | FBC/ProductsAndServices/ClientsAndAccounts | …/ClientsAndAccounts/TimeCertificateOfDepositAccount |
| `bc:SavingsAccount` (储蓄账户) | FBC/ProductsAndServices/ClientsAndAccounts | …/ClientsAndAccounts/NonTransactionDepositAccount |
| `bc:SettlementAccount` (结算账户) | FBC/ProductsAndServices/ClientsAndAccounts | …/ClientsAndAccounts/TransactionDepositAccount |
| `bc:LoanAccount` (贷款账户) | FBC/ProductsAndServices/ClientsAndAccounts | …/ClientsAndAccounts/LoanOrCreditAccount |
| `bc:Bank` (银行) | FBC/FunctionalEntities/FinancialServicesEntities | …/FinancialServicesEntities/Bank |
| `bc:Loan` (贷款) | LOAN/LoansGeneral/Loans | …/LOAN/LoansGeneral/Loans/Loan |
| `bc:HousingLoan` (住房贷款) | LOAN/RealEstateLoans/Mortgages | …/LOAN/RealEstateLoans/Mortgages/Mortgage |
| `bc:ConsumptionLoan` (消费贷款) | LOAN/LoansSpecific/ConsumerLoans | …/LOAN/LoansSpecific/ConsumerLoans/ConsumerLoan |

Classes not listed (wealth management, parties/roles, rate & banking-event
concepts, and security-dimension loan classes) are deliberately **not mapped**
in this change — either FIBO has no clean one-to-one term in the pinned modules
we consume, or alignment was judged lower value than its semantic risk.
