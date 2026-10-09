import hashlib,json,os,pathlib,resource,signal,subprocess,time
OUT=pathlib.Path(__file__).resolve().parent;argv=[str(OUT/'StaticSVG'),str(OUT/'manifest.json'),str(OUT/'png')];env=os.environ.copy();env['TMPDIR']=str(OUT/'compiler-tmp');t=time.monotonic()
with (OUT/'render-standard.stdout').open('x') as stdout,(OUT/'render-standard.stderr').open('x') as stderr:
    p=subprocess.Popen(argv,env=env,stdout=stdout,stderr=stderr,start_new_session=True)
    try:rc=p.wait(timeout=60);timed=False
    except subprocess.TimeoutExpired:os.killpg(p.pid,signal.SIGKILL);rc=p.wait();timed=True
receipt=dict(argv=argv,returncode=rc,timed_out=timed,timeout_seconds=60,elapsed_seconds=time.monotonic()-t,render_binary_sha256=hashlib.sha256((OUT/'StaticSVG').read_bytes()).hexdigest(),swift_source_sha256=hashlib.sha256((OUT/'StaticSVG.swift').read_bytes()).hexdigest(),children_peak_rss_bytes_macos=resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss,scope='One standard sandbox execution; isolated static file documents, nonpersistent WKWebView data store, no content JavaScript, no remote navigation')
(OUT/'render-standard-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt,indent=2))
