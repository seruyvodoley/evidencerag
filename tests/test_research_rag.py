"""Diagnostic tests for the offline research pipeline; all backends here are test doubles."""

import json
import time
import pytest

from evidencerag.research_rag import (
    ConflictingClaim,
    EvidenceGap,
    FormalRequirement,
    FormalRule,
    FormalRuleEvaluator,
    GapKind,
    InjectedSemanticEvaluator,
    LiteralExtractAnswerGenerator,
    SearchBudget,
    SearchRequest,
    SufficiencyAssessment,
    SufficiencyStatus,
    SupportedClaim,
    UnavailableSemanticEvaluator,
    parse_semantic_assessment,
    run_pipeline,
    validate_answer,
)


def hit(ident, text, *, doc="doc-a", version="1.0", date="2025-01-01"):
    return {"id": ident, "document": doc, "evidence_id": f"ev-{ident}", "text": text,
            "family": "contract", "version": version, "date": date, "locator": "§1"}


def test_formal_rule_needs_exact_authored_quote_and_applicable_version():
    rule = FormalRule("Каков лимит?", (FormalRequirement(
        "claim-limit", "Лимит — 20 тыс.", "Лимит финансирования: 20 тыс. рублей",
        "лимит финансирования", allowed_versions=("2.0",)),))
    evaluator = FormalRuleEvaluator((rule,))
    lexical_lookalike = hit(1, "Лимит финансирования составляет двадцать тысяч рублей", version="2.0")
    result = evaluator.evaluate(SearchRequest("Каков лимит?"), [lexical_lookalike], [])
    assert result.status is SufficiencyStatus.INSUFFICIENT
    assert result.missing_information[0].kind is GapKind.EVIDENCE_SPAN

    exact = hit(2, "Лимит финансирования: 20 тыс. рублей", version="2.0")
    result = evaluator.evaluate(SearchRequest("Каков лимит?", version="2.0"), [exact], [])
    assert result.status is SufficiencyStatus.SUFFICIENT
    assert result.supported_claims[0].evidence_ids == ("ev-2",)


def test_formal_direct_quote_answer_is_citation_checked_and_labelled_literal():
    exact = hit(2, "Лимит финансирования: 20 тыс. рублей", version="2.0")
    rule = FormalRule("Каков лимит?", (FormalRequirement(
        "claim-limit", "Лимит финансирования: 20 тыс. рублей", "Лимит финансирования: 20 тыс. рублей",
        "лимит финансирования", allowed_versions=("2.0",)),))

    class Backend:
        def search(self, query, limit, family, version, as_of, deadline):
            return [exact]

    result = run_pipeline(SearchRequest("Каков лимит?", version="2.0"), Backend(),
                          FormalRuleEvaluator((rule,)), LiteralExtractAnswerGenerator())
    assert result["assessment"]["status"] == "sufficient"
    assert result["answer"]["status"] == "answered"
    assert result["answer"]["verification"] == "literal_citation_checked"
    assert result["answer"]["claims"][0]["citations"][0]["id"] == "ev-2"


def test_gap_directed_search_finds_amendment_and_stops_when_sufficient():
    original = hit(1, "Первоначальный лимит финансирования: 100 рублей", version="1.0")
    amendment = hit(2, "Дополнительное соглашение изменило лимит финансирования: 75 рублей",
                    doc="doc-b", version="2.0", date="2025-04-01")
    calls = []

    class Backend:
        def search(self, query, limit, family, version, as_of, deadline):
            calls.append((query, limit, family, version, as_of))
            return [original] if len(calls) == 1 else [original, amendment]

    class Judge:
        name = "test-double-gap-judge"

        def evaluate(self, request, hits, history):
            if len(hits) == 1:
                return SufficiencyAssessment(
                    SufficiencyStatus.INSUFFICIENT,
                    supported_claims=(SupportedClaim("initial", "Изначально 100 рублей", ("ev-1",)),),
                    missing_information=(EvidenceGap("amendment", GapKind.ATTRIBUTE,
                        "Нет применимого изменённого лимита.", "дополнительное соглашение лимит финансирования",
                        target_version="2.0"),), evidence_ids=("ev-1",), evaluator=self.name)
            return SufficiencyAssessment(
                SufficiencyStatus.SUFFICIENT,
                supported_claims=(SupportedClaim("current", "После изменения 75 рублей", ("ev-2",)),),
                evidence_ids=("ev-1", "ev-2"), evaluator=self.name)

    result = run_pipeline(SearchRequest("Какой лимит действует после изменения?", family="contract"),
                          Backend(), Judge(), budget=SearchBudget(max_iterations=3, max_chunks=8))
    assert len(calls) == 2
    assert "дополнительное соглашение" in calls[1][0]
    assert calls[1][3] == "2.0"
    assert result["trace"][0]["action"] == "check_version"
    assert result["trace"][1]["action"] == "stop_sufficient"
    assert result["trace"][1]["new_document_count"] == 1
    assert result["trace"][1]["new_evidence_claim_count"] == 1
    assert result["answer"]["status"] == "refused"  # No answerer was configured.


