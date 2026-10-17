from pathlib import Path
import os,subprocess,json,hashlib
r=Path(__file__).resolve().parent;d=r/'resource-final-apks';env=os.environ.copy();env['JAVA_HOME']='/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home';sign='/private/tmp/wwl-next-175-env/sdk/build-tools/34.0.0/apksigner';keytool=env['JAVA_HOME']+'/bin/keytool';ks='/private/tmp/wwl-next-175-env/android-user/debug.keystore';log=(d/'signing.log').open('w');rows=[]
def run(cmd):
 rows.append(cmd);subprocess.run(cmd,env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
other=r/'ephemeral-other-signer.p12'
run([keytool,'-genkeypair','-keystore',str(other),'-storetype','PKCS12','-storepass','android','-keypass','android','-alias','wwl-teaching-other','-keyalg','RSA','-keysize','2048','-validity','3650','-dname','CN=WWL175 disposable alternate signer NOT PRODUCTION'])
for dest,key,alias in [('v3-release-same-debugcert.apk',ks,'androiddebugkey'),('v3-release-other-cert.apk',str(other),'wwl-teaching-other')]:
 run([sign,'sign','--ks',key,'--ks-key-alias',alias,'--ks-pass','pass:android','--key-pass','pass:android','--out',str(d/dest),str(d/'v3-release-unsigned.apk')])
records={}
for p in d.glob('*.apk'):
 if p.name.endswith('unsigned.apk'):continue
 cmd=[sign,'verify','--verbose','--print-certs',str(p)];q=subprocess.run(cmd,env=env,capture_output=True,text=True,check=True);(d/(p.stem+'-certificate.txt')).write_text(q.stdout+q.stderr);records[p.name]={'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'bytes':p.stat().st_size,'verify_argv':cmd,'certificate_output':p.stem+'-certificate.txt'}
(d/'signing-commands.json').write_text(json.dumps(rows,indent=2));(d/'apk-identities.json').write_text(json.dumps(records,indent=2));print('signed same/alternate teaching cert; public cert metadata saved; no private-key export')
