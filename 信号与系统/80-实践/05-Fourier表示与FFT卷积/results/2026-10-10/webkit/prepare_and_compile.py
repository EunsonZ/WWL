import hashlib,json,os,pathlib,platform,subprocess,sys,time,xml.etree.ElementTree as ET
OUT=pathlib.Path(__file__).resolve().parent;SOURCE=OUT.parent/'current-bound-01/source-layout'
items=[];bindings=[]
for p in sorted(SOURCE.rglob('*.svg')):
    data=p.read_bytes();tree=ET.fromstring(data);width=float(tree.attrib['width']);height=float(tree.attrib['height'])
    assert not any(v.startswith(('http:','https:','//')) for elem in tree.iter() for v in elem.attrib.values())
    items.append(dict(source=str(p),width=width,height=height,output=p.stem+'.png'))
    bindings.append(dict(source=str(p),sha256=hashlib.sha256(data).hexdigest(),bytes=len(data),width=width,height=height,viewBox=tree.attrib['viewBox']))
assert len(items)==5
(OUT/'manifest.json').write_text(json.dumps(items,ensure_ascii=False,indent=2)+'\n');(OUT/'source-bindings.json').write_text(json.dumps(bindings,ensure_ascii=False,indent=2)+'\n')
(OUT/'compiler-tmp').mkdir()
env=os.environ.copy();env['CLANG_MODULE_CACHE_PATH']=str(OUT/'module-cache');env['TMPDIR']=str(OUT/'compiler-tmp')
argv=['/usr/bin/xcrun','swiftc','-swift-version','5','-module-cache-path',str(OUT/'module-cache'),'-framework','AppKit','-framework','WebKit',str(OUT/'StaticSVG.swift'),'-o',str(OUT/'StaticSVG')]
t=time.monotonic()
with (OUT/'compile.stdout').open('x') as stdout,(OUT/'compile.stderr').open('x') as stderr:
    try:rc=subprocess.run(argv,env=env,stdout=stdout,stderr=stderr,timeout=60).returncode;timed=False
    except subprocess.TimeoutExpired:rc=None;timed=True
receipt=dict(phase='compilation preparation only, no rendering yet',argv=argv,returncode=rc,timed_out=timed,timeout_seconds=60,elapsed_seconds=time.monotonic()-t,environment=dict(python=sys.version,platform=platform.platform(),compiler_cache=env['CLANG_MODULE_CACHE_PATH'],compiler_tmp=env['TMPDIR']))
(OUT/'compile-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt,indent=2))