def test_repeated_gap_stops_when_search_returns_no_new_evidence():
    original = hit(1, "Исходное условие финансирования: 100 рублей")

    class Backend:
        def search(self, query, limit, family, version, as_of, deadline):
            return [original]

    class Judge:
        name = "test-double-gap-judge"

        def evaluate(self, request, hits, history):
            return SufficiencyAssessment(SufficiencyStatus.INSUFFICIENT,
                missing_information=(EvidenceGap("gap", GapKind.RELATION, "Нет последующего изменения.",
                                                 "изменение дополнительное соглашение"),),
                evidence_ids=("ev-1",), evaluator=self.name)

    result = run_pipeline(SearchRequest("Что действует после изменения?"), Backend(), Judge())
    assert result["termination"] == "no_new_evidence_chunks"
    assert result["trace"][1]["action"] == "stop_no_new_evidence_chunks"
    assert result["trace"][1]["new_document_count"] == 0
    assert result["trace"][1]["new_evidence_chunk_count"] == 0
    assert result["trace"][1]["new_evidence_claim_count"] == 0


def test_new_chunk_without_new_supported_claim_stops_and_is_reported_separately():
    first, second = hit(1, "Первый фрагмент", doc="doc-a"), hit(2, "Второй фрагмент", doc="doc-b")
    calls = []

    class Backend:
        def search(self, query, limit, family, version, as_of, deadline):
            calls.append(query)
            return [first] if len(calls) == 1 else [second]

    class Judge:
        name = "test-double-stuck-gap"

        def evaluate(self, request, hits, history):
            return SufficiencyAssessment(SufficiencyStatus.INSUFFICIENT,
                missing_information=(EvidenceGap("gap", GapKind.OTHER, "Нужна дата.", "дата поправки"),),
                evidence_ids=tuple(h["evidence_id"] for h in hits), evaluator=self.name)

    result = run_pipeline(SearchRequest("Какова дата?"), Backend(), Judge())
    assert len(calls) == 2
    # The controller does not stop merely because no new claim signature appeared.
    # It detects that the same gap query was exhausted after a second chunk arrived.
    assert result["termination"] == "repeated_query"
    assert result["trace"][-1]["action"] == "stop_repeated_query"
    assert result["trace"][-1]["new_evidence_chunk_count"] == 1
    assert result["trace"][-1]["new_evidence_claim_count"] == 0


def test_repeated_gap_query_with_new_claim_is_recorded_and_stopped():
    first, second = hit(1, "Первый фрагмент", doc="doc-a"), hit(2, "Второй фрагмент", doc="doc-b")
    calls = []

    class Backend:
        def search(self, query, limit, family, version, as_of, deadline):
            calls.append(query)
            return [first] if len(calls) == 1 else [second]

    class Judge:
        name = "test-double-repeated-gap"

        def evaluate(self, request, hits, history):
            claims = tuple(SupportedClaim(f"claim-{i}", f"Claim {i}", (h["evidence_id"],))
                           for i, h in enumerate(hits, start=1))
            return SufficiencyAssessment(SufficiencyStatus.INSUFFICIENT, supported_claims=claims,
                missing_information=(EvidenceGap("gap", GapKind.OTHER, "Нужны дополнительные сведения.",
                                                 "дополнительное соглашение"),),
                evidence_ids=tuple(h["evidence_id"] for h in hits), evaluator=self.name)

    result = run_pipeline(SearchRequest("Каковы условия?"), Backend(), Judge())
    assert len(calls) == 2
    assert result["termination"] == "repeated_query"
    assert result["trace"][-1]["action"] == "stop_repeated_query"
    assert result["trace"][-1]["new_evidence_claim_count"] == 1


