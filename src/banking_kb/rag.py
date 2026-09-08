"""Retrieval-augmented question answering over the concept knowledge base
(specs/rag-question-answering, design.md D1/D3/D4).

Pipeline: question -> retrieve concepts (anchors + n-gram overlap) -> build
passages -> optional LLM synthesis with deterministic citations, else a
deterministic fallback summary. Answers are grounded: nothing outside the
retrieved corpus content is used, and out-of-corpus questions get an explicit
not-found response.
"""
from __future__ import annotations

import re
from typing import Optional

from rdflib import URIRef

from . import llm
from .kb import KnowledgeBase

MIN_OVERLAP = 0.25        # minimum fraction of question bigrams covered
MIN_INTERSECTION = 2      # minimum shared bigrams
MAX_CONTEXT = 6           # maximum concepts in one context
MAX_HISTORY = 6           # turns forwarded to the LLM

_NOT_FOUND_MESSAGE = (
    "知识库中未找到与这个问题相关的概念。我只能回答本体收录的银行业务/产品概念"
    "（如 存款、定期存款、大额存单、贷款、理财产品、账户 等）。请换个问法，"
    "或补充具体的概念名称。"
)
_SYSTEM_PROMPT = (
    "你是银行概念知识库助手。你的回答必须只基于用户消息中提供的「知识库资料」，"
    "不得使用资料之外的任何知识，不得编造事实。优先使用与问题相同的语言回答"
    "（默认简体中文）。资料条目编号为 [1][2]…；可以引用它们，但不要声称资料中"
    "不存在的内容。如果资料不足以回答问题，请直接说明知识库未收录。"
)


def normalize_question(question: str) -> str:
    """Lowercase, drop punctuation/whitespace, keep letters/digits/CJK."""
    text = question.strip().lower()
    return re.sub(r"[^\w\u4e00-\u9fff]+", "", text, flags=re.UNICODE)


def _bigrams(text: str) -> set[str]:
    return {text[i : i + 2] for i in range(len(text) - 1)} if len(text) >= 2 else {text}


def _concept_text(kb: KnowledgeBase, uri: URIRef) -> str:
    """Concatenated searchable text for one concept (labels/synonyms/defs/attrs)."""
    parts: list[str] = []
    labels = kb.labels(uri)
    parts.extend([labels["zh"], labels["en"]])
    parts.extend(kb.synonyms(uri))
    parts.append(kb.definition(uri))
    for attr in kb.attributes(uri):
        parts.append(f"{attr['property_label']} {attr['value']}")
    for rel in kb.relationships(uri):
        parts.append(f"{rel['property_label']} {rel['value_label']}")
    if kb.is_class(uri):
        parent = kb.direct_superclass(uri)
        if parent is not None:
            parts.append("上级 " + kb.labels(parent)["zh"])
    text = " ".join(p for p in parts if p)
    return normalize_question(text)


def _is_anchored(kb: KnowledgeBase, uri: URIRef, question: str) -> bool:
    """True when a label/synonym of *uri* appears in the question (full term or
    as a leading prefix of the term, e.g. 按揭 inside 按揭贷款)."""
    labels = kb.labels(uri)
    names = [labels["zh"], labels["en"], *kb.synonyms(uri)]
    for raw in names:
        name = normalize_question(raw)
        if not name:
            continue
        if name in question:
            return True
        if len(name) > 2:
            for cut in range(2, len(name)):
                if name[:cut] in question:
                    return True
    return False


def retrieve(kb: KnowledgeBase, question: str, top_n: int = MAX_CONTEXT) -> list[dict]:
    """Rank concepts for *question*; each entry is a concept_detail + score/anchor."""
    q = normalize_question(question)
    if not q:
        return []
    q_bigrams = _bigrams(q)
    if not q_bigrams:
        return []
    scored: list[tuple[float, URIRef, bool]] = []
    for uri in kb.candidate_concepts():
        anchored = _is_anchored(kb, uri, q)
        if anchored:
            # A label/synonym named in the question is decisive on its own;
            # do not let n-gram gates reject short synonym questions (定存).
            score = 1.0 + (0.05 if kb.is_class(uri) else 0.0)
            scored.append((score, uri, anchored))
            continue
        text = _concept_text(kb, uri)
        if not text:
            continue
        text_bigrams = _bigrams(text)
        shared = q_bigrams & text_bigrams
        if len(shared) < MIN_INTERSECTION:
            continue
        overlap = len(shared) / len(q_bigrams)
        if overlap < MIN_OVERLAP:
            continue
        score = overlap + (0.05 if kb.is_class(uri) else 0.0)
        scored.append((score, uri, anchored))
    scored.sort(key=lambda item: (-item[0], kb.labels(item[1])["zh"] or ""))
    results = []
    for score, uri, anchored in scored[:top_n]:
        detail = kb.concept_detail(uri)
        if detail is None:
            continue
        detail["score"] = round(score, 3)
        detail["anchored"] = anchored
        results.append(detail)
    return results


