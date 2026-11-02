"""Author-created Stage 010 regression cases; not an independent benchmark."""

from evidencerag.research_rag import (
    SearchRequest, StructuredClaimEvaluator, SufficiencyStatus,
    StructuredFactAnswerGenerator, validate_answer,
)


QUESTION = (
    'Какие требования действуют на 3 ноября 2026 года для итогового зачёта '
    'по практикуму «Полевой корпус речи»? Укажи количество аудиозаписей, '
    'максимальную длительность каждой, формат файлов и крайний срок сдачи. '
    'Приведи источники.'
)
TITLE = 'Положение о зачёте по практикуму «Полевой корпус речи»'


def hit(ident, text, date, family='speech-corpus', version='2026', title=TITLE):
    return {'evidence_id': ident, 'text': text, 'date': date, 'family': family,
            'version': version, 'title': title, 'source_revision_id': 'doc-' + ident}


def corpus():
    return [
        hit('speech-2025',
            'Итоговый зачёт состоит из семи аудиозаписей. Максимальная длительность каждой — не более четырёх минут. Файлы принимаются в формате WAV. Срок сдачи — до 30 ноября 2025 года включительно.',
            '2025-09-01', version='2025'),
        hit('speech-2026',
            'Итоговый зачёт состоит из девяти аудиозаписей. Максимальная длительность каждой — не более пяти минут. Файлы принимаются в формате WAV. Срок сдачи — до 15 ноября 2026 года включительно.',
            '2026-09-01'),
        hit('speech-amendment',
            'Поправка к Положение о зачёте по практикуму «Полевой корпус речи». В редакции от 1 сентября 2026 года пункт 4.2 изменить: формат файлов установить FLAC; срок сдачи установить до 30 ноября 2026 года включительно.',
            '2026-10-20', family='speech-corpus-amendment', version='2026-10',
            title='Поправка к положению о Полевом корпусе речи'),
    ]


def evaluate(hits=None, question=QUESTION, as_of=None):
    return StructuredClaimEvaluator().evaluate(SearchRequest(question, as_of=as_of), hits or corpus(), [])


def claims_by_id(assessment):
    return {claim.claim_id: claim for claim in assessment.supported_claims}


def test_unseen_question_slots_and_cross_family_partial_amendment():
    hits = corpus()
    assessment = evaluate(hits)
    assert assessment.status is SufficiencyStatus.SUFFICIENT
    facts = claims_by_id(assessment)
    assert facts['count:аудиозапись'].value == '9'
    assert facts['duration'].value == '5'
    assert facts['duration'].operator == 'less_or_equal'
    assert facts['format'].value == 'FLAC'
    assert facts['deadline'].value == '2026-11-30'
    assert facts['format'].evidence_ids == ('speech-amendment',)
    assert facts['deadline'].evidence_ids == ('speech-amendment',)
    assert facts['count:аудиозапись'].evidence_ids == ('speech-2026',)
    answer = validate_answer(StructuredFactAnswerGenerator().generate(
        SearchRequest(QUESTION), hits, assessment), hits, assessment)
    assert len(answer['claims']) == 4
    assert 'flac' in answer['text'] and '2026-11-30' in answer['text']


def test_maximum_question_does_not_accept_exact_value():
    question = 'Укажи максимальную длительность каждой записи.'
    docs = [hit('exact', 'Длительность каждой записи ровно 5 минут.', '2026-09-01')]
    result = evaluate(docs, question)
    assert result.status is SufficiencyStatus.INSUFFICIENT
    assert not result.supported_claims


def test_minimum_question_does_not_accept_exact_value():
    question = 'Сколько минимум аудиозаписей требуется?'
    docs = [hit('exact', 'Требуется ровно пять аудиозаписей.', '2026-09-01')]
    result = evaluate(docs, question)
    assert result.status is not SufficiencyStatus.SUFFICIENT


def test_minimum_question_accepts_only_an_explicit_lower_bound():
    docs = [hit('minimum', 'Требуется не менее пяти аудиозаписей.', '2026-09-01')]
    result = evaluate(docs, 'Сколько минимум аудиозаписей требуется?')
    assert result.status is SufficiencyStatus.SUFFICIENT
    assert claims_by_id(result)['count:аудиозапись'].operator == 'greater_or_equal'


