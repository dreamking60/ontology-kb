"""Streamlit demo UI for the banking concept knowledge base (MVP).

Three panels mapped to the OpenSpec delta specs:
- Search  (specs/concept-search)
- Browse  (specs/concept-browser)
- Reasoning demo (specs/reasoning-demo)

Requires the FastAPI server:  make api
"""
from __future__ import annotations

import os
from urllib.parse import quote

import requests
import streamlit as st

API = os.getenv("BANKING_KB_API", "http://127.0.0.1:8000")

st.set_page_config(page_title="银行概念知识库 Demo", page_icon="🏦", layout="wide")
st.title("🏦 银行概念知识库 · Ontology Demo")
st.caption("OpenSpec change `banking-concept-kb-mvp` — 语义搜索 / 概念浏览 / 规则推理")


def _get(path: str, **params) -> dict | None:
    try:
        resp = requests.get(f"{API}{path}", params=params or None, timeout=10)
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException as exc:
        st.error(f"无法连接 API（{API}）：{exc}\n请先运行 `make api`。")
        return None


def _post(path: str) -> dict | None:
    try:
        resp = requests.post(f"{API}{path}", timeout=30)
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException as exc:
        st.error(f"无法连接 API（{API}）：{exc}\n请先运行 `make api`。")
        return None


def _post_json(path: str, payload: dict) -> dict | None:
    try:
        resp = requests.post(f"{API}{path}", json=payload, timeout=60)
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException as exc:
        st.error(f"无法连接 API（{API}）：{exc}\n请先运行 `make api`。")
        return None


def prefixed(iri: str) -> str:
    """bc:xxx / ex:xxx form of an IRI, for path parameters."""
    for prefix, ns in (("bc", "https://ontology.example/banking-core#"),
                       ("ex", "https://ontology.example/seed#")):
        if iri.startswith(ns):
            return f"{prefix}:{iri[len(ns):]}"
    return iri


def render_detail(detail: dict) -> None:
    labels = detail.get("labels", {})
    st.subheader(labels.get("zh") or labels.get("en") or detail["id"])
    st.caption(f"{labels.get('en') or ''} · kind={detail['kind']}")
    if detail.get("definition"):
        st.markdown(detail["definition"])
    if detail.get("synonyms"):
        st.markdown("**同义词 / synonyms:** " + "、".join(detail["synonyms"]))
    if detail.get("superclass"):
        st.markdown(f"**上级类:** {detail['superclass']['label']}")
    if detail.get("subclasses"):
        st.markdown("**子类:** " + "、".join(s["label"] for s in detail["subclasses"]))
    if detail.get("types"):
        st.markdown("**类型:** " + "、".join(t["label"] for t in detail["types"]))
    if detail.get("attributes"):
        st.markdown("**属性 / attributes:**")
        st.table(
            [
                {"属性": a["property_label"], "值": a["value"], "类型": a["datatype"]}
                for a in detail["attributes"]
            ]
        )
    if detail.get("relationships"):
        st.markdown("**关系 / relationships:**")
        for r in detail["relationships"]:
            st.markdown(f"- **{r['property_label']}** → {r['value_label']} (`{r['value']}`)")


# --------------------------------------------------------------------------- #
chat_tab, search_tab, browse_tab, reason_tab = st.tabs(
    ["💬 智能问答", "🔎 语义搜索", "🌳 概念浏览", "🧠 推理演示"]
)

with chat_tab:
    st.markdown(
        "基于知识库的 **RAG 问答**：回答只引用本体收录的概念（存款/贷款/理财/账户…）。"
        "未配置 LLM（`BANKING_KB_LLM_*`）时自动降级为确定性摘要（mode=fallback）。"
    )
    if "chat_messages" not in st.session_state:
        st.session_state.chat_messages = []
    for message in st.session_state.chat_messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            if message.get("meta"):
                st.caption(message["meta"])
    prompt = st.chat_input("问知识库…（例如：大额存单和定期存款有什么区别？）")
    if prompt and prompt.strip():
        st.session_state.chat_messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        history = [
            {"role": m["role"], "content": m["content"]}
            for m in st.session_state.chat_messages[-6:-1]
        ]
        with st.chat_message("assistant"):
            with st.spinner("检索知识库并生成回答…"):
                body = _post_json("/api/chat", {"question": prompt, "history": history})
            if body is None:
                st.session_state.chat_messages.pop()
            else:
                st.markdown(body["answer"])
                mode_icon = "🟢 LLM" if body["mode"] == "llm" else "🟡 摘要(fallback)"
                meta_parts = [f"模式：{mode_icon}"]
                if body["citations"]:
                    names = "、".join(c["label"] for c in body["citations"])
                    meta_parts.append(f"引用概念：{names}")
                meta = " · ".join(meta_parts)
                st.caption(meta)
                st.session_state.chat_messages.append(
                    {"role": "assistant", "content": body["answer"], "meta": meta}
                )

