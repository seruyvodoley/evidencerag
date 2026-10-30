"""Read-only SSH audit; never reads VPN keys, peer configurations or environment secrets."""
import argparse
import json
import re
import subprocess

REMOTE = r'''
import json, os, platform, subprocess, urllib.request

def run(args):
    r=subprocess.run(args,capture_output=True,text=True,timeout=10)
    return {'exit':r.returncode,'output':r.stdout.strip()}
result={
 'os':open('/etc/os-release').read(), 'arch':platform.machine(), 'cpu':os.cpu_count(),
 'memory':run(['free','-m']), 'disk':run(['df','-h','/']),
 'listeners':run(['ss','-H','-lntu']),
 'services':run(['systemctl','list-units','--type=service','--state=running','--no-legend','--no-pager']),
 'resources':run(['ps','-eo','comm,%cpu,rss','--sort=-rss']),
 'python':run(['python3','--version']),
 'docker':run(['docker','ps','--format','{{.Names}} {{.Status}}']),
 'proxy':run(['docker','inspect','ma-alice-https','--format','{{json .HostConfig.NetworkMode}} {{json .Mounts}}']),
 'interfaces':os.listdir('/sys/class/net'),
 'vpn_links':{name:open('/sys/class/net/'+name+'/operstate').read().strip() for name in os.listdir('/sys/class/net') if name.startswith(('wg','awg','homeexit'))},
 'ssh_effective':run(['sshd','-T','-C','user=root,host=localhost,addr=127.0.0.1'])['output'].splitlines()[:0],
}
# Obtain only route hostnames from Caddy's existing read-only admin API.
try:
    data=json.load(urllib.request.urlopen('http://127.0.0.1:2019/config/',timeout=3))
    hosts=[]
    def walk(obj):
        if isinstance(obj,dict):
            if isinstance(obj.get('host'),list):hosts.extend(obj['host'])
            for v in obj.values():walk(v)
        elif isinstance(obj,list):
            for v in obj:walk(v)
    walk(data);result['proxy_hosts']=sorted(set(hosts))
except Exception:result['proxy_hosts']='unavailable'
print(json.dumps(result))
'''


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--host',required=True);parser.add_argument('--key',required=True);parser.add_argument('--port',default='22');parser.add_argument('--output',required=True);args=parser.parse_args()
    command=['ssh','-i',args.key,'-p',args.port,'-o','BatchMode=yes','-o','StrictHostKeyChecking=yes','-o','ConnectTimeout=6',args.host,'python3 -']
    result=subprocess.run(command,input=REMOTE,text=True,capture_output=True,timeout=45)
    if result.returncode:
        raise SystemExit('Read-only audit failed; no configuration changed')
    payload=json.loads(result.stdout)
    # Reports intentionally omit IP addresses, including IPv6 listeners.
    payload['listeners']['output']='\n'.join(re.sub(r'\S+:([0-9]+)',r'[bind]:\1',line) for line in payload['listeners']['output'].splitlines())
    sanitized=re.sub(r'\b(?:\d{1,3}\.){3}\d{1,3}\b','[address]',json.dumps(payload,ensure_ascii=False,indent=2))
    from pathlib import Path
    Path(args.output).write_text(sanitized)
    print(sanitized)


if __name__=='__main__':main()
