"""Knowledge-base loading, RDF helpers and concept-detail assembly.

The authoritative dataset is a set of read-only Turtle files under
``ontology/``; ``KnowledgeBase`` loads them into one in-memory rdflib graph.
Nothing in this module ever writes back to the source files.
"""
from __future__ import annotations

from pathlib import Path
from typing import Iterable, Optional

from rdflib import Graph, Literal, Namespace, URIRef
from rdflib.namespace import OWL, RDF, RDFS, SKOS, XSD

BC = Namespace("https://ontology.example/banking-core#")
EX = Namespace("https://ontology.example/seed#")

DEFAULT_ONTOLOGY_FILES = [
    Path("ontology/banking-core.ttl"),
    Path("ontology/seed-corpora.ttl"),
    Path("ontology/fibo-alignment.ttl"),
]

# Top-level categories of the tree browser (design.md D6, specs/concept-browser).
ROOT_CATEGORIES = [BC.Product, BC.Account, BC.Party]

# Predicates that are never exposed as "attributes" or "relationships".
_SKIP_ATTRIBUTE_PREDICATES = {
    RDFS.label,
    SKOS.definition,
    SKOS.altLabel,
    SKOS.editorialNote,
    RDF.type,
}
_SKIP_RELATIONSHIP_PREDICATES = {
    RDFS.label,
    SKOS.definition,
    SKOS.altLabel,
    SKOS.editorialNote,
    RDF.type,
    RDFS.subClassOf,
    BC.alignedToFibo,
}

# Annotation predicates that carry prose (not data attributes).
_LITERAL_PROSE_PREDICATES = {SKOS.definition, SKOS.editorialNote}


def normalize(term: str) -> str:
    """Normalize a search term: trim and lowercase Latin characters."""
    return term.strip().lower()


