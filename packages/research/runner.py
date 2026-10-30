"""Reproducible, offline retrieval experiment runner.

This harness measures retrieval and literal field signals. It has no answer generator
or semantic sufficiency judge; answer quality and abstention metrics are therefore null.
"""

import argparse
import csv
import hashlib
import json
import os
import platform
import sqlite3
import statistics
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from evidencerag.parser import parse
from evidencerag.retrieval import morphology, retrieve, stable_document_id, stable_evidence_id
from evidencerag.store import EvidenceStore

ROOT = Path(__file__).resolve().parents[2]

# All methods share max_iterations, max_chunks and time_budget_ms. Fixed-k has a
# smaller stopping rule by definition; actual context and latency are reported.
STRATEGIES = {
    'fixed_k': ('fixed5', {}),
    'fixed10_sensitivity': ('fixed10', {}),
    'adaptive_k_score_gap': ('adaptive', {}),
    'sufficiency_guided_no_judge': ('sufficiency_guided', {}),
    'proposed_evidencerag': ('evidencerag', {}),
    'without_version_awareness': ('evidencerag', {'use_versions': False}),
    'without_literal_conflict_signals': ('evidencerag', {'detect_conflicts': False}),
    'without_iterative_expansion': ('evidencerag', {'adaptation': False}),
}


def sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def load_corpus(store, workspace):
    catalog = json.loads((ROOT / 'datasets/demo/catalog.json').read_text(encoding='utf-8'))
    for corpus in catalog:
        for document in corpus['documents']:
            raw = (ROOT / 'datasets/demo' / document['filename']).read_bytes()
            parsed = parse(raw, '.md')
            store.add(workspace, document['filename'], raw, parsed, document['title'],
                      document['family'], document['version'], document['date'],
                      {'formal_rules': document.get('formal_rules', [])})


def stable_ids(chunks):
    """Assign content-derived IDs stable across isolated SQLite database runs."""
    document_ids = {}
    evidence_ids = {}
    for chunk in chunks:
        document_ids[chunk['document']] = stable_document_id(chunk)
        evidence_ids[chunk['id']] = stable_evidence_id(chunk)
    return document_ids, evidence_ids


def divide(numerator, denominator):
    return numerator / denominator if denominator else None


def evaluate(case, result, all_chunks):
    required = case.get('required', [])
    allowed = [chunk for chunk in all_chunks
               if (not case.get('family') or chunk['family'] == case['family'])
               and (not case.get('version') or chunk['version'] == case['version'])
               and (not case.get('as_of') or (chunk['date'] and chunk['date'] <= case['as_of']))]
    gold_ids = {chunk['id'] for chunk in allowed
                if any(phrase.casefold() in chunk['text'].casefold() for phrase in required)}
    returned_ids = {hit['id'] for hit in result['hits']}
    found_requirements = sum(
        any(phrase.casefold() in hit['text'].casefold() for hit in result['hits'])
        for phrase in required
    )
    requirement_coverage = divide(found_requirements, len(required)) if required else None

    expected = case['expected_resolution']
    predicted_conflict = bool(result['conflicts'])
    predicted_version_change = bool(result.get('version_differences'))
    return {
        'evidence_precision': divide(len(returned_ids & gold_ids), len(returned_ids)) if gold_ids else None,
        'evidence_recall': divide(len(returned_ids & gold_ids), len(gold_ids)) if gold_ids else None,
        'required_span_coverage': requirement_coverage,
        'required_spans_found': found_requirements if required else None,
        'required_spans_total': len(required) if required else None,
        'gold_resolution': expected,
        'predicted_same_edition_conflict': int(predicted_conflict),
        'gold_same_edition_conflict': int(expected == 'within_edition_conflict'),
        'conflict_tp': int(predicted_conflict and expected == 'within_edition_conflict'),
        'conflict_fp': int(predicted_conflict and expected != 'within_edition_conflict'),
        'conflict_fn': int(not predicted_conflict and expected == 'within_edition_conflict'),
        'predicted_version_change': int(predicted_version_change),
        'gold_version_change': int(expected == 'versioned_difference'),
        'version_tp': int(predicted_version_change and expected == 'versioned_difference'),
        'version_fp': int(predicted_version_change and expected != 'versioned_difference'),
        'version_fn': int(not predicted_version_change and expected == 'versioned_difference'),
        # Deliberately null: this runner has neither an answerer nor a semantic judge.
        'sufficiency_prediction': None,
        'sufficiency_accuracy': None,
        'answer_exact_match': None,
        'answer_correctness': None,
        'false_abstention': None,
        'unsupported_answer': None,
        'faithfulness': None,
        'iterations': len(result['trace']),
        'context_chunks': len(returned_ids),
        'context_chars': sum(len(hit['text']) for hit in result['hits']),
        'latency_ms': result['elapsed_ms'],
        'answer_generation_enabled': False,
        'semantic_sufficiency_judge_enabled': any(
            step.get('sufficiency_judgement') is not None for step in result['trace']),
    }


