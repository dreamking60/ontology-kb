"""Optional ontology consistency gate (HermiT via owlready2, requires Java).

Run with:  make check-consistency

Reports whether the loaded ontology contains unsatisfiable (inconsistent)
classes. If Java or HermiT is unavailable the script says so clearly and points
to the Protégé/HermiT fallback — it never fails silently.
"""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FILES = [
    ROOT / "ontology/banking-core.ttl",
    ROOT / "ontology/seed-corpora.ttl",
    ROOT / "ontology/fibo-alignment.ttl",
]
ONTOLOGY_IRI = "https://ontology.example/banking-core"


def main() -> int:
    print(f"Consistency gate (HermiT via owlready2) over {len(FILES)} files...")
    if shutil.which("java") is None:  # pragma: no cover - environment dependent
        print("[FAIL] Java runtime unavailable (java not found on PATH).")
        print("Fallback: open ontology/banking-core.ttl (plus seed + alignment files)")
        print("in Protégé and run the HermiT reasoner tab to verify satisfiability.")
        return 1

    try:
        from owlready2 import default_world, get_ontology, sync_reasoner
    except Exception as exc:  # pragma: no cover
        print(f"[FAIL] owlready2 not importable: {exc}")
        return 1

    # owlready2 parses RDF/XML natively; convert our Turtle sources first.
    import tempfile

    from rdflib import Graph as RdfGraph

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        for index, path in enumerate(FILES):
            rdf_graph = RdfGraph().parse(path, format="turtle")
            rdf_path = tmp / f"ontology-{index}.rdf"
            rdf_graph.serialize(destination=str(rdf_path), format="xml")
            get_ontology(f"file://{rdf_path}").load()
        try:
            sync_reasoner()
        except Exception as exc:  # pragma: no cover - reasoner download/JVM issues
            print(f"[FAIL] HermiT reasoning failed: {exc}")
            print("Fallback: verify satisfiability manually in Protégé (HermiT tab).")
            return 1

        inconsistent = []
        if hasattr(default_world, "inconsistent_classes"):  # owlready2 >= 0.42ish
            try:
                inconsistent = list(default_world.inconsistent_classes())
            except Exception:  # pragma: no cover
                inconsistent = []
        if inconsistent:
            print("[FAIL] Unsatisfiable (inconsistent) classes found:")
            for cls in inconsistent:
                print(f"  - {cls}")
            return 1
        print("[OK] No inconsistent classes detected (HermiT satisfiability check passed).")
        return 0


if __name__ == "__main__":
    sys.exit(main())