class KnowledgeBase:
    """In-memory RDF knowledge base over the ontology Turtle files."""

    def __init__(self, files: Optional[Iterable[Path | str]] = None) -> None:
        source_files = [Path(f) for f in (files or DEFAULT_ONTOLOGY_FILES)]
        self.graph = Graph()
        self.graph.bind("bc", BC)
        self.graph.bind("ex", EX)
        self.graph.bind("skos", SKOS)
        self.graph.bind("rdf", RDF)
        self.graph.bind("rdfs", RDFS)
        self.graph.bind("owl", OWL)
        self.graph.bind("xsd", XSD)
        for path in source_files:
            self.graph.parse(path, format="turtle")

    # ---------------------------------------------------------------- labels

    def labels(self, uri: URIRef) -> dict[str, str]:
        """Return first Chinese/English rdfs:label for a resource."""
        zh = en = ""
        for label in self.graph.objects(uri, RDFS.label):
            if isinstance(label, Literal):
                lang = label.language
                if lang == "zh" and not zh:
                    zh = str(label)
                elif lang == "en" and not en:
                    en = str(label)
        return {"zh": zh, "en": en}

    def synonyms(self, uri: URIRef) -> list[str]:
        return [str(a) for a in self.graph.objects(uri, SKOS.altLabel)]

    def definition(self, uri: URIRef) -> str:
        for lang in ("zh", "en", None):
            for d in self.graph.objects(uri, SKOS.definition):
                if isinstance(d, Literal) and (lang is None or d.language == lang):
                    return str(d)
        return ""

    def is_class(self, uri: URIRef) -> bool:
        types = set(self.graph.objects(uri, RDF.type))
        if OWL.Class in types or RDFS.Class in types:
            return True
        return any(self.graph.objects(uri, RDFS.subClassOf))

    def direct_superclass(self, cls: URIRef) -> Optional[URIRef]:
        for parent in self.graph.objects(cls, RDFS.subClassOf):
            if isinstance(parent, URIRef) and parent != OWL.Thing:
                return parent
        return None

    def direct_subclasses(self, cls: URIRef) -> list[URIRef]:
        return sorted(
            (
                s
                for s in self.graph.subjects(RDFS.subClassOf, cls)
                if isinstance(s, URIRef)
            ),
            key=lambda s: self.labels(s)["zh"] or self.labels(s)["en"] or str(s),
        )

    def descendants(self, root: URIRef, include_self: bool = True) -> set[URIRef]:
        seen: set[URIRef] = set()
        stack = [root] if include_self else self.direct_subclasses(root)
        while stack:
            node = stack.pop()
            if node in seen:
                continue
            seen.add(node)
            stack.extend(self.direct_subclasses(node))
        return seen

    # ------------------------------------------------------------ node detail

    def _short_label(self, uri: URIRef, fallback: Optional[str] = None) -> str:
        labels = self.labels(uri)
        return labels["zh"] or labels["en"] or (fallback or str(uri))

    def attributes(self, uri: URIRef) -> list[dict]:
        attrs = []
        for pred, obj in self.graph.predicate_objects(uri):
            if pred in _SKIP_ATTRIBUTE_PREDICATES or pred in _LITERAL_PROSE_PREDICATES:
                continue
            if not isinstance(obj, Literal):
                continue
            datatype = (
                obj.datatype.split("#")[-1] if obj.datatype else (obj.language or "text")
            )
            attrs.append(
                {
                    "property": str(pred),
                    "property_label": self._short_label(pred, fallback=str(pred).split("#")[-1]),
                    "value": str(obj),
                    "datatype": datatype,
                }
            )
        return attrs

    def relationships(self, uri: URIRef) -> list[dict]:
        rels = []
        for pred, obj in self.graph.predicate_objects(uri):
            if pred in _SKIP_RELATIONSHIP_PREDICATES:
                continue
            if not isinstance(obj, URIRef):
                continue
            rels.append(
                {
                    "property": str(pred),
                    "property_label": self._short_label(pred, fallback=str(pred).split("#")[-1]),
                    "value": str(obj),
                    "value_label": self._short_label(obj),
                }
            )
        return rels

    def concept_detail(self, uri: URIRef) -> Optional[dict]:
        has_any = any(self.graph.predicate_objects(uri))
        if not has_any:
            return None
        labels = self.labels(uri)
        is_class = self.is_class(uri)
        detail: dict = {
            "id": str(uri),
            "kind": "class" if is_class else "individual",
            "labels": labels,
            "label_zh": labels["zh"],
            "label_en": labels["en"],
            "synonyms": self.synonyms(uri),
            "definition": self.definition(uri),
            "attributes": self.attributes(uri),
            "relationships": self.relationships(uri),
        }
        if is_class:
            parent = self.direct_superclass(uri)
            detail["superclass"] = (
                {"id": str(parent), "label": self._short_label(parent)} if parent else None
            )
            detail["subclasses"] = [
                {"id": str(sub), "label": self._short_label(sub)}
                for sub in self.direct_subclasses(uri)
            ]
            detail["types"] = []
        else:
            detail["superclass"] = None
            detail["subclasses"] = []
            detail["types"] = [
                {"id": str(t), "label": self._short_label(t)}
                for t in sorted(self.graph.objects(uri, RDF.type), key=str)
                if isinstance(t, URIRef)
            ]
        return detail

    def candidate_concepts(self) -> list[URIRef]:
        """Labelled classes and individuals in the bc:/ex: namespaces.

        Properties (owl:ObjectProperty / DatatypeProperty / AnnotationProperty
        and owl:Ontology declarations) are intentionally excluded.
        """
        out = []
        for s in self.graph.subjects(RDFS.label, None):
            if not isinstance(s, URIRef):
                continue
            if not (str(s).startswith(str(BC)) or str(s).startswith(str(EX))):
                continue
            if self.is_class(s):
                out.append(s)
                continue
            types = {t for t in self.graph.objects(s, RDF.type) if isinstance(t, URIRef)}
            if any(str(t).startswith(str(BC)) for t in types):
                out.append(s)
        return sorted(set(out), key=lambda s: self.labels(s)["zh"] or str(s))

    def triple_count(self) -> int:
        return len(self.graph)

    def tree(self) -> list[dict]:
        def build(node: URIRef) -> dict:
            children = [build(c) for c in self.direct_subclasses(node)]
            return {
                "id": str(node),
                "label_zh": self.labels(node)["zh"],
                "label_en": self.labels(node)["en"],
                "children": children,
            }

        return [build(root) for root in ROOT_CATEGORIES]

    def resolve(self, identifier: str) -> Optional[URIRef]:
        """Resolve a local name (Deposit), prefixed name (bc:Deposit) or IRI."""
        raw = identifier.strip()
        if raw.startswith("http://") or raw.startswith("https://"):
            uri = URIRef(raw)
            return uri if any(self.graph.predicate_objects(uri)) else None
        if ":" in raw:
            prefix, _, name = raw.partition(":")
            namespace = {"bc": BC, "ex": EX}.get(prefix)
            if namespace is None:
                return None
            uri = namespace[name]
            return uri if any(self.graph.predicate_objects(uri)) else None
        for namespace in (BC, EX):
            uri = namespace[raw]
            if any(self.graph.predicate_objects(uri)):
                return uri
        return None


def main(argv: Optional[list[str]] = None) -> int:
    """CLI entry: load the corpus and print a dataset summary.

    Optional positional arg: an extra directory of *.ttl files (the git-ignored
    ``internal/`` import area). Usage:  python -m banking_kb.kb [internal-dir]
    """
    import sys

    args = list(sys.argv[1:] if argv is None else argv)
    files: list[Path] = list(DEFAULT_ONTOLOGY_FILES)
    if args:
        internal_dir = Path(args[0])
        if not internal_dir.is_dir():
            print(f"[error] internal data directory not found: {internal_dir}")
            return 1
        files += sorted(internal_dir.glob("*.ttl"))
    kb = KnowledgeBase(files)
    classes = sum(1 for c in kb.candidate_concepts() if kb.is_class(c))
    individuals = sum(1 for c in kb.candidate_concepts() if not kb.is_class(c))
    print(f"Loaded {len(files)} file(s): {kb.triple_count()} triples, "
          f"{classes} classes, {individuals} individuals.")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