def test_budget_stop_is_explicit_and_answer_is_not_generated():
    class Backend:
        def search(self, query, limit, family, version, as_of, deadline):
            return [hit(1, "Условие договора")]

    class Judge:
        name = "test-double-insufficient"

        def evaluate(self, request, hits, history):
            return SufficiencyAssessment(SufficiencyStatus.INSUFFICIENT,
                missing_information=(EvidenceGap("gap", GapKind.OTHER, "Не хватает условий.", "поправка"),),
                evidence_ids=("ev-1",), evaluator=self.name)

    result = run_pipeline(SearchRequest("Какие условия?"), Backend(), Judge(),
                          budget=SearchBudget(max_iterations=1, max_chunks=3))
    assert result["termination"] == "iteration_budget"
    assert result["trace"][0]["action"] == "stop_iteration_budget"
    assert result["answer"]["status"] == "refused"
    assert result["answer"]["refusal_reason"] == "evidence_insufficient"


def test_chunk_and_time_budgets_stop_with_explicit_trace_actions():
    class GapJudge:
        name = "test-budget"

        def evaluate(self, request, hits, history):
            return SufficiencyAssessment(
                SufficiencyStatus.INSUFFICIENT,
                missing_information=(EvidenceGap("gap", GapKind.OTHER, "Нужен ещё источник.", "дополнение"),),
                evidence_ids=tuple(h["evidence_id"] for h in hits), evaluator=self.name)

    gap_judge = GapJudge()

    class OneHitBackend:
        def search(self, query, limit, family, version, as_of, deadline):
            return [hit(1, "Условие")]

    chunk_result = run_pipeline(SearchRequest("Вопрос?"), OneHitBackend(), gap_judge,
                                budget=SearchBudget(max_iterations=3, max_chunks=1, initial_top_k=1))
    assert chunk_result["termination"] == "chunk_budget"
    assert chunk_result["trace"][0]["action"] == "stop_chunk_budget"

    class SlowBackend:
        def search(self, query, limit, family, version, as_of, deadline):
            time.sleep(0.01)
            return [hit(2, "Условие")]

    time_result = run_pipeline(SearchRequest("Вопрос?"), SlowBackend(), gap_judge,
                               budget=SearchBudget(max_iterations=3, max_chunks=5, time_budget_ms=1,
                                                   initial_top_k=1))
    assert time_result["termination"] == "time_budget"
    assert time_result["trace"][0]["action"] == "stop_time_budget"


def test_no_results_returns_explicit_refusal_not_false_answer():
    class EmptyBackend:
        def search(self, query, limit, family, version, as_of, deadline):
            return []

    result = run_pipeline(SearchRequest("Неизвестный факт?"), EmptyBackend())
    assert result["termination"] == "no_results"
    assert result["assessment"]["status"] == "uncertain"
    assert result["answer"]["status"] == "refused"
    assert result["answer"]["refusal_reason"] == "evidence_uncertain"


def test_different_versions_do_not_become_a_conflict_without_same_scope_rule():
    old = hit(1, "Срок возврата: 14 дней", version="2024", date="2024-01-01")
    current = hit(2, "Срок возврата: 30 дней", doc="doc-b", version="2025", date="2025-01-01")
    rule = FormalRule("Какой срок возврата?", (FormalRequirement(
        "return-current", current["text"], current["text"], "срок возврата",
        allowed_versions=("2025",)),))
    result = FormalRuleEvaluator((rule,)).evaluate(
        SearchRequest("Какой срок возврата?", version="2025"), [old, current], [])
    assert result.status is SufficiencyStatus.SUFFICIENT
    assert result.conflicting_claims == ()
    assert result.supported_claims[0].evidence_ids == ("ev-2",)


def test_version_gap_applies_requested_version_to_next_retrieval():
    first = hit(1, "Лимит: 100", version="1.0")
    second = hit(2, "Лимит: 75", doc="doc-b", version="2.0", date="2025-04-01")
    calls = []

    class Backend:
        def search(self, query, limit, family, version, as_of, deadline):
            calls.append((query, version, as_of))
            return [first] if len(calls) == 1 else [second]

    class Judge:
        name = "test-double-version-judge"

        def evaluate(self, request, hits, history):
            if len(hits) == 1:
                return SufficiencyAssessment(SufficiencyStatus.INSUFFICIENT,
                    missing_information=(EvidenceGap("version", GapKind.VERSION,
                        "Проверить редакцию 2.0", "изменённый лимит", target_version="2.0"),),
                    evidence_ids=tuple(h["evidence_id"] for h in hits), evaluator=self.name)
            return SufficiencyAssessment(SufficiencyStatus.UNCERTAIN,
                reasoning_summary="Дата применимости не установлена.",
                evidence_ids=tuple(h["evidence_id"] for h in hits), evaluator=self.name)

    result = run_pipeline(SearchRequest("Лимит на 2025-05-01?", family="contract"), Backend(), Judge())
    assert calls[1][1] == "2.0"
    assert result["trace"][0]["action"] == "check_version"
    assert result["assessment"]["status"] == "uncertain"
    assert result["answer"]["status"] == "refused"


