"""Read-only, secret-free status/fingerprint snapshot. Run on VPS using python3."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import time


def run(args):
    r=subprocess.run(args,capture_output=True,text=True,timeout=10)
    return r.stdout if r.returncode==0 else None


def fingerprint(value):
    return hashlib.sha256(value.encode()).hexdigest() if value is not None else None


def wg_status(tool):
    if not shutil.which(tool):return None
    text=run([tool,'show','all','latest-handshakes']) or ''
    ages=[]
    for line in text.splitlines():
        fields=line.split()
        if len(fields)>=3 and fields[-1].isdigit() and int(fields[-1]):ages.append(int(time.time())-int(fields[-1]))
    return {'peers_with_handshake':len(ages),'recent_180_seconds':sum(a<180 for a in ages)}

units=['wg-quick@wg0','wg-quick@homeexit','xray','tunneldeck-xray-xhttp','tunneldeck-xray-xhttp-tls']
services={u:run(['systemctl','show',u,'-p','ActiveState','-p','InvocationID']) for u in units}
result={'services':services,'interfaces':[n for n in Path('/sys/class/net').iterdir() if n.name.startswith(('wg','awg','homeexit'))],
        'routes_sha256':fingerprint(run(['ip','-j','route','show','table','all'])),
        'rules_sha256':fingerprint(run(['ip','-j','rule','show'])),
        'firewall_sha256':fingerprint(run(['nft','--stateless','list','ruleset'])),
        'docker_networks_sha256':fingerprint(run(['docker','network','ls','--no-trunc','--format','{{.ID}} {{.Name}} {{.Driver}}'])),
        'wg':wg_status('wg'),'awg':wg_status('awg')}
result['interfaces']=[p.name for p in result['interfaces']]
print(json.dumps(result,indent=2))
