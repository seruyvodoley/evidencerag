"""Bounded LOCAL HTTP test. No VPN VPS stress by default; do not raise limits there."""
import argparse
import asyncio
import json
import statistics
import time
from pathlib import Path
import httpx


async def run(base, output, requests=40, concurrency=4):
    if requests>80 or concurrency>8:raise ValueError('Local smoke-load cap exceeded')
    async with httpx.AsyncClient(base_url=base,timeout=20) as client:
        response=await client.post('/api/workspaces');response.raise_for_status()
        response=await client.post('/api/demos/device/import');response.raise_for_status()
        semaphore=asyncio.Semaphore(concurrency)
        async def query(i):
            async with semaphore:
                started=time.perf_counter()
                r=await client.post('/api/search',json={'question':'Какая ёмкость аккумулятора?','family':'device'})
                valid=r.status_code==200 and bool(r.json().get('hits'))
                return {'status':r.status_code,'valid':valid,'ms':(time.perf_counter()-started)*1000}
        started=time.perf_counter();rows=await asyncio.gather(*(query(i) for i in range(requests)));duration=time.perf_counter()-started
        await client.delete('/api/workspace')
    lat=sorted(r['ms'] for r in rows)
    report={'target':'local loopback','requests':requests,'concurrency':concurrency,'valid_responses':sum(r['valid'] for r in rows),
        'duration_seconds':duration,'throughput_requests_per_second':requests/duration,'p50_ms':statistics.median(lat),'p95_ms':lat[int(.95*(len(lat)-1))],
        'statuses':{str(s):sum(r['status']==s for r in rows) for s in {r['status'] for r in rows}},'samples':rows,
        'limitation':'Short local test on developer Mac, not a VPS capacity estimate. Includes real FTS search over a tiny demo corpus.'}
    Path(output).write_text(json.dumps(report,indent=2));print(json.dumps({k:v for k,v in report.items() if k!='samples'},indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--base',default='http://127.0.0.1:8000');p.add_argument('--output',default='experiments/local-load.json');a=p.parse_args()
    asyncio.run(run(a.base,a.output))