def test_no_semantic_backend_keeps_uncertain_and_does_not_call_answer_generator():
    called = {"answerer": 0}

    class Backend:
        def search(self, query, limit, family, version, as_of, deadline):
            return [hit(1, "Совпадают отдельные слова: поправка, лимит")]

    class Answerer:
        name = "must-not-run"

        def generate(self, request, hits, assessment):
            called["answerer"] += 1
            raise AssertionError("uncertain context must not reach generator")

    result = run_pipeline(SearchRequest("Что доказано?"), Backend(), UnavailableSemanticEvaluator(), Answerer(),
                          SearchBudget(max_iterations=1, max_chunks=3))
    assert result["assessment"]["status"] == "uncertain"
    assert result["answer"]["status"] == "refused"
    assert called["answerer"] == 0


def test_version_applicability_unknown_is_never_upgraded_by_lexical_match():
    rule = FormalRule("Каков лимит?", (FormalRequirement(
        "claim-limit", "Лимит — 20", "Лимит: 20", "лимит", allowed_versions=("2.0",)),))
    old = hit(1, "Лимит: 20", version="2.0", date="")
    assessment = FormalRuleEvaluator((rule,)).evaluate(
        SearchRequest("Каков лимит?", as_of="2025-01-01"), [old], [])
    assert assessment.status is SufficiencyStatus.INSUFFICIENT
    assert assessment.missing_information


def test_conflict_stops_and_unresolved_status_is_preserved():
    one, two = hit(1, "Лимит: 100"), hit(2, "Лимит: 75", doc="doc-b")

    class Backend:
        def search(self, query, limit, family, version, as_of, deadline):
            return [one, two]

    class Judge:
        name = "test-double-conflict"

        def evaluate(self, request, hits, history):
            return SufficiencyAssessment(SufficiencyStatus.CONFLICTING,
                conflicting_claims=(ConflictingClaim("Разные суммы", ("ev-1", "ev-2")),),
                evidence_ids=("ev-1", "ev-2"), evaluator=self.name)

    result = run_pipeline(SearchRequest("Какой лимит?"), Backend(), Judge())
    assert result["termination"] == "conflict"
    assert result["trace"][0]["action"] == "stop_conflict"
    assert result["answer"]["status"] == "refused"


def test_semantic_backend_requires_consent_and_rejects_unknown_evidence_ids():
    evidence = hit(1, "Точный источник с формулировкой")
    calls = []
    invalid_response = {"status": "sufficient", "supported_claims": [{"claim_id": "x", "text": "x", "evidence_ids": ["ev-fake"]}],
                        "missing_information": [], "conflicting_claims": [], "evidence_ids": ["ev-fake"],
                        "version_constraints": {}, "reasoning_summary": "ok", "recommended_action": "stop"}

    class Backend:
        def assess(self, payload):
            calls.append(payload)
            return invalid_response

    denied = InjectedSemanticEvaluator(Backend(), consent=False)
    assert denied.evaluate(SearchRequest("question"), [evidence], []).status is SufficiencyStatus.UNCERTAIN
    assert calls == []
    enabled = InjectedSemanticEvaluator(Backend(), consent=True)
    result = enabled.evaluate(SearchRequest("question"), [evidence], [])
    assert result.status is SufficiencyStatus.UNCERTAIN
    assert "document_handling" in calls[0]
    with pytest.raises(ValueError, match="неизвестные доказательства"):
        parse_semantic_assessment(invalid_response, {"ev-1"}, "test")


def test_semantic_backend_unavailable_fails_closed_to_uncertain():
    class OfflineBackend:
        def assess(self, payload):
            raise ConnectionError("offline")

    result = InjectedSemanticEvaluator(OfflineBackend(), consent=True).evaluate(
        SearchRequest("Есть ответ?"), [hit(1, "Совпадение слов")], [])
    assert result.status is SufficiencyStatus.UNCERTAIN
    assert "недоступен" in result.reasoning_summary


