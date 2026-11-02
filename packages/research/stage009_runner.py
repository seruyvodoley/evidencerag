"""Execute the authored stage-009 regression case through real SQLite/FTS retrieval."""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import sqlite3
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from evidencerag.parser import parse
from evidencerag.research_rag import (
    EvidenceStoreBackend, SearchBudget, SearchRequest, StructuredClaimEvaluator,
    StructuredFactAnswerGenerator, run_pipeline, save_trace,
)
from evidencerag.store import EvidenceStore

ROOT = Path(__file__).resolve().parents[2]
FIXTURE_PATH = ROOT / "experiments/stage009/fixtures/ifiyak-known-case.json"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(output: Path) -> dict:
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    fixture = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    with tempfile.TemporaryDirectory(prefix="evidencerag-stage009-") as temp:
        store = EvidenceStore(Path(temp) / "evidence.sqlite3")
        workspace = store.workspace(store.create_workspace())
        for document in fixture["documents"]:
            raw = document["text"].encode("utf-8")
            store.add(workspace, document["filename"], raw, parse(raw, ".txt"),
                      document["title"], document["family"], document["version"], document["date"])
        request = SearchRequest(fixture["question"], family=fixture["family"], as_of=fixture["as_of"])
        budget = SearchBudget(max_iterations=3, max_chunks=20, time_budget_ms=2000, initial_top_k=5)
        result = run_pipeline(request, EvidenceStoreBackend(store, workspace),
                              StructuredClaimEvaluator(), StructuredFactAnswerGenerator(), budget)

    save_trace(output / "trace.json", result)
    config = {
        "experiment": "stage009_known_case_regression",
        "dataset_kind": fixture["kind"],
        "purpose": fixture["purpose"],
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "git_commit_before_run": __import__("subprocess").run(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=False
        ).stdout.strip() or None,
        "source_sha256": {str(path.relative_to(ROOT)): digest(path) for path in [
            FIXTURE_PATH, ROOT / "apps/api/evidencerag/research_rag.py",
            ROOT / "apps/api/evidencerag/retrieval.py", ROOT / "apps/api/evidencerag/store.py",
            Path(__file__).resolve()]},
        "environment": {"python": sys.version, "platform": platform.platform(),
                        "sqlite": sqlite3.sqlite_version},
        "retrieval": "workspace-scoped SQLite FTS5; Russian morphological query terms",
        "evaluator": "structured_attribute_date_rules_v1; transparent regex/lemma rules, no NLI",
        "answer_generator": "structured_fact_composer_v1; mechanically linked citation quotes",
        "external_model": None,
        "request": {"question": fixture["question"], "family": fixture["family"], "as_of": fixture["as_of"]},
        "budget": {"max_iterations": budget.max_iterations, "max_chunks": budget.max_chunks,
                   "time_budget_ms": budget.time_budget_ms, "initial_top_k": budget.initial_top_k},
        "expected_values": fixture["expected"],
        "scientific_inference": None,
        "metrics_not_measured": ["semantic entailment", "real-world accuracy", "S2G-RAG comparison", "human adjudication"],
    }
    (output / "config.json").write_text(json.dumps(config, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    values = {claim["attribute"]: claim["value"] for claim in result["claims"]}
    report = {
        "experiment": config["experiment"], "dataset_kind": config["dataset_kind"],
        "purpose": config["purpose"], "status": result["assessment"]["status"],
        "answer_status": result["answer"]["status"], "answer": result["answer"].get("text"),
        "values": values, "expected": fixture["expected"],
        "values_match_fixture": values == fixture["expected"],
        "citation_count": sum(len(claim.get("citations", [])) for claim in result["answer"].get("claims", [])),
        "iterations": len(result["trace"]), "termination": result["termination"],
        "selected_evidence_count": len(result["selected_evidence"]),
        "elapsed_ms": result["elapsed_ms"],
        "semantic_claim": "No semantic entailment or scientific effectiveness claim is made.",
    }
    (output / "result.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (output / "REPORT.md").write_text(
        "# Stage 009 known-case regression\n\n" +
        f"- Corpus: authored synthetic debugging fixture; not an independent efficacy set.\n"+
        f"- Assessment: `{report['status']}`; answer: `{report['answer_status']}`.\n"+
        f"- Extracted values match fixture: `{report['values_match_fixture']}`.\n"+
        f"- Search iterations: {report['iterations']}; evidence chunks: {report['selected_evidence_count']}; runtime: {report['elapsed_ms']} ms.\n"+
        f"- Every answer claim has a literal source chunk and mechanically re-extracted attribute/value.\n"+
        "- This is a functional regression check, not a semantic faithfulness or method superiority result.\n\n"
        "Reproduce with a fresh output directory:\n\n"
        "```sh\nPYTHONPATH=apps/api .venv/bin/python -m packages.research.stage009_runner --output experiments/stage009/NEW_RUN\n```\n",
        encoding="utf-8")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    result = run(args.output)
    print(json.dumps({"output": str(args.output), "status": result["assessment"]["status"],
                      "answer_status": result["answer"]["status"], "iterations": len(result["trace"]),
                      "elapsed_ms": result["elapsed_ms"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
