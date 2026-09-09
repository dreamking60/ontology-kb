#!/usr/bin/env python3
"""Verify every bc:alignedToFibo annotation resolves to a real FIBO term.

Resolution source:
1. If the downloaded FIBO module files are present under ontology/reference/fibo/
   (git-ignored), re-parse them and check against the live extraction.
2. Otherwise check against the committed compact index
   docs/reference/fibo-verified.json (built from the pinned snapshot,
   edmcouncil/fibo commit 119fa8c091aa4beece7d22aefa6fe138021a4355).

Exit 0 when every annotation resolves; exit 1 and list unresolved IRIs
otherwise. Run via:  make check-alignment
"""
from __future__ import annotations

import glob
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SYSTEM_PATH = str(ROOT / "src")
if SYSTEM_PATH not in sys.path:
    sys.path.insert(0, SYSTEM_PATH)

from banking_kb.kb import BC, KnowledgeBase  # noqa: E402
from rdflib import OWL, RDF, Graph  # noqa: E402


def _manifest_index() -> dict[str, dict[str, str]]:
    with open(ROOT / "docs/reference/fibo-verified.json", encoding="utf-8") as fh:
        return json.load(fh)


def _raw_index() -> dict[str, dict[str, str]] | None:
    files = sorted(glob.glob(str(ROOT / "ontology/reference/fibo/*.rdf")))
    if not files:
        return None
    mods: dict[str, dict[str, str]] = {}
    for path in files:
        graph = Graph().parse(path, format="xml")
        module = os.path.basename(path)[:-4]
        mapping = {
            str(s).rstrip("/").split("/")[-1]: str(s)
            for s in set(graph.subjects(RDF.type, OWL.Class))
            | set(graph.subjects(RDF.type, OWL.NamedIndividual))
        }
        mods[module] = mapping
    return mods


def main() -> int:
    kb = KnowledgeBase()
    aligned = sorted({str(o) for o in kb.graph.objects(None, BC.alignedToFibo)})
    index = _raw_index() or _manifest_index()
    known = {iri for module in index.values() for iri in module.values()}
    unresolved = [iri for iri in aligned if iri not in known]
    print(f"FIBO alignment check: {len(aligned)} annotations, "
          f"checked against {'live FIBO modules' if _raw_index() else 'committed verified index'}.")
    if unresolved:
        print("UNRESOLVED alignment IRIs:")
        for iri in unresolved:
            print(f"  - {iri}")
        return 1
    print("OK — every aligned IRI resolves to a real FIBO term in the pinned snapshot.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
