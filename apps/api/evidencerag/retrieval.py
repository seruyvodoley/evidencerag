"""Deterministic lexical controller. Coverage is a heuristic, never entailment."""
import hashlib
import sqlite3
import json
import re
import time
from functools import lru_cache

STOP = set('и в во на с со к ко из по за до от о об а но или не это как какой какая какое какие сколько ли для у при что чем быть можно нужно мне the a an is are of to for in and what how'.split())


@lru_cache(maxsize=1)
def morphology():
    import pymorphy3
    return pymorphy3.MorphAnalyzer()


@lru_cache(maxsize=20000)
def lemma(word):
    return morphology().parse(word)[0].normal_form if re.search('[а-яё]', word) else word


def terms(text):
    return list(dict.fromkeys(lemma(w) for w in re.findall(r'[\w]+', text.lower(), re.UNICODE) if len(w) > 1 and w not in STOP))


def normalized(text):
    return ' '.join(terms(text))


def stable_document_id(hit):
    """Content-derived opaque edition ID, stable across database rebuilds."""
    material = '\0'.join((hit.get('digest') or '', hit.get('family') or '',
                          hit.get('version') or '', hit.get('date') or ''))
    return 'doc-' + hashlib.sha256(material.encode('utf-8')).hexdigest()[:24]


def stable_evidence_id(hit):
    """Stable evidence ID within an immutable source edition."""
    material = '\0'.join((stable_document_id(hit), hit.get('locator') or '',
                          str(hit.get('page') or ''), str(hit.get('offset') or 0), hit.get('text') or ''))
    return 'ev-' + hashlib.sha256(material.encode('utf-8')).hexdigest()[:24]


def analyze_field_changes(hits, question=None, version_aware=True):
    """Separate same-edition disagreement from differences across editions.

    These are literal field signals only. They do not determine which statement is
    correct, whether an amendment supersedes an earlier clause, or semantic entailment.
    """
    facts = {}
    query_terms = set(terms(question)) if question else None
    for h in hits:
        for line in h['text'].splitlines():
            match = re.match(r'^([\wА-Яа-яЁё ()/-]{3,100}):\s*(.{1,200})$', line.strip())
            if match:
                key, value = match.groups()
                # Keep literal signals about fields named in the question; do not
                # surface an unrelated version change elsewhere in the context.
                field_terms = set(terms(key))
                if query_terms is not None and (not field_terms or not field_terms.issubset(query_terms)):
                    continue
                facts.setdefault((h['family'], key.lower()), []).append((value.strip(), h))
    conflict_signals, version_changes = [], []
    for (family, key), entries in facts.items():
        values = {v.casefold() for v, _ in entries}
        if len(values) <= 1:
            continue
        sources = [{'id': h['id'], 'document': h['document'], 'version': h.get('version'),
                    'date': h.get('date'), 'value': v} for v, h in entries]
        if not version_aware:
            conflict_signals.append({'field': key, 'family': family, 'kind': 'unscoped_literal_field_difference',
                                     'label': 'Разные literal значения; применимость редакций не учитывается',
                                     'sources': sources})
            continue
        by_edition = {}
        for value, hit in entries:
            edition = (hit.get('version') or '', hit.get('date') or '')
            by_edition.setdefault(edition, []).append((value, hit))

        # A single source edition that states different values is the narrowest
        # deterministic contradiction signal supported without semantic models.
        same_edition = []
        for edition_entries in by_edition.values():
            if len({v.casefold() for v, _ in edition_entries}) > 1:
                docs = {h.get('document') for _, h in edition_entries}
                if len(docs) == 1 or (edition_entries[0][1].get('version') and edition_entries[0][1].get('date')):
                    same_edition.extend(edition_entries)
        if same_edition:
            conflict_signals.append({'field': key, 'family': family, 'kind': 'same_edition_value_disagreement',
                                     'label': 'В одной редакции указаны разные значения; смысловая проверка не выполнена',
                                     'sources': sources})
            continue

        dates = {h.get('date') for _, h in entries}
        dated = bool(entries) and all(dates) and len(dates) > 1
        version_changes.append({'field': key, 'family': family,
                                'kind': 'dated_edition_change' if dated else 'applicability_unknown',
                                'label': 'Значения различаются между редакциями; порядок применения не установлен',
                                'sources': sources})
    return conflict_signals, version_changes


def conflicts(hits):
    """Compatibility helper: return only same-edition conflict signals."""
    return analyze_field_changes(hits)[0]


def adaptive_k(candidates, max_chunks, relevance_ratio=0.55):
    """Score-threshold top-k over the BM25 candidate pool (not Adaptive-k reproduction)."""
    selected, _ = adaptive_k_decision(candidates, max_chunks, relevance_ratio)
    return selected


