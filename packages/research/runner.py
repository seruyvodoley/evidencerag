import argparse
import csv
import hashlib
import json
import math
import platform
import sqlite3
import statistics
import subprocess
import tempfile
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from evidencerag.parser import parse
from evidencerag.retrieval import retrieve, normalized, morphology
from evidencerag.store import EvidenceStore

ROOT=Path(__file__).resolve().parents[2]
STRATEGIES={
 'fixed5':('fixed5',{}), 'fixed10':('fixed10',{}), 'adaptive':('adaptive',{}), 'versioned':('versioned',{}),
 'without_sufficiency':('versioned',{'sufficiency':False}),
 'without_versions':('adaptive',{}), 'without_conflicts':('versioned',{'detect_conflicts':False}),
 'without_adaptation':('versioned',{'max_iterations':1})}


def load_corpus(store,ws):
    catalog=json.loads((ROOT/'datasets/demo/catalog.json').read_text())
    for c in catalog:
        for d in c['documents']:
            raw=(ROOT/'datasets/demo'/d['filename']).read_bytes()
            store.add(ws,d['filename'],raw,parse(raw,'.md'),d['title'],d['family'],d['version'],d['date'],{'formal_rules':d.get('formal_rules',[])})


def divide(a,b):
    return a/b if b else None


def wilson(success,n):
    if not n:return None
    z=1.96;p=success/n;den=1+z*z/n
    center=(p+z*z/(2*n))/den
    half=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/den
    return [center-half,center+half]


def evaluate(case, result, all_chunks):
    gold={c['id'] for c in all_chunks if any(t in c['text'] for t in case['required'])}
    # Gold provenance must respect the requested version/family/date, not just text.
    gold={c['id'] for c in all_chunks if c['id'] in gold and
          (not case['family'] or c['family']==case['family']) and
          (not case['version'] or c['version']==case['version']) and
          (not case['as_of'] or (c['date'] and c['date']<=case['as_of']))}
    ids={h['id'] for h in result['hits']}
    predicted=bool(result['answer'])
    actual_conflict=bool(result['conflicts'])
    answer=result['answer']['text'] if result['answer'] else ''
    return {'evidence_precision':divide(len(ids&gold),len(ids)) if gold else None,
      'evidence_recall':divide(len(ids&gold),len(gold)),
      'sufficiency_correct':int(predicted==case['sufficient']),
      'lexical_proxy_correct':int((result['lexical_coverage']==1 and not actual_conflict)==case['sufficient']),
      'false_abstention':int(not predicted and case['sufficient']), 'answerable':int(case['sufficient']),
      'unsupported_answer':int(predicted and not case['sufficient']), 'answered':int(predicted),
      'exact_match':int(normalized(answer)==normalized(case['gold_answer'])) if case['gold_answer'] is not None else None,
      'conflict_tp':int(actual_conflict and case['conflict']), 'conflict_fp':int(actual_conflict and not case['conflict']),
      'conflict_fn':int(not actual_conflict and case['conflict']),
      'iterations':len(result['trace']), 'context_chunks':len(ids), 'context_chars':sum(len(h['text']) for h in result['hits']),
      'latency_ms':result['elapsed_ms'], 'llm_calls':0, 'api_cost_usd':0, 'faithfulness':None}


def mean(rows,key):
    values=[r[key] for r in rows if r[key] is not None]
    return statistics.mean(values) if values else None