def test_inclusive_deadline_is_preserved():
    docs = [hit('deadline', 'Крайний срок сдачи — до 30 ноября 2026 года включительно.', '2026-09-01')]
    result = evaluate(docs, 'Каков крайний срок сдачи?')
    assert result.status is SufficiencyStatus.SUFFICIENT
    assert claims_by_id(result)['deadline'].value == '2026-11-30'
    assert claims_by_id(result)['deadline'].text.endswith('включительно')


def test_question_and_filter_date_conflict_refuses_current_claim():
    result = evaluate(as_of='2026-11-04')
    assert result.status is SufficiencyStatus.APPLICABILITY_UNCERTAIN
    assert not result.supported_claims
    assert 'расходится' in result.missing_information[0].description


def test_unrelated_same_date_amendment_does_not_change_target_document():
    docs = corpus()
    docs[-1] = hit('foreign-amendment',
        'Поправка к Положению о зачёте для другой группы. В редакции от 1 сентября 2026 года пункт 4.2 изменить: формат файлов установить PDF.',
        '2026-10-20', family='other-amendment', title='Поправка для другой группы')
    result = evaluate(docs)
    assert result.status is SufficiencyStatus.SUFFICIENT
    assert claims_by_id(result)['format'].value == 'WAV'
    assert 'foreign-amendment' not in claims_by_id(result)['format'].evidence_ids


def test_draft_fact_is_not_promoted_to_supported_claim():
    docs = [hit('draft', 'Проект положения: требуется 9 аудиозаписей.', '2026-09-01')]
    result = evaluate(docs, 'Сколько аудиозаписей требуется?')
    assert result.status is SufficiencyStatus.INSUFFICIENT
    assert not result.supported_claims


def test_forbidden_format_is_not_reported_as_an_allowed_format():
    docs = [hit('forbidden', 'Формат файлов WAV запрещён.', '2026-09-01')]
    result = evaluate(docs, 'Какой формат файлов разрешён?')
    assert result.status is SufficiencyStatus.INSUFFICIENT
    assert not result.supported_claims


def test_unrelated_conditional_format_does_not_replace_general_requirement():
    docs = [hit('conditions',
        'Если участник заочного отделения, формат файлов — MP3. Общий формат файлов для участников — WAV.',
        '2026-09-01')]
    result = evaluate(docs, 'Какой общий формат файлов требуется?')
    assert result.status is SufficiencyStatus.SUFFICIENT
    assert claims_by_id(result)['format'].value == 'WAV'


def test_unknown_date_does_not_support_current_claim():
    docs = [hit('undated', 'Требуется 9 аудиозаписей.', '')]
    result = evaluate(docs, 'Сколько аудиозаписей требуется?')
    assert result.status is SufficiencyStatus.APPLICABILITY_UNCERTAIN
    assert not result.supported_claims


def test_sqlite_revision_index_accepts_competing_legacy_amendment(tmp_path):
    import json
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'apps/api'))
    from evidencerag.parser import parse
    from evidencerag.store import EvidenceStore
    from evidencerag.research_rag import EvidenceStoreBackend, SearchBudget, run_pipeline

    fixture = json.loads((Path(__file__).resolve().parents[1] /
                          'experiments/stage009/fixtures/ifiyak-known-case.json').read_text(encoding='utf-8'))
    store = EvidenceStore(tmp_path / 'stage010-revisions.sqlite3')
    workspace = store.workspace(store.create_workspace())
    documents = list(fixture['documents']) + [{
        'title': 'Поправка 2026 — конфликт', 'family': fixture['family'] + '-Поправки-2',
        'version': '2026', 'date': '2026-10-15',
        'text': 'С 15 октября 2026 года в редакции от 1 сентября 2026 года время выполнения изменено: вместо 20 минут устанавливается 30 минут.'
    }]
    for index, document in enumerate(documents):
        raw = document['text'].encode('utf-8')
        store.add(workspace, f'stage010-{index}.txt', raw, parse(raw, '.txt'), document['title'],
                  document['family'], document['version'], document['date'])
    request = SearchRequest(fixture['question'], family=fixture['family'], as_of='2026-10-31')
    result = run_pipeline(request, EvidenceStoreBackend(store, workspace), StructuredClaimEvaluator(),
        StructuredFactAnswerGenerator(), SearchBudget(max_iterations=3, max_chunks=20,
        time_budget_ms=3000, initial_top_k=5))
    assert result['assessment']['status'] == 'conflicting'
    assert not result['answer']['claims']
    assert len(result['assessment']['conflicting_claims']) == 1
