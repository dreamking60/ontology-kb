"""Spec coverage: specs/rag-question-answering/spec.md (retrieval & answers)."""
from __future__ import annotations

import httpx
from httpx import MockTransport

from banking_kb import llm, rag
from banking_kb.kb import KnowledgeBase


def _labels(concepts: list[dict]) -> list[str]:
    return [c["label_zh"] or c["label_en"] for c in concepts]


def test_anchor_question_about_known_concept(kb):
    resp = rag.answer_question(kb, "什么是大额存单？")
    assert resp["mode"] == "fallback"
    assert "大额存单" in resp["answer"]
    labels = [c["label"] for c in resp["citations"]]
    assert "大额存单" in labels


def test_synonym_question_retrieves_same_concepts(kb):
    concepts = rag.retrieve(kb, "定存有什么特点？")
    assert concepts and concepts[0]["label_zh"] == "定期存款"
    assert concepts[0]["anchored"] is True


def test_attribute_difference_question_surfaces_both(kb):
    concepts = rag.retrieve(kb, "定期存款和活期存款有什么区别？")
    labels = _labels(concepts)
    assert "定期存款" in labels and "活期存款" in labels


def test_out_of_corpus_question_is_refused(kb):
    resp = rag.answer_question(kb, "腾讯股价最近怎么样？")
    assert resp["mode"] == "fallback"
    assert resp["citations"] == []
    assert "未找到" in resp["answer"]
    assert resp["retrieval_summary"]["matched"] == 0


def test_fallback_answer_summarizes_matched_concepts(kb):
    resp = rag.answer_question(kb, "什么是信用贷款？")
    assert resp["mode"] == "fallback"
    assert "信用贷款" in resp["answer"]
    assert [c["label"] for c in resp["citations"]]  # non-empty citations


def test_passages_carry_definition_and_attributes(kb):
    concepts = rag.retrieve(kb, "大额存单")
    passages = rag.build_passages(concepts)
    assert passages and passages[0].startswith("[1]")
    assert "定义" in passages[0]


def test_llm_mode_grounded_on_passages(kb):
    captured: list[dict] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        return httpx.Response(
            200,
            json={"choices": [{"message": {"role": "assistant", "content": "大额存单是…"}}]},
        )

    cfg = llm.LLMConfig(base_url="https://llm.example/v1", api_key="k", model="m")
    with httpx.Client(transport=MockTransport(handler)) as http:
        resp = rag.answer_question(
            kb,
            "什么是大额存单？",
            history=[
                {"role": "user", "content": "你好"},
                {"role": "assistant", "content": "你好，有什么可以帮你？"},
            ],
            config=cfg,
            http=http,
        )
    assert resp["mode"] == "llm"
    assert resp["answer"] == "大额存单是…"
    assert [c["label"] for c in resp["citations"]]
    body = captured[0].read().decode("utf-8")
    assert "知识库资料" in body and "大额存单" in body  # grounding in prompt
    import json

    payload = json.loads(body)
    roles = [m["role"] for m in payload["messages"]]
    assert roles[0] == "system" and "user" in roles and "assistant" in roles


def test_llm_failure_degrades_to_fallback(kb):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="boom")

    cfg = llm.LLMConfig(base_url="https://llm.example/v1", api_key="k", model="m")
    with httpx.Client(transport=MockTransport(handler)) as http:
        resp = rag.answer_question(kb, "什么是大额存单？", config=cfg, http=http)
    assert resp["mode"] == "fallback"
    assert "降级" in resp["answer"]
