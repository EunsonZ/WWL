"""Preview or restore only this structure batch, preserving subsequent edits.

Run without --apply first. The manifest is retained as a recovery receipt.
"""
from pathlib import Path
import argparse,hashlib,json,os,shutil

def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def safe(root,rel):
    p=root/rel
    if not p.resolve().is_relative_to(root.resolve()):raise RuntimeError('Path outside root: '+rel)
    if any(q.is_symlink() for q in [p,*p.parents] if q!=root and q.is_relative_to(root)):
        raise RuntimeError('Symlink: '+rel)
    return p
def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('manifest',type=Path)
    ap.add_argument('--apply',action='store_true')
    a=ap.parse_args();m=json.loads(a.manifest.read_text());root=Path(m['root']);snapshot=Path(m['snapshot'])
    conflicts=[];outputs={r['path']:r for r in m['outputs']}
    for r in m['sources']:
        b=safe(snapshot,r['path']);p=safe(root,r['path'])
        if not b.is_file() or digest(b)!=r['sha256']:conflicts.append({'path':r['path'],'reason':'backup_mismatch'})
        if p.exists() and r['path'] not in outputs and (not p.is_file() or digest(p)!=r['sha256']):
            conflicts.append({'path':r['path'],'reason':'new_user_content_at_original_path'})
    for r in m['outputs']:
        p=safe(root,r['path'])
        if not p.is_file() or digest(p)!=r['sha256']:conflicts.append({'path':r['path'],'reason':'output_changed_since_acceptance'})
    if conflicts:
        print(json.dumps({'status':'conflict_no_changes','conflicts':conflicts},ensure_ascii=False,indent=2));return 1
    if not a.apply:
        print(json.dumps({'status':'preview_passed','restore_sources':len(m['sources']),'batch_outputs':len(outputs)},ensure_ascii=False));return 0
    source_paths={r['path'] for r in m['sources']}
    for r in m['sources']:
        src=safe(snapshot,r['path']);dst=safe(root,r['path'])
        if dst.is_file() and digest(dst)==r['sha256']:continue
        expected=outputs.get(r['path'],{}).get('sha256')
        if dst.exists() and (expected is None or digest(dst)!=expected):raise RuntimeError('Concurrent edit: '+r['path'])
        dst.parent.mkdir(parents=True,exist_ok=True)
        if dst.exists():
            tmp=dst.with_name(dst.name+'.wwl-restore-tmp')
            with tmp.open('xb') as out:out.write(src.read_bytes())
            if digest(dst)!=expected:tmp.unlink();raise RuntimeError('Concurrent edit before restore: '+r['path'])
            os.replace(tmp,dst)
        else:
            with dst.open('xb') as out:out.write(src.read_bytes())
        os.chmod(dst,r['mode'])
        if digest(dst)!=r['sha256']:raise RuntimeError('Restore hash mismatch: '+r['path'])
    for r in reversed(m['outputs']):
        if r['path'] in source_paths:continue
        p=safe(root,r['path'])
        if not p.is_file() or digest(p)!=r['sha256']:raise RuntimeError('Concurrent output edit: '+r['path'])
        p.unlink()
    print(json.dumps({'status':'restored','manifest_retained':str(a.manifest)},ensure_ascii=False));return 0
if __name__=='__main__':raise SystemExit(main())
