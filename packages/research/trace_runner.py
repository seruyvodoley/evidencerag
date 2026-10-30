"""Run one auditable, author-rule diagnostic trace without a model or web service."""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import sqlite3
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from evidencerag.parser import parse
from evidencerag.research_rag import (
    EvidenceStoreBackend,
    FormalRequirement,
    FormalRule,
    FormalRuleEvaluator,
    LiteralExtractAnswerGenerator,
    SearchBudget,
    SearchRequest,
    run_pipeline,
    save_trace,
)
from evidencerag.store import EvidenceStore

ROOT = Path(__file__).resolve().parents[2]
QUESTION = "Какой срок возврата после изменений?"
REQUIRED_QUOTE = "Срок возврата: 30 дней"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(output: Path) -> dict:
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    catalog_path = ROOT / "datasets/demo/catalog.json"
    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    corpus = next(item for item in catalog if item["id"] == "service")
    source_paths = [ROOT / "apps/api/evidencerag/research_rag.py",
                    ROOT / "apps/api/evidencerag/retrieval.py",
                    ROOT / "apps/api/evidencerag/parser.py",
                    ROOT / "apps/api/evidencerag/store.py", Path(__file__).resolve(), catalog_path]
    source_paths.append(ROOT / "datasets/demo/LICENSE")
    source_paths.extend(ROOT / "datasets/demo" / doc["filename"] for doc in corpus["documents"])
    source_hashes = {str(path.relative_to(ROOT)): digest(path) for path in source_paths}
    commit_result = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT,
                                   capture_output=True, text=True, check=False)
    status_result = subprocess.run(["git", "status", "--porcelain", "--untracked-files=all"], cwd=ROOT,
                                   capture_output=True, text=True, check=False)

    with tempfile.TemporaryDirectory(prefix="evidencerag-trace-") as temp:
        store = EvidenceStore(Path(temp) / "trace.sqlite3")
        token = store.create_workspace()
        workspace = store.workspace(token)
        for document in corpus["documents"]:
            path = ROOT / "datasets/demo" / document["filename"]
            raw = path.read_bytes()
            store.add(workspace, document["filename"], raw, parse(raw, ".md"),
                      document["title"], document["family"], document["version"], document["date"])
        rule = FormalRule(QUESTION, (FormalRequirement(
            claim_id="return-term-2025", claim_text=REQUIRED_QUOTE, exact_quote=REQUIRED_QUOTE,
            search_query="редакция 2025 срок возврата 30 дней", allowed_versions=("2025",)),))
        trace = run_pipeline(
            SearchRequest(QUESTION, family="service"), EvidenceStoreBackend(store, workspace),
            FormalRuleEvaluator((rule,)), LiteralExtractAnswerGenerator(),
            SearchBudget(max_iterations=3, max_chunks=10, time_budget_ms=500, initial_top_k=1))

    save_trace(output / "trace.json", trace)
    config = {
        "experiment": "single_question_controller_diagnostic",
        "dataset_kind": "authored_synthetic_fixture",
        "split": "diagnostic_only_no_statistical_split",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "git_commit": commit_result.stdout.strip() or None,
        "git_dirty_before_run": bool(status_result.stdout.strip()),
        "source_hashes": source_hashes,
        "environment": {"python": sys.version, "platform": platform.platform(),
                        "sqlite": sqlite3.sqlite_version, "processor": platform.processor()},
        "retrieval": "SQLite FTS5 BM25 through EvidenceStoreBackend; query terms normalized by current project code",
        "indexing": {"parser": "apps/api/evidencerag/parser.py, Markdown extraction",
                     "chunk_size_chars": 1100, "overlap_chars": 0,
                     "normalization": "apps/api/evidencerag/retrieval.py::terms (Russian morphology)"},
        "sufficiency_evaluator": "authored exact-quote rule; not semantic NLI or LLM",
        "answer_generator": "literal extract only; no paraphrase or free-form generation",
        "external_model": None,
        "seed": None,
        "seed_use": "No random sampling or randomized model operation is used.",
        "budget": {"max_iterations": 3, "max_chunks": 10, "time_budget_ms": 500, "initial_top_k": 1},
        "question": QUESTION,
        "answer_quality_metrics": None,
        "statistical_inference": None,
    }
    (output / "config.json").write_text(json.dumps(config, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    new_chunks = sum(step["new_evidence_chunk_count"] for step in trace["trace"])
    new_documents = sum(step["new_document_count"] for step in trace["trace"])
    newly_supported_claims = sum(step["new_evidence_claim_count"] for step in trace["trace"])
    report = f"""# Diagnostic trace: stage 006

One already executed diagnostic run, not a benchmark. Corpus: two author-written synthetic editions in `datasets/demo/service-*`. It tests the actual SQLite/FTS5 adapter, explicit authored exact-quote sufficiency rule, version-targeted follow-up retrieval, and literal-citation validation.

- Search calls: {len(trace['trace'])}; stop reason: `{trace['termination']}`.
- New evidence chunks returned across calls: {new_chunks}; distinct source revisions: {new_documents}.
- Newly supported formal claims: {newly_supported_claims}.
- Answer: `{trace['answer']['status']}`, exact quote only; verification `{trace['answer']['verification']}`.
- Semantic evaluation, free-form answer generation, correctness/faithfulness metrics: not run (`null` / unavailable).
- No external API was called. The output is not evidence of real-world answer quality or method superiority.

Reproduce with:

```sh
PYTHONPATH=apps/api .venv/bin/python -m packages.research.trace_runner --output experiments/NEW_OUTPUT_DIRECTORY
```

The command requires a new output path and refuses to overwrite one. See `config.json` for input and source hashes; `trace.json` contains each action, version filter, assessment, returned IDs, new documents/chunks/claims and the final citation-checked extract.
"""
    (output / "REPORT.md").write_text(report, encoding="utf-8")
    return trace


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    result = run(args.output)
    print(json.dumps({"output": str(args.output), "termination": result["termination"],
                      "iterations": len(result["trace"]), "answer_status": result["answer"]["status"]},
                     ensure_ascii=False))


if __name__ == "__main__":
    main()
