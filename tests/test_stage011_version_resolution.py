"""Stage 011 version regressions derived from the request's exact amendment text.

The uploaded source documents themselves were not in the repository/workspace, so the
fixture explicitly records its limited provenance and reproduces their stated facts.
"""
import json
import sys
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps/api"))

from evidencerag.parser import parse
from evidencerag.research_rag import (
    ClaimExtractor, EvidenceStoreBackend, SearchBudget, SearchRequest,
    StructuredClaimEvaluator, StructuredFactAnswerGenerator, SufficiencyStatus,
    QuestionAnalyzer, _extract_attribute_facts, run_pipeline, validate_answer,
)
from evidencerag.store import EvidenceStore

FIXTURE = json.loads((ROOT / "experiments/stage011/fixtures/speech-corpus.json").read_text(encoding="utf-8"))


def make_store(tmp_path, documents=None):
    store = EvidenceStore(tmp_path / "stage011.sqlite3")
    workspace = store.workspace(store.create_workspace())
    for document in documents or FIXTURE["documents"]:
        raw = document["text"].encode("utf-8")
        store.add(workspace, document["filename"], raw, parse(raw, Path(document["filename"]).suffix),
                  document["title"], document["family"], document["version"], document["date"],
                  document.get("metadata"))
    return store, workspace


def question_for(as_of):
    dates = {"2025-10-01": "1 октября 2025 года",
             "2026-10-10": "10 октября 2026 года",
             "2026-11-03": "3 ноября 2026 года"}
    return FIXTURE["question"].replace("3 ноября 2026 года", dates[as_of])


def pipeline(store, workspace, as_of, question=None):
    return run_pipeline(SearchRequest(question or question_for(as_of), as_of=as_of),
        EvidenceStoreBackend(store, workspace), StructuredClaimEvaluator(),
        StructuredFactAnswerGenerator(), SearchBudget(max_iterations=3, max_chunks=20,
        time_budget_ms=3000, initial_top_k=5))


@pytest.mark.parametrize("expected", FIXTURE["expected"], ids=["2025-base", "2026-before-amendment", "2026-after-amendment"])
def test_full_speech_case_resolves_all_four_values_and_citations(tmp_path, expected):
    store, workspace = make_store(tmp_path)
    result = pipeline(store, workspace, expected["as_of"])
    assert result["assessment"]["status"] == "sufficient"
    facts = {claim["claim_id"]: claim["value"] for claim in result["assessment"]["supported_claims"]}
    assert facts == {"count:аудиозапись": expected["count"], "duration": expected["duration"],
                     "format": expected["format"], "deadline": expected["deadline"]}
    assert result["assessment"]["version_constraints"]["revision_catalog_complete"] is True
    answer = result["answer"]
    assert answer["verification"] == "structural_rule_and_citation_checked"
    assert len(answer["claims"]) == 4
    evidence = {item["evidence_id"]: item["text"] for item in result["selected_evidence"]}
    assert all(claim["citations"][0]["quote"] in evidence[claim["citations"][0]["id"]]
               for claim in answer["claims"])


def test_amendment_extracts_date_roles_and_old_value_provenance():
    amendment = FIXTURE["documents"][2]["text"]
    facts = _extract_attribute_facts(amendment, [("deadline", "сдача")])
    dates = [(fact["value"], fact["date_role"], fact["old_value"], fact["target_clause"])
             for fact in facts]
    assert ("2026-11-18", "old_deadline", None, "4") in dates
    assert ("2026-11-30", "new_deadline", "2026-11-18", "4") in dates
    assert not any(value == "2026-09-01" for value, *_ in dates)
    format_fact = _extract_attribute_facts(amendment, [("format", "файл")])[0]
    assert (format_fact["old_value"], format_fact["value"], format_fact["target_clause"]) == ("WAV", "FLAC", "3")


def test_separate_group_amendment_links_to_unique_edition_by_clause_and_old_value(tmp_path):
    store, workspace = make_store(tmp_path)
    with store.connect() as db:
        links = db.execute("SELECT amendment_document,target_document,relation FROM revision_links").fetchall()
        docs = {row["id"]: row["version"] for row in db.execute("SELECT id,version FROM documents")}
    link = next(row for row in links if docs[row["target_document"]] == "2026")
    assert link["relation"] == "explicit_edition_and_clause_and_old_value"