def build_passages(concepts: list[dict]) -> list[str]:
    """One numbered passage per concept for the LLM prompt."""
    passages = []
    for index, c in enumerate(concepts, start=1):
        label = c["label_zh"] or c["label_en"] or c["id"]
        lines = [f"[{index}] {label}"]
        if c["label_en"] and c["label_zh"]:
            lines[0] += f" ({c['label_en']})"
        if c["definition"]:
            lines.append(f"  定义：{c['definition']}")
        if c.get("attributes"):
            attrs = "、".join(f"{a['property_label']}={a['value']}" for a in c["attributes"])
            lines.append(f"  关键属性：{attrs}")
        if c.get("superclass"):
            lines.append(f"  上级类：{c['superclass']['label']}")
        if c.get("subclasses") and len(c["subclasses"]) <= 6:
            lines.append("  子类：" + "、".join(s["label"] for s in c["subclasses"]))
        passages.append("\n".join(lines))
    return passages


def _fallback_answer(concepts: list[dict], kb: KnowledgeBase) -> str:
    lines = ["以下为基于知识库检索的确定性摘要（未配置大语言模型，mode=fallback）：", ""]
    for c in concepts:
        label = c["label_zh"] or c["label_en"]
        lines.append(f"• {label}" + (f" ({c['label_en']})" if c.get("label_en") else ""))
        if c["definition"]:
            lines.append(f"  定义：{c['definition']}")
        if c.get("attributes"):
            attrs = "、".join(f"{a['property_label']}={a['value']}" for a in c["attributes"])
            lines.append(f"  关键属性：{attrs}")
        if c.get("superclass"):
            lines.append(f"  上级类：{c['superclass']['label']}")
        if c.get("relationships"):
            rels = "、".join(f"{r['property_label']}→{r['value_label']}" for r in c["relationships"])
            lines.append(f"  关系：{rels}")
        lines.append("")
    return "\n".join(lines)


def citations_for(concepts: list[dict]) -> list[dict]:
    return [{"id": c["id"], "label": c["label_zh"] or c["label_en"] or c["id"]} for c in concepts]


def _summary(concepts: list[dict], kb: KnowledgeBase) -> dict:
    return {
        "matched": len(concepts),
        "anchors": [c["label_zh"] or c["label_en"] for c in concepts if c.get("anchored")],
        "top": [c["label_zh"] or c["label_en"] for c in concepts],
    }


def answer_question(
    kb: KnowledgeBase,
    question: str,
    history: Optional[list[dict]] = None,
    config: Optional[llm.LLMConfig] = None,
    http=None,
) -> dict:
    """Answer *question*; returns the /api/chat contract dict."""
    concepts = retrieve(kb, question)
    passages = build_passages(concepts)
    context = concepts
    summary = _summary(concepts, kb)

    if not concepts:
        return {
            "answer": _NOT_FOUND_MESSAGE,
            "mode": "fallback",
            "citations": [],
            "context": context,
            "retrieval_summary": summary,
        }

    cfg = config if config is not None else llm.read_llm_config()
    if cfg is None:
        return {
            "answer": _fallback_answer(concepts, kb),
            "mode": "fallback",
            "citations": citations_for(concepts),
            "context": context,
            "retrieval_summary": summary,
        }

    messages: list[dict] = [{"role": "system", "content": _SYSTEM_PROMPT}]
    if history:
        messages += [
            {"role": m.get("role", "user"), "content": str(m.get("content", ""))}
            for m in history[-MAX_HISTORY:]
            if m.get("role") in ("user", "assistant")
        ]
    materials = "\n\n".join(passages)
    user_content = f"知识库资料：\n{materials}\n\n问题：{question}"
    messages.append({"role": "user", "content": user_content})

    answer = llm.complete(messages, config=cfg, http=http)
    if answer is None:  # endpoint configured but failed -> degrade, don't fail
        return {
            "answer": _fallback_answer(concepts, kb)
            + "\n\n（注：LLM 调用失败，已降级为确定性摘要。）",
            "mode": "fallback",
            "citations": citations_for(concepts),
            "context": context,
            "retrieval_summary": summary,
        }
    return {
        "answer": answer.strip(),
        "mode": "llm",
        "citations": citations_for(concepts),
        "context": context,
        "retrieval_summary": summary,
    }