def mean(rows, key):
    values = [row[key] for row in rows if row[key] is not None]
    return statistics.mean(values) if values else None


def binary_scores(rows, prefix):
    tp = sum(row[f'{prefix}_tp'] for row in rows)
    fp = sum(row[f'{prefix}_fp'] for row in rows)
    fn = sum(row[f'{prefix}_fn'] for row in rows)
    return {
        'precision': divide(tp, tp + fp),
        'recall': divide(tp, tp + fn),
        'f1': divide(2 * tp, 2 * tp + fp + fn),
        'tp': tp,
        'fp': fp,
        'fn': fn,
    }


def serializable_result(result, document_ids, evidence_ids):
    def serial_source(source):
        return {
            'evidence_id': evidence_ids.get(source['id']),
            'source_revision_id': document_ids.get(source['document']),
            'version': source.get('version'),
            'date': source.get('date'),
            'value': source.get('value'),
        }

    trace = []
    for step in result['trace']:
        trace.append({
            **{key: value for key, value in step.items() if key not in {'selected_chunk_ids', 'new_chunk_ids'}},
            'selected_evidence_ids': [evidence_ids.get(ident) for ident in step.get('selected_chunk_ids', [])],
            'new_evidence_ids': [evidence_ids.get(ident) for ident in step.get('new_chunk_ids', [])],
        })
    return {
        'status': result['status'],
        'answer': result['answer'],
        'strategy': result['strategy'],
        'termination': result['termination'],
        'elapsed_ms': result['elapsed_ms'],
        'lexical_coverage': result['lexical_coverage'],
        'gaps': result['gaps'],
        'limitations': result['limitations'],
        'hits': [{
            'evidence_id': evidence_ids.get(hit['id']),
            'source_revision_id': document_ids.get(hit['document']),
            'title': hit['title'],
            'family': hit['family'],
            'version': hit['version'],
            'date': hit['date'],
            'locator': hit['locator'],
            'page': hit['page'],
            'offset': hit['offset'],
            'rank_score': hit.get('score'),
            'text': hit['text'],
        } for hit in result['hits']],
        'conflicts': [{**signal, 'sources': [serial_source(s) for s in signal['sources']]}
                      for signal in result['conflicts']],
        'version_differences': [{**signal, 'sources': [serial_source(s) for s in signal['sources']]}
                                for signal in result.get('version_differences', [])],
        'trace': trace,
    }


