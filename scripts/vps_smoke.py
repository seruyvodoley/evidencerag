"""Run on VPS against loopback. Tiny smoke check, never a capacity/load experiment."""
import io
import json
import re
import statistics
import subprocess
import time
import httpx
from pypdf import PdfWriter

checks={}
with httpx.Client(base_url='http://127.0.0.1:8077',timeout=20) as c:
    r=c.get('/');checks['frontend']=r.status_code==200 and 'Основание' in r.text
    assets=re.findall(r'(?:src|href)="(/assets/[^\"]+)"',r.text)
    checks['assets']=bool(assets) and all(c.get(a).status_code==200 for a in assets)
    r=c.post('/api/workspaces');r.raise_for_status();checks['secure_cookie']='Secure' in r.headers['set-cookie']
    c.headers['Cookie']='evidence_session='+r.cookies['evidence_session']
    r=c.post('/api/demos/device/import');r.raise_for_status()
    docs=c.get('/api/documents').json();checks['demo_import']=len(docs)==2
    r=c.post('/api/search',json={'question':'Какая ёмкость аккумулятора?','family':'device'});r.raise_for_status();data=r.json()
    checks['version_signal']=data['status']=='potential_conflict' and len(data['hits'])==2
    r=c.post('/api/search',json={'question':'Какая ёмкость аккумулятора?','family':'device','version':'2.0'});r.raise_for_status();data=r.json()
    checks['formal_rule']=data['status']=='confirmed_formal' and '3600' in data['answer']['text']
    hit=data['hits'][0];source=c.get('/api/documents/'+hit['document']).json()
    checks['real_citation']=any(h['id']==hit['id'] and h['text']==hit['text'] for h in source['chunks'])
    checks['original_download']=len(c.get('/api/documents/'+hit['document']+'/original').content)>100
    r=c.post('/api/compare',json={'left':docs[0]['id'],'right':docs[1]['id']});r.raise_for_status()
    checks['diff']=bool(r.json()['changes']) and bool(r.json()['conflicts'])
    r=c.post('/api/documents',files={'file':('smoke.txt','Проверка сервера: сапфир721'.encode())});r.raise_for_status();private=r.json()
    r=c.post('/api/search',json={'question':'сапфир721'});r.raise_for_status();checks['private_upload_search']=bool(r.json()['hits'])
    b=io.BytesIO();w=PdfWriter();w.add_blank_page(width=100,height=100);w.write(b)
    r=c.post('/api/documents',files={'file':('scan.pdf',b.getvalue())});r.raise_for_status();checks['scan_status']=r.json()['status']=='needs_ocr'
    from docx import Document
    doc=Document();doc.add_heading('Section',level=1);doc.add_paragraph('VPS parser smoke');buf=io.BytesIO();doc.save(buf)
    r=c.post('/api/documents',files={'file':('smoke.docx',buf.getvalue())});r.raise_for_status();checks['docx_parse']=any('VPS parser smoke' in x['text'] for x in r.json()['chunks'])
    checks['bad_format_rejected']=c.post('/api/documents',files={'file':('bad.exe',b'abc')}).status_code==415
    checks['csrf_rejected']=c.post('/api/workspaces',headers={'Origin':'https://unrelated.invalid'}).status_code==403
    with httpx.Client(base_url='http://127.0.0.1:8077',timeout=10) as other:
        r=other.post('/api/workspaces');other.headers['Cookie']='evidence_session='+r.cookies['evidence_session']
        checks['isolation']=other.get('/api/documents/'+private['id']).status_code==404
        other.delete('/api/workspace')
    c.delete('/api/documents/'+private['id'])
    checks['deletion']=not c.post('/api/search',json={'question':'сапфир721'}).json()['hits']
    latency=[]
    for _ in range(5):
        started=time.perf_counter();r=c.post('/api/search',json={'question':'Какая ёмкость аккумулятора?','family':'device'});r.raise_for_status();latency.append((time.perf_counter()-started)*1000)
    checks['cleanup']=c.delete('/api/workspace').status_code==200
result={'checks':checks,'passed':sum(checks.values()),'total':len(checks),'query_latency_ms':latency,
    'median_query_ms':statistics.median(latency),'service':subprocess.run(['systemctl','show','evidencerag.service','-p','ActiveState','-p','MemoryCurrent','-p','CPUUsageNSec'],capture_output=True,text=True).stdout,
    'limitation':'5 sequential real queries on tiny corpus; not a VPS load/capacity test'}
print(json.dumps(result,ensure_ascii=False,indent=2))
if not all(checks.values()):raise SystemExit(1)
