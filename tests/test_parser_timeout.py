import subprocess
from fastapi.testclient import TestClient
from evidencerag import main
from evidencerag.store import EvidenceStore


def test_slow_parser_fails_closed(tmp_path,monkeypatch):
    monkeypatch.setattr(main,'STORE',EvidenceStore(tmp_path/'timeout.sqlite3'))
    def timeout(*args,**kwargs):raise subprocess.TimeoutExpired('parser',15)
    monkeypatch.setattr(main.subprocess,'run',timeout)
    with TestClient(main.app,client=('timeout-test',1)) as client:
        client.post('/api/workspaces')
        response=client.post('/api/documents',files={'file':('slow.pdf',b'%PDF-test')})
        assert response.status_code==422
        assert client.get('/api/documents').json()==[]