def adaptive_k_decision(candidates, max_chunks, relevance_ratio=0.55):
    """Return selected hits and an auditable record of the score-gap cutoff."""
    candidates = candidates[:max_chunks]
    if len(candidates) <= 1:
        return candidates, {'candidate_count': len(candidates), 'selected_count': len(candidates),
                            'threshold': relevance_ratio, 'cutoff': 'candidate_pool_exhausted'}
    # SQLite FTS5 BM25 sorts ascending and generally returns negative values.
    best = abs(float(candidates[0].get('score') or 0))
    if best <= 0:
        return candidates[:1], {'candidate_count': len(candidates), 'selected_count': 1,
                                'threshold': relevance_ratio, 'cutoff': 'non_positive_best_score'}
    for index, hit in enumerate(candidates[1:], start=1):
        relative = abs(float(hit.get('score') or 0)) / best
        if relative < relevance_ratio:
            return candidates[:index], {'candidate_count': len(candidates), 'selected_count': index,
                                        'threshold': relevance_ratio, 'cutoff': 'relative_score_below_threshold',
                                        'last_included_relative_score': abs(float(candidates[index-1].get('score') or 0)) / best,
                                        'first_excluded_relative_score': relative}
    return candidates, {'candidate_count': len(candidates), 'selected_count': len(candidates),
                        'threshold': relevance_ratio, 'cutoff': 'threshold_not_crossed'}