def test_compatible_api_adapter_needs_key_and_budget_even_with_consent(monkeypatch):
    from evidencerag.llm import CompatibleModel
    import asyncio

    monkeypatch.setenv("LLM_ENABLED", "true")
    monkeypatch.setenv("LLM_BUDGET_USD", "1")
    monkeypatch.setenv("LLM_MAX_REQUEST_USD", "0.1")
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    with pytest.raises(ValueError, match="необходимы согласие, ключ и утверждённый бюджет"):
        asyncio.run(CompatibleModel().generate("question", [], consent=True))


def test_answer_citations_must_be_real_exact_and_verbatim():
    evidence = hit(1, "В документе указан предел финансирования 75 рублей.")
    good = {"status": "answered", "claims": [{"text": "В документе указан предел финансирования 75 рублей.",
            "citations": [{"id": "ev-1", "quote": "В документе указан предел финансирования 75 рублей."}]}],
            "verification": "literal_citation_checked", "unresolved_conflicts": [], "refusal_reason": None}
    assert validate_answer(good, [evidence]) == good
    bad_link = {**good, "claims": [{**good["claims"][0],
                "citations": [{"id": "ev-fake", "quote": good["claims"][0]["text"]}]}]}
    import pytest
    with pytest.raises(ValueError):
        validate_answer(bad_link, [evidence])
    free_inference = {**good, "claims": [{"text": "Теперь действует 75 рублей.",
                       "citations": good["claims"][0]["citations"]}]}
    with pytest.raises(ValueError, match="дословные"):
        validate_answer(free_inference, [evidence])


def test_semantic_payload_rejects_unverifiable_confidence_and_fake_citations():
    allowed = {"ev-1"}
    payload = {"status": "sufficient", "supported_claims": [{"claim_id": "x", "text": "fact", "evidence_ids": ["ev-1"]}],
               "missing_information": [], "conflicting_claims": [], "evidence_ids": ["ev-1"],
               "version_constraints": {}, "reasoning_summary": "ok", "recommended_action": "stop",
               "confidence": 0.91}
    with pytest.raises(ValueError, match="Confidence"):
        parse_semantic_assessment(payload, allowed, "test")


def test_retrieval_results_are_deduplicated_and_capped_by_requested_k():
    results = [hit(1, "fragment one"), hit(1, "duplicate fragment"), hit(2, "fragment two")]

    class Backend:
        def search(self, query, limit, family, version, as_of, deadline):
            return results

    trace = run_pipeline(SearchRequest("question"), Backend(), UnavailableSemanticEvaluator(),
                         budget=SearchBudget(max_iterations=1, max_chunks=2, initial_top_k=2))
    assert len(trace["selected_evidence"]) == 2
    assert trace["trace"][0]["returned_evidence_ids"] == ["ev-1", "ev-2"]


def test_external_answerer_failure_fails_closed_without_exposing_exception_text():
    evidence = hit(1, "Лимит финансирования: 20 тыс. рублей")
    rule = FormalRule("Каков лимит?", (FormalRequirement(
        "limit", evidence["text"], evidence["text"], "лимит", allowed_versions=("1.0",)),))

    class Backend:
        def search(self, query, limit, family, version, as_of, deadline):
            return [evidence]

    class OfflineAnswerer:
        name = "test-offline"

        def generate(self, request, hits, assessment):
            raise RuntimeError("secret-key-should-not-appear")

    result = run_pipeline(SearchRequest("Каков лимит?", version="1.0"), Backend(),
                          FormalRuleEvaluator((rule,)), OfflineAnswerer())
    assert result["answer"]["status"] == "refused"
    assert result["answer"]["refusal_reason"] == "answer_validation_failed"
    assert "secret-key" not in json.dumps(result)


def test_saved_store_trace_uses_stable_ids_and_refuses_overwrite(tmp_path):
    import pytest
    from packages.research.trace_runner import run

    first = run(tmp_path / "first")
    second = run(tmp_path / "second")
    project = lambda result: (result["termination"], result["assessment"]["status"],
                              result["answer"]["claims"],
                              [(x["action"], x["new_evidence_ids"], x["new_supported_claim_ids"])
                               for x in result["trace"]])
    assert project(first) == project(second)
    assert first["trace"][0]["action"] == "stop_chunk_budget"
    assert first["assessment"]["status"] == "insufficient"
    with pytest.raises(FileExistsError):
        run(tmp_path / "first")

