"""Stage 009 regression fixtures; authored cases are diagnostics, not efficacy evidence."""

import json
from pathlib import Path

from evidencerag.research_rag import (
    SearchRequest, StructuredClaimEvaluator, StructuredFactAnswerGenerator,
    SufficiencyStatus, validate_answer,
)


FIXTURE = json.loads((Path(__file__).resolve().parents[1] / "experiments/stage009/fixtures/ifiyak-known-case.json").read_text(encoding="utf-8"))
FAMILY = FIXTURE["family"]
QUESTION = FIXTURE["question"]


def source(ident, text, date, family=FAMILY, version="2026", title="Практикум Причастный оборот"):
    return {"evidence_id": ident, "text": text, "date": date, "family": family,
            "version": version, "title": title, "source_revision_id": "doc-" + ident}


def corpus():
    return [source(ident, doc["text"], doc["date"], family=doc["family"], version=doc["version"], title=doc["title"])
            for ident, doc in zip(("old", "new", "amend"), FIXTURE["documents"])]


def evaluate(as_of, hits=None, question=QUESTION, family=None):
    request = SearchRequest(question, family=family, as_of=as_of)
    return StructuredClaimEvaluator().evaluate(request, hits if hits is not None else corpus(), [])


def by_attribute(assessment):
    return {claim.attribute: claim for claim in assessment.supported_claims}


def test_a_known_ifiyak_case_builds_three_cited_facts_and_applies_partial_amendment():
    hits = corpus()
    request = SearchRequest(QUESTION, as_of="2026-10-31")
    assessment = StructuredClaimEvaluator().evaluate(request, hits, [])
    assert assessment.status is SufficiencyStatus.SUFFICIENT
    facts = by_attribute(assessment)
    assert facts["count:предложение"].value == "8"
    assert facts["duration"].value == "25"
    assert facts["submission_mode"].value == "в электронном виде"
    answer = validate_answer(StructuredFactAnswerGenerator().generate(request, hits, assessment), hits)
    assert "25 минут" in answer["text"]
    assert {claim["citations"][0]["id"] for claim in answer["claims"]} == {"new", "amend"}


def test_b_before_amendment_keeps_base_duration():
    result = evaluate("2026-10-01")
    assert result.status is SufficiencyStatus.SUFFICIENT
    assert by_attribute(result)["duration"].value == "20"


def test_c_old_date_selects_old_edition():
    result = evaluate("2025-10-01")
    facts = by_attribute(result)
    assert result.status is SufficiencyStatus.SUFFICIENT
    assert (facts["count:предложение"].value, facts["duration"].value,
            facts["submission_mode"].value) == ("6", "15", "на бумаге")


def test_d_missing_attribute_is_reported_by_name():
    result = evaluate("2026-10-31", question=QUESTION + " Сколько абзацев требуется?")
    assert result.status is SufficiencyStatus.INSUFFICIENT
    assert any("count:абзац" in gap.description for gap in result.missing_information)


def test_e_competing_applicable_amendments_are_a_conflict():
    hits = corpus() + [source("amend2", "С 15 октября 2026 года в редакции от 1 сентября 2026 года время изменено: вместо 20 минут устанавливается 30 минут.", "2026-10-15", family=FAMILY + "-Поправки-2")]
    result = evaluate("2026-10-31", hits)
    assert result.status is SufficiencyStatus.CONFLICTING
    assert any("duration" in item.description for item in result.conflicting_claims)


def test_f_paraphrased_submission_mode_is_extractable_without_claiming_nli():
    hits = [source("mode", "Итоговая работа содержит 8 предложений. На выполнение отводится 20 минут. Работа сдаётся в электронном виде.", "2026-09-01"),
            source("mode-paraphrase", "Работа принимается посредством цифровой системы сдачи.", "2026-09-01")]
    result = evaluate("2026-09-30", hits)
    assert result.status is SufficiencyStatus.SUFFICIENT
    assert by_attribute(result)["submission_mode"].value in {"в электронном виде", "посредством цифровой системы сдачи"}


def test_g_partial_amendment_preserves_other_base_facts():
    facts = by_attribute(evaluate("2026-10-31"))
    assert facts["count:предложение"].evidence_ids == ("new",)
    assert facts["submission_mode"].evidence_ids == ("new",)
    assert facts["duration"].evidence_ids == ("amend",)


def test_h_independent_technical_domain_uses_labelled_attribute():
    question = "Какова температура оборудования?"
    hits = [source("old-temp", "Температура: 70 °C", "2024-01-01", family="Терморегламент", version="1"),
            source("new-temp", "Температура: 85 °C", "2025-01-01", family="Терморегламент", version="2")]
    result = evaluate("2025-06-01", hits, question, "Терморегламент")
    assert result.status is SufficiencyStatus.SUFFICIENT
    assert by_attribute(result)["field:температура"].value == "85 °C"


def test_i_lexical_lookalike_does_not_become_fact():
    hits = [source("lookalike", "Документ обсуждает итоговую работу, предложения и минуты, но не устанавливает их число или время.", "2026-09-01")]
    result = evaluate("2026-09-30", hits)
    assert result.status is SufficiencyStatus.INSUFFICIENT
    assert not result.supported_claims


def test_j_unknown_applicability_is_not_returned_as_current():
    hits = [source("undated", "Итоговая работа содержит 8 предложений. На выполнение отводится 20 минут. Работа сдаётся в электронном виде.", "")]
    result = evaluate("2026-10-31", hits)
    assert result.status is SufficiencyStatus.INSUFFICIENT
    assert not result.supported_claims
    assert all(gap.kind.value == "version" for gap in result.missing_information)


def test_actual_fts_backend_discovers_cross_family_amendment_and_stops_when_complete(tmp_path):
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "apps/api"))
    from evidencerag.parser import parse
    from evidencerag.research_rag import (EvidenceStoreBackend, SearchBudget,
        StructuredFactAnswerGenerator, run_pipeline)
    from evidencerag.store import EvidenceStore

    store = EvidenceStore(tmp_path / "stage009.sqlite3")
    workspace = store.workspace(store.create_workspace())
    for index, document in enumerate(corpus()):
        content = document["text"].encode("utf-8")
        store.add(workspace, f"doc-{index}.txt", content, parse(content, ".txt"),
                  f"Документ {index}", document["family"], document["version"], document["date"])
    request = SearchRequest(QUESTION, family=FAMILY, as_of="2026-10-31")
    result = run_pipeline(request, EvidenceStoreBackend(store, workspace), StructuredClaimEvaluator(),
        StructuredFactAnswerGenerator(), SearchBudget(max_iterations=3, max_chunks=12,
        time_budget_ms=3000, initial_top_k=12))
    assert result["assessment"]["status"] == "sufficient"
    assert result["answer"]["status"] == "answered"
    assert "25 минут" in result["answer"]["text"]
    assert any(item["family"].endswith("-Поправки") for item in result["selected_evidence"])
    assert result["termination"] == "sufficient"
