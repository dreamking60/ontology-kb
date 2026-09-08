"""API contract tests (design.md D4; specs endpoints surface)."""
from __future__ import annotations

from fastapi.testclient import TestClient

from banking_kb.api import app

client = TestClient(app)


def test_health():
    resp = client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"
    assert resp.json()["triples"] > 0


def test_search_hit():
    resp = client.get("/api/concepts", params={"q": "定存"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["count"] >= 1
    assert body["results"][0]["label_zh"] == "定期存款"


def test_search_miss_is_200_empty():
    resp = client.get("/api/concepts", params={"q": "完全不存在zzz"})
    assert resp.status_code == 200
    assert resp.json()["count"] == 0
    assert resp.json()["results"] == []


def test_concept_detail_by_local_name():
    resp = client.get("/api/concepts/CertificateOfDeposit")
    assert resp.status_code == 200
    body = resp.json()
    assert body["labels"]["zh"] == "大额存单"
    assert body["superclass"]["label"] == "定期存款"


def test_concept_detail_by_prefixed_name():
    resp = client.get("/api/concepts/bc:Loan")
    assert resp.status_code == 200
    assert resp.json()["labels"]["zh"] == "贷款"


def test_concept_detail_unknown_404():
    assert client.get("/api/concepts/NoSuchConceptXyz").status_code == 404


def test_tree():
    resp = client.get("/api/tree")
    assert resp.status_code == 200
    labels = [r["label_zh"] for r in resp.json()["roots"]]
    assert labels == ["产品", "账户", "主体"]


def test_reasoning_demo_payload():
    resp = client.post("/api/reasoning/demo")
    assert resp.status_code == 200
    body = resp.json()
    for key in (
        "asserted_type_facts",
        "inferred_type_facts",
        "rule_derived_facts",
        "store_unchanged",
        "consistency",
    ):
        assert key in body
    assert body["store_unchanged"]["unchanged"] is True
    assert any(f["subject_label"] == "示例十年期定期存款" for f in body["rule_derived_facts"])
