"""Shared pytest fixtures for the banking-concept-kb-mvp demo."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from banking_kb.kb import KnowledgeBase  # noqa: E402


@pytest.fixture(scope="session")
def kb() -> KnowledgeBase:
    """The knowledge base as loaded from the shipped ontology files."""
    return KnowledgeBase()


@pytest.fixture(scope="session")
def repo_root() -> Path:
    return ROOT
