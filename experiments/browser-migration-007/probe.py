"""Deterministic subset of the real Python core used for Pyodide parity checks."""
from __future__ import annotations

import json
import sqlite3
import tempfile
from pathlib import Path

from evidencerag.parser import parse
from evidencerag.retrieval import (
    adaptive_k_decision,
    analyze_field_changes,
    retrieve,
    stable_evidence_id,
    terms,
)
from evidencerag.research_rag import (
    FormalRequirement,
    FormalRule,
    FormalRuleEvaluator,
    LiteralExtractAnswerGenerator,
    SearchBudget,
    SearchRequest,
    run_pipeline,
)
from evidencerag.store import EvidenceStore


HERE = Path(__file__).resolve().parent


class OneEvidenceBackend:
    def __init__(self, evidence: dict):
        self.evidence = evidence

    def search(self, query, limit, family, version, as_of, deadline):
        return [self.evidence][:limit]


def _without_timings(value):
    if isinstance(value, dict):
        return {k: _without_timings(v) for k, v in value.items() if k != "elapsed_ms"}
    if isinstance(value, list):
        return [_without_timings(v) for v in value]
    return value


def probe() -> dict:
    docx = (HERE / "fixtures" / "table-heading.docx").read_bytes()
    pdf = (HERE / "fixtures" / "two-page.pdf").read_bytes()
    scanned = (HERE / "fixtures" / "scanned.pdf").read_bytes()
    hits = [
        {
            "id": "chunk-a",
            "document": "document-a",
            "digest": "a" * 64,
            "family": "contract",
            "version": version,
            "date": date,
            "locator": "Условия",
            "page": 2,
            "offset": 0,
            "text": f"Срок возврата: {days} дней",
            "score": score,
        }
        for version, date, days, score in (
            ("1.0", "2024-01-01", 30, -1.0),
            ("2.0", "2025-01-01", 14, -0.8),
        )
    ]
    candidates = [
        {"id": "a", "score": -1.0},
        {"id": "b", "score": -0.8},
        {"id": "c", "score": -0.1},
    ]
    selected, cutoff = adaptive_k_decision(candidates, 3)

    requirement = FormalRequirement(
        claim_id="return-period",
        claim_text="Срок возврата: 14 дней",
        exact_quote="Срок возврата: 14 дней",
        search_query="Срок возврата",
        allowed_versions=("2.0",),
    )
    evidence = {
        "evidence_id": "ev-contract-v2",
        "source_revision_id": "doc-contract-v2",
        "text": "Условия\nСрок возврата: 14 дней",
        "family": "contract",
        "version": "2.0",
        "date": "2025-01-01",
        "locator": "Условия",
        "page": 2,
    }
    controller = run_pipeline(
        SearchRequest(question="Какой срок возврата?", family="contract", version="2.0"),
        OneEvidenceBackend(evidence),
        FormalRuleEvaluator((FormalRule("Какой срок возврата?", (requirement,)),)),
        LiteralExtractAnswerGenerator(),
        SearchBudget(max_iterations=3, max_chunks=8, time_budget_ms=1000, initial_top_k=2),
    )
    with tempfile.TemporaryDirectory(dir=HERE) as temp_dir:
        evidence_store = EvidenceStore(Path(temp_dir) / "evidence.sqlite3")
        workspace = evidence_store.workspace(evidence_store.create_workspace())
        for version, date, days, _score in (
            ("1.0", "2024-01-01", 30, -1.0),
            ("2.0", "2025-01-01", 14, -0.8),
        ):
            text = f"# Договор\n\nСрок возврата: {days} дней"
            evidence_store.add(
                workspace,
                f"contract-{version}.md",
                text.encode(),
                parse(text.encode(), ".md"),
                "Договор",
                "contract",
                version,
                date,
            )
        retrieval_result = retrieve(
            evidence_store,
            workspace,
            "Срок возврата",
            strategy="versioned",
            max_iterations=3,
            max_chunks=12,
            time_budget_ms=1000,
        )
        retrieval_summary = {
            "status": retrieval_result["status"],
            "termination": retrieval_result["termination"],
            "gaps": retrieval_result["gaps"],
            "hits": [
                {
                    "evidence_id": hit["evidence_id"],
                    "text": hit["text"],
                    "score": hit["score"],
                    "version": hit["version"],
                    "date": hit["date"],
                }
                for hit in retrieval_result["hits"]
            ],
            "version_differences": [
                {
                    "field": signal["field"],
                    "kind": signal["kind"],
                    "values": [source["value"] for source in signal["sources"]],
                }
                for signal in retrieval_result["version_differences"]
            ],
            "trace": [
                {
                    key: step[key]
                    for key in ("iteration", "query", "selected_chunks", "gaps", "action", "reason")
                }
                for step in retrieval_result["trace"]
            ],
        }
    return {
        "sqlite_version": sqlite3.sqlite_version,
        "terms": terms("Договоры, договорами и услугами"),
        "parser": {
            "markdown": parse("# Договор\n\nСрок возврата: 30 дней".encode(), ".md"),
            "docx": parse(docx, ".docx"),
            "pdf": parse(pdf, ".pdf"),
            "scanned_pdf": parse(scanned, ".pdf"),
        },
        "stable_evidence_ids": [stable_evidence_id(h) for h in hits],
        "adaptive_k": {"selected_ids": [h["id"] for h in selected], "decision": cutoff},
        "version_signals": analyze_field_changes(hits, "Какой срок возврата?"),
        "research_controller": _without_timings(controller),
        "fts_retrieval": retrieval_summary,
    }


def store_probe() -> dict:
    connection = sqlite3.connect(":memory:")
    connection.execute("CREATE VIRTUAL TABLE test_fts USING fts5(text)")
    connection.execute("INSERT INTO test_fts(text) VALUES ('локальный документ')")
    fts_match = connection.execute(
        "SELECT count(*) FROM test_fts WHERE test_fts MATCH 'документ'"
    ).fetchone()[0]
    try:
        connection.execute("INSERT INTO test_fts(test_fts, rank) VALUES('secure-delete', 1)")
        secure_delete = True
    except sqlite3.OperationalError:
        secure_delete = False
    connection.close()
    try:
        EvidenceStore(HERE / "pyodide-store-probe.sqlite3")
    except Exception as error:
        return {
            "status": "blocked",
            "error_type": type(error).__name__,
            "message": str(error),
            "sqlite_version": sqlite3.sqlite_version,
            "fts5_match_works": fts_match == 1,
            "fts5_secure_delete_works": secure_delete,
        }
    return {
        "status": "available",
        "sqlite_version": sqlite3.sqlite_version,
        "fts5_match_works": fts_match == 1,
        "fts5_secure_delete_works": secure_delete,
    }


if __name__ == "__main__":
    print(json.dumps(probe(), ensure_ascii=False, sort_keys=True, separators=(",", ":")))
