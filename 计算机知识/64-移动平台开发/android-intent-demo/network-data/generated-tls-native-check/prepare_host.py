from pathlib import Path
import subprocess,json,shutil,os,sys,time,hashlib
r=Path(__file__).resolve().parent;p=r/'project';gen=p/'network-server/fixtures/generated';wrong=r/'wrong-host';wrong.mkdir(mode=0o700);unknown=r/'unknown-ca';openssl='/usr/bin/openssl';log=(r/'certificate-generation.log').open('w');commands=[]
def run(cmd):
 commands.append(cmd);subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT,check=True)
(wrong/'server.cnf').write_text('''[req]\ndistinguished_name=dn\nprompt=no\n[dn]\nCN=wrong.invalid\n[server]\nbasicConstraints=critical,CA:false\nkeyUsage=critical,digitalSignature,keyEncipherment\nsubjectKeyIdentifier=hash\nauthorityKeyIdentifier=keyid,issuer\nextendedKeyUsage=serverAuth\nsubjectAltName=DNS:wrong.invalid\n''')
run([openssl,'req','-new','-newkey','rsa:2048','-nodes','-sha256','-config',str(wrong/'server.cnf'),'-keyout',str(wrong/'server.key'),'-out',str(wrong/'server.csr')]);run([openssl,'x509','-req','-in',str(wrong/'server.csr'),'-CA',str(gen/'ca.pem'),'-CAkey',str(gen/'ca-public-fixture.key'),'-set_serial','17503','-days','3650','-sha256','-extfile',str(wrong/'server.cnf'),'-extensions','server','-out',str(wrong/'server.pem')]);run(['sh',str(p/'network-server/fixtures/generate-fixtures.sh'),str(unknown)])
# Public certificate/config metadata only. Keys remain local.
meta={'trusted_ca_sha256':hashlib.sha256((gen/'ca.pem').read_bytes()).hexdigest(),'unknown_ca_sha256':hashlib.sha256((unknown/'ca.pem').read_bytes()).hexdigest(),'generation_argv':commands};servers=[]
for name,cert,key in [('positive',gen/'server.pem',gen/'server-public-fixture.key'),('wrong-host',wrong/'server.pem',wrong/'server.key'),('unknown-ca',unknown/'server.pem',unknown/'server-public-fixture.key')]:
 out=r/('server-'+name);out.mkdir();cmd=[sys.executable,'-B',str(p/'network-server/http_authority.py'),'--contract','/Users/ysz/Misc/Obsidian/Valults/WLM/WWL/计算机知识/75-软件工程与人机交互/reservation_v2.py','--database',str(out/'authority.db'),'--events',str(out/'events.jsonl'),'--ready',str(out/'ready.json'),'--port','0','--cert',str(cert),'--key',str(key)];f=(out/'server.log').open('w');proc=subprocess.Popen(cmd,stdout=f,stderr=subprocess.STDOUT,start_new_session=True)
 for _ in range(60):
  if proc.poll() is not None:raise RuntimeError((out/'server.log').read_text())
  if (out/'ready.json').exists():break
  time.sleep(.1)
 else:raise RuntimeError('server ready timeout')
 ready=json.loads((out/'ready.json').read_text());servers.append({'name':name,'pid':proc.pid,'argv':cmd,'port':ready['port'],'cert_sha256':hashlib.sha256(cert.read_bytes()).hexdigest()})
meta['servers']=servers;(r/'host-fixture.json').write_text(json.dumps(meta,indent=2));print('ready three owned dynamic loopback TLS endpoints')