def test_foreign_named_regulation_is_not_linked_by_shared_date_or_old_value(tmp_path):
    amendment = dict(FIXTURE["documents"][2])
    amendment.update(id="foreign-amendment", title="Поправка к другому регламенту",
        family="foreign", date="2026-10-20",
        text="Поправка к регламенту «Курс Чужой». В пункте 3 регламента 2026 года формат изменён: вместо WAV необходимо предоставлять MP3."
             " В пункте 4 регламента 2026 года срок перенесён: вместо 18 ноября 2026 года комплект принимается до 30 ноября 2026 года включительно.")
    docs = FIXTURE["documents"][:2] + [amendment]
    store, workspace = make_store(tmp_path, docs)
    with store.connect() as db:
        assert db.execute("SELECT count(*) FROM revision_links WHERE amendment_document=?", (amendment["id"],)).fetchone()[0] == 0
    result = pipeline(store, workspace, "2026-11-03")
    facts = {claim["claim_id"]: claim["value"] for claim in result["assessment"]["supported_claims"]}
    assert facts["format"] == "WAV"
    assert facts["deadline"] == "2026-11-18"


def test_ambiguous_equal_targets_are_reported_not_applied(tmp_path):
    first, second = [dict(FIXTURE["documents"][1]) for _ in range(2)]
    first.update(id="base-a", title="Регламент A итогового зачёта», speech", family="family-a")
    second.update(id="base-b", title="Регламент B итогового зачёта», speech", family="family-b")
    amendment = dict(FIXTURE["documents"][2], id="ambiguous-amendment", family="amendments")
    # This deliberately omits a unique title and identifies two 2026 targets equally.
    docs = [FIXTURE["documents"][0], first, second, amendment]
    store, workspace = make_store(tmp_path, docs)
    result = pipeline(store, workspace, "2026-11-03")
    assert result["assessment"]["status"] == "applicability_uncertain"
    assert any("несколько" in gap["description"].casefold() for gap in result["assessment"]["missing_information"])
    assert not result["answer"]["claims"]


def test_unknown_amendment_date_does_not_change_value_or_claim_currentness(tmp_path):
    amendment = dict(FIXTURE["documents"][2], date="", id="undated-amendment")
    store, workspace = make_store(tmp_path, FIXTURE["documents"][:2] + [amendment])
    result = pipeline(store, workspace, "2026-11-03")
    assert result["assessment"]["status"] == "applicability_uncertain"
    values = {claim["claim_id"]: claim["value"] for claim in result["assessment"]["supported_claims"]}
    assert values.get("format") != "FLAC"
    assert values.get("deadline") != "2026-11-30"


def test_sufficiency_requires_a_complete_revision_catalog():
    hit = {"evidence_id": "one", "text": "Требуется 5 файлов.", "date": "2026-01-01",
           "family": "f", "version": "1", "title": "Правила", "document": "d"}
    result = StructuredClaimEvaluator().evaluate(SearchRequest("Сколько файлов требуется?"), [hit], [])
    assert result.status is not SufficiencyStatus.SUFFICIENT
    assert result.version_constraints["revision_catalog_checked"] is False
    assert any("поправ" in gap.description.casefold() for gap in result.missing_information)


def test_repeated_changes_chain_from_the_previous_effective_value(tmp_path):
    first = dict(FIXTURE["documents"][2], id="amendment-a", family="amend-a", version="1", date="2026-10-01",
                 text="В пункте 3 регламента 2026 года формат изменён: вместо WAV необходимо предоставлять FLAC.")
    second = dict(FIXTURE["documents"][2], id="amendment-b", family="amend-b", version="2", date="2026-10-20",
                  text="В пункте 3 регламента 2026 года формат изменён: вместо FLAC необходимо предоставлять OGG.")
    store, workspace = make_store(tmp_path, FIXTURE["documents"][:2] + [first, second])
    result = pipeline(store, workspace, "2026-11-03")
    facts = {claim["claim_id"]: claim["value"] for claim in result["assessment"]["supported_claims"]}
    assert result["assessment"]["status"] == "sufficient"
    assert facts["format"] == "OGG"
    assert len(result["assessment"]["version_constraints"]["resolution"]["format"]["applied_operations"]) == 2
