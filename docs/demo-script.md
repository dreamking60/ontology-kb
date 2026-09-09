# Demo Script — banking concept knowledge base (chat-frontend)

End-to-end walkthrough of the MVP demo, mirroring the OpenSpec spec scenarios.

## 0. Prerequisites

```bash
make setup
make load        # expect: Loaded 3 file(s): <n> triples, <c> classes, <i> individuals.
```

## 1. Start the server (one terminal)

```bash
make api          # http://127.0.0.1:8000 — API + web UI (docs at /docs)
```

Open **http://127.0.0.1:8000** in a browser — the LLM-chat web app loads.

## 2. Web UI tour (specs/chat-interface)

- **💬 AI 对话** — chat like an LLM product: bubbles + markdown, mode badge
  (🤖 Agent / 🟢 LLM / 🟡 检索摘要), citation chips, empty-state suggestions.
  Without any LLM configured the sidebar chip reads 「未配置 LLM · 摘要模式」and
  every answer still works as a deterministic retrieval summary (fallback).
- **⚙️ 设置** — configure Base URL / API Key / Model in-app (runtime only,
  masked reads) and watch the status chip turn green; answers then stream.
- **🔎 概念探索** / **🧠 推理演示** — search/tree/detail and the reasoner.

## 3. Semantic search (specs/concept-search)

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

## 4. Concept browser (specs/concept-browser)

```bash
curl -s http://127.0.0.1:8000/api/tree | python3 -m json.tool | head -30
# roots: 产品 / 账户 / 主体; walk 产品 → 存款 → 定期存款 → 大额存单

curl -s http://127.0.0.1:8000/api/concepts/CertificateOfDeposit | python3 -m json.tool
# detail: bilingual labels, synonym CD, definition, superclass 定期存款

curl -s http://127.0.0.1:8000/api/concepts/DemoHousingLoan | python3 -m json.tool
# attributes (期限/利率/风险等级…) + relationship 提供机构 → 示例商业银行
```

In the UI: open **🔎 概念探索**, expand the tree, select a concept to see its detail.

## 5. Reasoning demo (specs/reasoning-demo)

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

## 6. RAG question answering (specs/rag-question-answering)

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

In the UI, chat in the **💬 AI 对话** view; mode badges and citation chips are shown
under each assistant message. With an LLM configured the UI consumes
`/api/chat/stream` and renders answers progressively; without one it still works
in fallback mode (see section 2).

## 7. Agent mode (specs/agentic-question-answering)

No-key mode (deterministic fallback — same grounding, no tools):

```bash
curl -s -X POST http://127.0.0.1:8000/api/agent/chat \
  -H "Content-Type: application/json" \
  -d '{"question": "哪些示例产品受存款保险保障？"}' | python3 -m json.tool
# expect: mode=fallback, trace=[], deterministic summary with citations

curl -si -X POST http://127.0.0.1:8000/api/agent/chat \
  -H "Content-Type: application/json" -d '{"question": " "}' | head -1
# expect: HTTP/1.1 422 (empty question rejected before any LLM call)
```

Agent mode (requires a tool-calling model, same `BANKING_KB_LLM_*` exports):

```bash
curl -s -X POST http://127.0.0.1:8000/api/agent/chat \
  -H "Content-Type: application/json" \
  -d '{"question": "哪些示例产品受存款保险保障？它们的期限分别是多少？"}' | python3 -m json.tool
# expect: mode=agent; trace shows e.g. sparql_query + concept_detail steps;
#         answer cites the matching 示例… deposit products
```

If the configured model rejects `tools`, the endpoint transparently returns
`mode=llm` (phase-2 RAG synthesis). Read-only guarantees: the SPARQL tool only
accepts `SELECT`/`ASK`; `INSERT`/`DELETE`/`LOAD`/`CLEAR` return a read-only
error and the dataset is never changed. In the UI, switch to **🤖 Agent 工具模式** in the **💬 AI 对话** view; the tool
execution timeline is streamed and shown per answer.

## 8. Validation & acceptance

```bash
make test
openspec validate --changes chat-frontend --strict
```

All spec scenarios have matching pytest tests; the change must stay green before
archive.