def run(output, split='test'):
    output=Path(output)
    output.mkdir(parents=True,exist_ok=False)
    cases=json.loads((ROOT/'datasets/evaluation/cases.json').read_text())
    cases=[c for c in cases if split=='all' or c['split']==split]
    inputs=[ROOT/'datasets/evaluation/cases.json',ROOT/'datasets/demo/catalog.json',*sorted((ROOT/'datasets/demo').glob('*.md'))]
    hashes={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs}
    config={'algorithm':'lexical-controller-v1','split':split,'seed':0,'max_iterations':3,'max_chunks':20,'time_budget_ms':500,
            'created_utc':datetime.now(timezone.utc).isoformat(),'input_hashes':hashes,'python':platform.python_version(),'sqlite':sqlite3.sqlite_version,
            'semantic_evaluator':None,'dataset_kind':'authored_synthetic','strategies':STRATEGIES}
    config['source_hashes']={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [*sorted((ROOT/'apps/api/evidencerag').glob('*.py')), Path(__file__).resolve()]}
    config['git_dirty']=bool(subprocess.run(['git','status','--porcelain'],capture_output=True,text=True,cwd=ROOT).stdout.strip())
    config['git_commit']=subprocess.run(['git','rev-parse','HEAD'],capture_output=True,text=True,cwd=ROOT).stdout.strip() or None
    morphology() # Explicit warm-up, excluded from per-query latency and recorded here.
    config['morphology_warmed']=True
    rows=[];traces=[]
    with tempfile.TemporaryDirectory(prefix='evidence-experiment-') as temp:
        store=EvidenceStore(Path(temp)/'run.sqlite3');ws=store.workspace(store.create_workspace());load_corpus(store,ws)
        with store.connect() as db:
            chunks=[dict(c) for c in db.execute('SELECT c.id,c.text,d.family,d.version,d.date,d.digest FROM chunks c JOIN documents d ON d.id=c.document')]
        for name,(strategy,extra) in STRATEGIES.items():
            for c in cases:
                options={'max_iterations':3,'max_chunks':20,'time_budget_ms':500,**extra}
                result=retrieve(store,ws,c['question'],strategy,c['family'],c['version'],c['as_of'],**options)
                metrics=evaluate(c,result,chunks)
                rows.append({'strategy':name,'case':c['id'],'category':c['category'],**metrics})
                traces.append({'strategy':name,'case':c,'config':options,'result':result})
    summaries=[]
    for name in STRATEGIES:
        subset=[r for r in rows if r['strategy']==name]
        tp=sum(r['conflict_tp'] for r in subset);fp=sum(r['conflict_fp'] for r in subset);fn=sum(r['conflict_fn'] for r in subset)
        summaries.append({'strategy':name,'n':len(subset),'evidence_precision':mean(subset,'evidence_precision'),
            'evidence_recall':mean(subset,'evidence_recall'),'sufficiency_accuracy':mean(subset,'sufficiency_correct'),
            'sufficiency_wilson95':wilson(sum(r['sufficiency_correct'] for r in subset),len(subset)),
            'lexical_proxy_accuracy':mean(subset,'lexical_proxy_correct'),
            'false_abstention_rate':divide(sum(r['false_abstention'] for r in subset),sum(r['answerable'] for r in subset)),
            'unsupported_answer_rate':divide(sum(r['unsupported_answer'] for r in subset),sum(r['answered'] for r in subset)),
            'answer_exact_match':mean(subset,'exact_match'),'conflict_precision':divide(tp,tp+fp),'conflict_recall':divide(tp,tp+fn),
            'conflict_f1':divide(2*tp,2*tp+fp+fn),'iterations':mean(subset,'iterations'),'context_chars':mean(subset,'context_chars'),
            'latency_ms':mean(subset,'latency_ms'),'faithfulness':None,'api_cost_usd':0})
    (output/'config.json').write_text(json.dumps(config,ensure_ascii=False,indent=2))
    (output/'traces.json').write_text(json.dumps(traces,ensure_ascii=False,indent=2))
    (output/'summary.json').write_text(json.dumps(summaries,ensure_ascii=False,indent=2))
    for filename,data in [('metrics.csv',rows),('summary.csv',summaries)]:
        with (output/filename).open('w',newline='') as f:
            writer=csv.DictWriter(f,fieldnames=data[0].keys());writer.writeheader();writer.writerows(data)
    report=['# Синтетическая проверка, не научное доказательство\n',f'Срез: {split}; {len(cases)} случаев на стратегию.','',
      '| Стратегия | Recall источников | F1 конфликтов | Ложный отказ | Средний контекст, символы |','|---|---:|---:|---:|---:|']
    for s in summaries:
        def fmt(x):return 'н/п' if x is None else f'{x:.3f}'
        report.append('| '+' | '.join([s['strategy'],fmt(s['evidence_recall']),fmt(s['conflict_f1']),fmt(s['false_abstention_rate']),fmt(s['context_chars'])])+' |')
    report.extend(['','Свободная генерация отключена. Faithfulness не измерена: независимого оценщика нет. Нулевое число неподтверждённых ответов при полном отказе от генерации не означает высокое качество ответов. Большинство достаточных вопросов получает отказ. Это ограничение текущей политики.','',
      'Абляция without_sufficiency отключает только лексическое условие остановки; without_adaptation ограничивает число итераций. Они не являются абляциями семантических моделей. Слишком малый корпус часто не различает стратегии. Wilson CI игнорирует зависимость вопросов одной семьи и приведён только как иллюстрация неопределённости; для статьи нужны семейный bootstrap и независимые документы.'])
    (output/'REPORT.md').write_text('\n'.join(report))
    return summaries


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',required=True);p.add_argument('--split',choices=['train','dev','test','all'],default='test');a=p.parse_args()
    summaries=run(a.output,a.split)
    print(f'Saved {len(summaries)} strategies in {a.output}; authored synthetic data only.')
