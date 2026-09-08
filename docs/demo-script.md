# Demo Script — banking-concept-kb-mvp

End-to-end walkthrough of the MVP demo, mirroring the OpenSpec spec scenarios.

## 0. Prerequisites

```bash
make setup
make load        # expect: Loaded 3 file(s): <n> triples, <c> classes, <i> individuals.
```

## 1. Start the servers (two terminals)

```bash
make api         # http://127.0.0.1:8000  (FastAPI, docs at /docs)
make ui          # http://127.0.0.1:8501  (Streamlit)
```

## 2. Semantic search (specs/concept-search)

```bash
curl -s "http://127.0.0.1:8000/api/concepts?q=%E5%AE%9A%E5%AD%98" | python3 -m json.tool | head -40
# q=定存  → first result label_zh == 定期存款 (synonym match)

curl -s "http://127.0.0.1:8000/api/concepts?q=%E5%AD%98%E6%AC%BE" | python3 -m json.tool
# q=存款  → 存款 ranked first; result carries superclass 产品 and subclasses
#           定期存款 / 活期存款 (hierarchy expansion)

curl -s "http://127.0.0.1:8000/api/concepts?q=deposit" | python3 -m json.tool
# English label match

curl -si "http://127.0.0.1:8000/api/concepts?q=zzz%E4%B8%8D%E5%AD%98%E5%9C%A8" | head -1
# → HTTP/1.1 200 with {"count": 0, "results": []} (no-match is not an error)
```

## 3. Concept browser (specs/concept-browser)

```bash
curl -s http://127.0.0.1:8000/api/tree | python3 -m json.tool | head -30
# roots: 产品 / 账户 / 主体; walk 产品 → 存款 → 定期存款 → 大额存单

curl -s http://127.0.0.1:8000/api/concepts/CertificateOfDeposit | python3 -m json.tool
# detail: bilingual labels, synonym CD, definition, superclass 定期存款

curl -s http://127.0.0.1:8000/api/concepts/DemoHousingLoan | python3 -m json.tool
# attributes (期限/利率/风险等级…) + relationship 提供机构 → 示例商业银行
```

In the UI: open the 概念浏览 tab and expand the tree, then select a concept.

## 4. Reasoning demo (specs/reasoning-demo)

```bash
curl -s -X POST http://127.0.0.1:8000/api/reasoning/demo | python3 -m json.tool
```

Expected highlights:

- `inferred_type_facts` includes 示例十年期定期存款 → 存款 (inferred: asserted
  only as 定期存款) and 示例大额存单 → 定期存款 → 存款.
- `rule_derived_facts` includes 示例十年期定期存款 → 长期定期存款（演示分类）,
  carrying the rule text "IF … termMonths >= 60 THEN …".
- every fact carries exactly one provenance tag; `store_unchanged.unchanged` is
  `true` (reasoning never writes back).

Optional satisfiability gate:

```bash
make check-consistency   # HermiT via owlready2 (Java present → [OK] …)
```

## 5. RAG question answering (specs/rag-question-answering)

No-key mode first (deterministic fallback — always works):

```bash
curl -s -X POST http://127.0.0.1:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"question": "大额存单和定期存款有什么区别？"}' | python3 -m json.tool
# expect: mode=fallback, citations include 定期存款/大额存单, answer summarizes both

curl -s -X POST http://127.0.0.1:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"question": "腾讯股价最近怎么样？"}' | python3 -m json.tool
# expect: mode=fallback, citations=[], answer explains 知识库未找到 (no fabrication)

curl -si -X POST http://127.0.0.1:8000/api/chat \
  -H "Content-Type: application/json" -d '{"question": "   "}' | head -1
# expect: HTTP/1.1 422 (empty question rejected, LLM not called)
```

LLM mode (optional; configure `.env`-style exports first — see README):

```bash
export BANKING_KB_LLM_BASE_URL=https://api.deepseek.com/v1
export BANKING_KB_LLM_API_KEY=sk-...   # never commit
export BANKING_KB_LLM_MODEL=deepseek-chat
make api   # restart the server so the env is picked up
curl -s -X POST http://127.0.0.1:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"question": "信用贷款和住房贷款有什么区别？"}' | python3 -m json.tool
# expect: mode=llm, synthesized answer with citations to 信用贷款/住房贷款
```

In the UI, open the **💬 智能问答** tab and chat; sources and mode are shown
under each assistant message.

## 6. Validation & acceptance

```bash
make test
openspec validate --changes rag-concept-qa --strict
```

All spec scenarios have matching pytest tests; the change must stay green before
archive.
