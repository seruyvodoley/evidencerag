"""Deterministic lexical controller. Coverage is a heuristic, never entailment."""
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


def conflicts(hits):
    """Only flag matching literal key:value statements; do not infer semantic conflicts."""
    facts = {}
    for h in hits:
        for line in h['text'].splitlines():
            match = re.match(r'^([\wА-Яа-яЁё ()/-]{3,100}):\s*(.{1,200})$', line.strip())
            if match:
                key, value = match.groups()
                facts.setdefault((h['family'], key.lower()), []).append((value.strip(), h))
    result = []
    for (family, key), entries in facts.items():
        if len({v for v, _ in entries}) > 1:
            result.append({'field': key, 'family': family, 'kind': 'literal_field_difference',
                           'label': 'Разные значения одного поля; применимость требует проверки',
                           'sources': [{'id': h['id'], 'document': h['document'], 'version': h['version'], 'value': v} for v, h in entries]})
    return result


def retrieve(store, ws, question, strategy='versioned', family=None, version=None, as_of=None,
             max_iterations=3, max_chunks=20, time_budget_ms=500, sufficiency=True, detect_conflicts=True):
    started = time.perf_counter()
    query = terms(question)[:32]
    if strategy not in {'fixed5', 'fixed10', 'adaptive', 'versioned'}:
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
    max_rounds = 1 if strategy.startswith('fixed') else max_iterations
    target = 5 if strategy == 'fixed5' else 10 if strategy == 'fixed10' else 4
    gaps = query[:]
    for iteration in range(max_rounds):
        if not query or time.perf_counter() >= deadline:
            termination = 'empty_query' if not query else 'time_budget'
            break
        # The accumulated budget applies to distinct processed chunks.
        remaining = max_chunks - len(selected)
        if remaining <= 0:
            termination = 'chunk_budget'
            break
        active = query if iteration == 0 else (gaps or query)
        candidates = search_terms(active, min(max_chunks, target), family)
        new = [h for h in candidates if h['id'] not in seen][:remaining]
        selected.extend(new)
        seen.update(h['id'] for h in new)
        if strategy == 'versioned':
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
        reason = 'lexical_coverage_reached' if not gaps and sufficiency else 'expand_missing_terms'
        trace.append({'iteration': iteration + 1, 'query': active, 'selected_chunks': len(seen), 'gaps': gaps,
                      'reason': reason, 'elapsed_ms': round((time.perf_counter() - started) * 1000, 3)})
        if (not gaps and sufficiency) or not new or len(selected) >= max_chunks:
            break
        target = min(max_chunks, target * 2)
    found_conflicts = conflicts(selected) if detect_conflicts else []
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
    status = 'no_results' if not selected else 'potential_conflict' if found_conflicts else 'insufficient' if gaps else 'unverified'
    if formal and not found_conflicts:
        status = 'confirmed_formal'
    return {'status': status, 'question': question, 'mode': 'lexical', 'answer': formal,
            'hits': selected, 'conflicts': found_conflicts, 'gaps': gaps, 'lexical_coverage': round(coverage, 3),
            'termination': termination, 'trace': trace, 'strategy': strategy, 'elapsed_ms': round((time.perf_counter() - started) * 1000, 3),
            'limitations': 'Совпадение слов не доказывает утверждение. Без языковой модели показаны исходные фрагменты и формальные сигналы.'}