def retrieve(store, ws, question, strategy='versioned', family=None, version=None, as_of=None,
             max_iterations=3, max_chunks=20, time_budget_ms=500, sufficiency=True, detect_conflicts=True,
             sufficiency_judge=None, use_versions=True, adaptation=True):
    started = time.perf_counter()
    query = terms(question)[:32]
    if strategy not in {'fixed5', 'fixed10', 'adaptive', 'versioned', 'sufficiency_guided', 'evidencerag'}:
        raise ValueError('Неизвестная стратегия')
    if not (1 <= max_iterations <= 5 and 1 <= max_chunks <= 50 and 1 <= time_budget_ms <= 5000):
        raise ValueError('Некорректный бюджет поиска')
    trace, selected, seen = [], [], set()
    deadline = started + time_budget_ms / 1000
    termination = 'complete'
    def search_terms(active, limit, fam):
        nonlocal termination
        if time.perf_counter() >= deadline:
            termination = 'time_budget'
            return []
        try:
            return store.search(ws, active, limit, fam, version, as_of, deadline=deadline)
        except sqlite3.OperationalError as exc:
            if 'interrupted' in str(exc) or 'locked' in str(exc):
                termination = 'time_or_database_budget'
                return []
            raise
    max_rounds = 1 if strategy.startswith('fixed') or strategy == 'adaptive' or not adaptation else max_iterations
    target = 5 if strategy == 'fixed5' else 10 if strategy == 'fixed10' else 4
    gaps = query[:]
    judge_gaps = []
    for iteration in range(max_rounds):
        if not query or time.perf_counter() >= deadline:
            termination = 'empty_query' if not query else 'time_budget'
            break
        # The accumulated budget applies to distinct processed chunks.
        remaining = max_chunks - len(selected)
        if remaining <= 0:
            termination = 'chunk_budget'
            break
        round_start = len(selected)
        active = query if iteration == 0 else (judge_gaps or gaps or query)
        pool_size = max_chunks if strategy == 'adaptive' else min(max_chunks, target)
        candidates = search_terms(active, pool_size, family)
        adaptive_details = None
        if strategy == 'adaptive':
            candidates, adaptive_details = adaptive_k_decision(candidates, max_chunks)
        new = [h for h in candidates if h['id'] not in seen][:remaining]
        selected.extend(new)
        seen.update(h['id'] for h in new)
        if use_versions and strategy in {'versioned', 'evidencerag'}:
            # Retrieve counterparts only within families encountered in this workspace.
            # Do not silently prefer "latest"; show both unless an explicit date/version was given.
            for fam in sorted({h['family'] for h in selected}):
                remaining = max_chunks - len(selected)
                if remaining <= 0:
                    break
                for h in search_terms(query, max_chunks, fam):
                    if h['id'] not in seen:
                        selected.append(h)
                        seen.add(h['id'])
                        remaining -= 1
                        if not remaining:
                            break
        covered = set().union(*(set(terms(h['text'])) for h in selected)) if selected else set()
        gaps = [t for t in query if t not in covered]
        judge_result = None
        if sufficiency_judge is not None and strategy in {'sufficiency_guided', 'evidencerag'}:
            judge_result = sufficiency_judge(question, selected)
            decision = judge_result.get('sufficient') if isinstance(judge_result, dict) else 'invalid'
            if decision is not None and not isinstance(decision, bool):
                raise ValueError('Судья достаточности должен вернуть sufficient=True, False или None')
            raw_gaps = judge_result.get('gaps', [])
            if not isinstance(raw_gaps, list) or len(raw_gaps) > 8 or any(not isinstance(g, str) or len(g) > 200 for g in raw_gaps):
                raise ValueError('Судья должен вернуть не более 8 кратких текстовых пробелов')
            judge_gaps = terms(' '.join(raw_gaps))[:32]
        reason = 'score_threshold' if strategy == 'adaptive' else 'judge_sufficient' if judge_result and judge_result['sufficient'] is True else 'judge_insufficient_expand' if judge_result and judge_result['sufficient'] is False else 'judge_unknown_expand' if strategy in {'sufficiency_guided', 'evidencerag'} else 'lexical_coverage_diagnostic'
        new_this_round = selected[round_start:]
        stop_now = strategy.startswith('fixed') or strategy == 'adaptive' or (judge_result and judge_result['sufficient'] is True) or not new_this_round or len(selected) >= max_chunks
        action = 'stop_search' if stop_now else 'retrieve_more'
        if strategy.startswith('fixed'):
            action = 'stop_search_fixed_k'
        elif judge_result and judge_result['sufficient'] is True:
            action = 'stop_search_judge_sufficient'
        elif not new_this_round:
            action = 'stop_search_no_new_evidence'
        elif len(selected) >= max_chunks:
            action = 'stop_search_chunk_budget'
        trace.append({'iteration': iteration + 1, 'query': active, 'selected_chunks': len(seen), 'gaps': gaps,
                      'judge_gaps': judge_gaps,
                      'selected_chunk_ids': [h['id'] for h in selected],
                      'new_chunk_ids': [h['id'] for h in new_this_round], 'new_chunks': len(new_this_round),
                      'sufficiency_judgement': judge_result['sufficient'] if judge_result else None,
                      'action': action, 'reason': reason, 'adaptive_cutoff': adaptive_details,
                      'elapsed_ms': round((time.perf_counter() - started) * 1000, 3)})
        if stop_now:
            break
        target = min(max_chunks, target * 2)
    found_conflicts, version_differences = analyze_field_changes(selected, question, version_aware=use_versions) if detect_conflicts else ([], [])
    coverage = 1 - len(gaps) / len(query) if query else 0
    formal = None
    # Formal confirmations are available ONLY for explicit authored demo annotations,
    # exact normalized questions, complete required citations, and applicable scope.
    for h in selected:
        for rule in json.loads(h['metadata']).get('formal_rules', []):
            if set(terms(rule['question'])) == set(query) and version == rule.get('version'):
                needed = set(rule.get('required_text', []))
                matching = [x for x in selected if any(t in x['text'] for t in needed)]
                if needed and all(any(t in x['text'] for x in matching) for t in needed):
                    formal = {'text': rule['answer'], 'citations': [x['id'] for x in matching], 'basis': 'authored_formal_rule'}
    status = 'no_results' if not selected else 'potential_conflict' if found_conflicts else 'versioned_difference' if version_differences else 'insufficient' if gaps else 'unverified'
    if formal and not found_conflicts:
        status = 'confirmed_formal'
    for hit in selected:
        document_id = stable_document_id(hit)
        evidence_id = stable_evidence_id(hit)
        hit['evidence_id'] = evidence_id
        hit['provenance'] = {'source_revision_id': document_id, 'revision': {'family': hit.get('family'),
                             'version': hit.get('version'), 'date': hit.get('date')},
                             'position': {'locator': hit.get('locator'), 'page': hit.get('page'),
                                          'offset': hit.get('offset')}, 'rank_score': hit.get('score')}
        hit.pop('digest', None)
    selected_by_id = {hit['id']: hit for hit in selected}
    for signal in [*found_conflicts, *version_differences]:
        for source in signal['sources']:
            selected_hit = selected_by_id.get(source['id'])
            if selected_hit:
                source['evidence_id'] = selected_hit['evidence_id']
                source['source_revision_id'] = selected_hit['provenance']['source_revision_id']
    return {'status': status, 'question': question, 'mode': 'lexical', 'answer': formal,
            'hits': selected, 'conflicts': found_conflicts, 'version_differences': version_differences,
            'gaps': gaps, 'lexical_coverage': round(coverage, 3),
            'termination': termination, 'trace': trace, 'strategy': strategy, 'elapsed_ms': round((time.perf_counter() - started) * 1000, 3),
            'limitations': 'Совпадение слов не доказывает достаточность или истинность. Изменения между редакциями не считаются конфликтом без подтверждения одного периода применимости. Без языкового судьи показаны исходные фрагменты и буквальные сигналы.'}