with search_tab:
    query = st.text_input("搜索概念（支持中文/英文标签与同义词）", placeholder="例如：存款 / 定存 / 按揭 / deposit")
    if query:
        body = _get("/api/concepts", q=query)
        if body is not None:
            st.success(f"找到 {body['count']} 个概念" if body["count"] else "没有匹配的概念（不是错误）。")
            for result in body["results"]:
                with st.expander(
                    f"{result['label_zh'] or result['label_en']}"
                    f"{'  (' + result['label_en'] + ')' if result['label_zh'] and result['label_en'] else ''}"
                ):
                    render_detail(result)

with browse_tab:
    tree = _get("/api/tree")
    if tree is not None:
        col_a, col_b = st.columns([3, 2])
        flat: list[tuple[str, str, int]] = []  # (label, prefixed id, depth)

        def walk(nodes: list[dict], depth: int) -> None:
            for node in nodes:
                flat.append((f"{'　' * depth}{node['label_zh']} ({node['label_en']})",
                             prefixed(node["id"]), depth))
                walk(node["children"], depth + 1)

        walk(tree["roots"], 0)
        with col_a:
            labels = [f[0] for f in flat]
            choice = st.selectbox("浏览层级（选择查看详情）", labels, index=0)
            idx = labels.index(choice)
            detail = _get(f"/api/concepts/{quote(flat[idx][1], safe=':')}")
            if detail is not None:
                render_detail(detail)
        with col_b:
            st.markdown("**类层级（产品 / 账户 / 主体）：**")
            for label, _pid, depth in flat:
                st.write(("  " * depth) + "• " + label)

with reason_tab:
    st.markdown(
        "运行 **OWL2-RL 推理**（类层级传递）与 **演示规则**（存期 ≥ 60 个月 → 长期定期存款），"
        "每条事实都带溯源标签 `asserted / inferred / rule-derived`，且不会写回数据。"
    )
    if st.button("▶ 运行推理演示", type="primary"):
        body = _post("/api/reasoning/demo")
        if body is not None:
            c1, c2, c3 = st.columns(3)
            c1.metric("声明的类型事实", len(body["asserted_type_facts"]))
            c2.metric("推理得到的类型", len(body["inferred_type_facts"]))
            c3.metric("规则推导事实", len(body["rule_derived_facts"]))

            st.markdown("#### 推理得到的类型（inferred）")
            if body["inferred_type_facts"]:
                st.table([
                    {"个体": f["subject_label"], "推断类型": f["object_label"],
                     "溯源": f["provenance"], "说明": f["explanation"]}
                    for f in body["inferred_type_facts"]
                ])
            else:
                st.info("没有可展示的推理结果。")

            st.markdown("#### 规则推导（rule-derived）")
            if body["rule_derived_facts"]:
                for f in body["rule_derived_facts"]:
                    st.markdown(
                        f"- **{f['subject_label']}** → `rdf:type` → **{f['object_label']}** "
                        f"（{f['rule']['title']}）"
                    )
                    with st.expander("查看规则文本"):
                        st.code(f["rule"]["text"])
            else:
                st.info("规则未命中任何个体。")

            unchanged = body["store_unchanged"]["unchanged"]
            st.markdown(
                f"**数据未被修改:** {unchanged} "
                f"（前后各 {body['store_unchanged']['triples_before']} 条三元组）"
            )
            st.caption(
                f"一致性：{body['consistency']['checked_by']} → {body['consistency']['status']}。"
                f" {body['consistency']['note']}"
            )