def run(output, split='test'):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    cases_path = ROOT / 'datasets/evaluation/cases.json'
    cases = json.loads(cases_path.read_text(encoding='utf-8'))
    cases = [case for case in cases if split == 'all' or case['split'] == split]
    corpus_files = sorted(path for path in (ROOT / 'datasets/demo').glob('*.md')
                          if not path.name.startswith('._'))
    input_files = [cases_path, ROOT / 'datasets/demo/catalog.json', ROOT / 'datasets/demo/LICENSE', *corpus_files]
    input_hashes = {str(path.relative_to(ROOT)): sha256(path.read_bytes()) for path in input_files}
    source_files = [ROOT / 'apps/api/evidencerag/retrieval.py', ROOT / 'apps/api/evidencerag/store.py',
                    ROOT / 'apps/api/evidencerag/parser.py', ROOT / 'pyproject.toml', ROOT / 'uv.lock',
                    Path(__file__).resolve()]
    source_hashes = {str(path.relative_to(ROOT)): sha256(path.read_bytes()) for path in source_files}
    commit = subprocess.run(['git', 'rev-parse', 'HEAD'], capture_output=True, text=True, cwd=ROOT).stdout.strip()
    dirty = bool(subprocess.run(['git', 'status', '--porcelain', '--untracked-files=no'],
                                capture_output=True, text=True, cwd=ROOT).stdout.strip())
    config = {
        'algorithm': 'evidencerag-retrieval-controller-v2',
        'split': split,
        'seed': 0,
        'seed_use': 'No random sampling is used in this deterministic lexical run.',
        'budget': {'max_iterations': 3, 'max_chunks': 20, 'time_budget_ms': 500},
        'created_utc': datetime.now(timezone.utc).isoformat(),
        'git_commit': commit or None,
        'git_dirty_tracked_before_run': dirty,
        'source_hashes': source_hashes,
        'input_hashes': input_hashes,
        'python': platform.python_version(),
        'platform': platform.platform(),
        'processor': platform.processor(),
        'cpu_count': os.cpu_count(),
        'sqlite': sqlite3.sqlite_version,
        'dataset_kind': 'authored_synthetic_fixture',
        'answer_generation': None,
        'semantic_sufficiency_judge': None,
        'metrics_not_measured': ['answer correctness', 'semantic sufficiency', 'false abstention',
                                 'unsupported answer rate', 'faithfulness', 'API cost'],
        'strategies': STRATEGIES,
        'fixed_context_threshold': 'Adaptive score-gap ratio 0.55 is a predeclared heuristic, not tuned on test and not an Adaptive-k reproduction.',
    }

    morphology()  # Warm-up is outside per-query timing.
    rows, traces = [], []
    with tempfile.TemporaryDirectory(prefix='evidence-experiment-') as temp:
        store = EvidenceStore(Path(temp) / 'run.sqlite3')
        workspace = store.workspace(store.create_workspace())
        load_corpus(store, workspace)
        with store.connect() as db:
            chunks = [dict(row) for row in db.execute('''
                SELECT c.id,c.document,c.text,c.locator,c.page,c.offset,d.title,d.family,d.version,d.date,d.digest
                FROM chunks c JOIN documents d ON d.id=c.document ORDER BY c.id
            ''')]
        document_ids, evidence_ids = stable_ids(chunks)

        for strategy_name, (controller_strategy, extra) in STRATEGIES.items():
            for case in cases:
                options = {'max_iterations': 3, 'max_chunks': 20, 'time_budget_ms': 500, **extra}
                result = retrieve(
                    store, workspace, case['question'], controller_strategy,
                    family=case.get('family'), version=case.get('version'), as_of=case.get('as_of'),
                    **options,
                )
                metrics = evaluate(case, result, chunks)
                rows.append({'strategy': strategy_name, 'case': case['id'],
                             'evaluation_cluster': case['evaluation_cluster'],
                             'category': case['category'], **metrics})
                traces.append({
                    'strategy': strategy_name,
                    'case_id': case['id'],
                    'question': case['question'],
                    'expected_resolution': case['expected_resolution'],
                    'gold_required_spans': case.get('required', []),
                    'config': options,
                    'result': serializable_result(result, document_ids, evidence_ids),
                })

    summaries = []
    for name in STRATEGIES:
        subset = [row for row in rows if row['strategy'] == name]
        conflict = binary_scores(subset, 'conflict')
        version = binary_scores(subset, 'version')
        summaries.append({
            'strategy': name,
            'n_queries': len(subset),
            'n_evaluation_clusters': len({row['evaluation_cluster'] for row in subset}),
            'evidence_precision': mean(subset, 'evidence_precision'),
            'evidence_recall': mean(subset, 'evidence_recall'),
            'required_span_coverage': mean(subset, 'required_span_coverage'),
            'same_edition_conflict': conflict,
            'dated_version_change': version,
            'answer_generation_enabled': False,
            'answer_correctness': None,
            'semantic_sufficiency_accuracy': None,
            'false_abstention_rate': None,
            'unsupported_answer_rate': None,
            'faithfulness': None,
            'iterations': mean(subset, 'iterations'),
            'context_chunks': mean(subset, 'context_chunks'),
            'context_chars': mean(subset, 'context_chars'),
            'latency_ms': mean(subset, 'latency_ms'),
            'api_cost_usd': None,
        })

    (output / 'config.json').write_text(json.dumps(config, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    (output / 'traces.json').write_text(json.dumps(traces, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    (output / 'summary.json').write_text(json.dumps(summaries, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    for filename, data in [('metrics.csv', rows), ('summary.csv', summaries)]:
        with (output / filename).open('w', newline='', encoding='utf-8') as file:
            writer = csv.DictWriter(file, fieldnames=data[0].keys())
            writer.writeheader()
            writer.writerows(data)

    report = [
        '# Offline synthetic retrieval pilot',
        '',
        f'Split: {split}; {len(cases)} queries per configuration; {len(STRATEGIES)} configurations.',
        'The corpus is author-created synthetic data. It is useful for controlled regression checks, not independent empirical evidence.',
        '',
        '| Configuration | Evidence recall | Required-span coverage | Same-edition conflict F1 | Version-change F1 | Mean chunks |',
        '|---|---:|---:|---:|---:|---:|',
    ]
    for summary in summaries:
        def fmt(value):
            return 'not measured' if value is None else f'{value:.3f}'
        report.append('| ' + ' | '.join([
            summary['strategy'], fmt(summary['evidence_recall']), fmt(summary['required_span_coverage']),
            fmt(summary['same_edition_conflict']['f1']), fmt(summary['dated_version_change']['f1']),
            fmt(summary['context_chunks']),
        ]) + ' |')
    report.extend([
        '',
        'No semantic sufficiency judge or answer generator ran. Answer correctness, false abstention, unsupported answers and faithfulness are null by design; the previous False Abstention=1.0 was an artifact of treating an absent formal-rule answer as a generated answer refusal.',
        'The score-gap top-k is an FTS5 BM25 heuristic inspired by adaptive context sizing; it is not a replication of Adaptive-k, which uses dense similarity thresholds. The sufficiency-guided configuration records UNKNOWN because no judge is installed, then expands retrieval within the common budget.',
        'The proposed controller is an engineering prototype that preserves dated version differences and same-edition literal disagreement separately. It is not a validated new method. There are only a few independent synthetic evaluation clusters; no confidence interval or significance claim is reported.',
        'Every trace includes content-derived evidence IDs, source position, version/date, retrieval score, chosen evidence and controller reasons. Variable wall-clock measurements are retained in raw outputs.',
    ])
    (output / 'REPORT.md').write_text('\n'.join(report) + '\n', encoding='utf-8')
    return summaries


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', required=True)
    parser.add_argument('--split', choices=['train', 'dev', 'test', 'all'], default='test')
    args = parser.parse_args()
    summary = run(args.output, args.split)
    print(f'Saved {len(summary)} configurations in {args.output}; authored synthetic data only.')
