"""Read-only validation of the delivered layout, with exact recorded baselines."""
from pathlib import Path
import argparse,json,subprocess,sys
from links import audit_tree
from check_mirrors import check as check_mirrors

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('root',nargs='?',type=Path,default=Path(__file__).resolve().parents[3])
    ap.add_argument('--baseline',type=Path)
    a=ap.parse_args();root=a.root.resolve()
    baseline_path=a.baseline or Path(__file__).resolve().parents[1]/'artifacts/known-diagnostics.json'
    known=json.loads(baseline_path.read_text())
    audit=audit_tree(root);mirrors=check_mirrors(root)
    allowed_missing={(r['path'],r['target']) for r in known['missing']}
    allowed_mirrors={(r['path'],r['source']) for r in known['mirrors']}
    unexpected=[]
    for rule in ['missing','ambiguous','anchors','images','json','canvas','case_conflicts','fences']:
        for d in audit[rule]:
            if rule=='missing' and (d['path'],d['target']) in allowed_missing:continue
            unexpected.append({'rule':rule,**d})
    for rule in ['missing','mismatched','unparsed']:
        for d in mirrors[rule]:
            if rule=='mismatched' and (d['path'],d['source']) in allowed_mirrors:continue
            unexpected.append({'rule':'mirror_'+rule,**d})
    fmt=subprocess.run(['ruby',str(Path(__file__).with_name('check_formats.rb')),str(root)],capture_output=True,text=True,timeout=60)
    try:formats=json.loads(fmt.stdout)
    except json.JSONDecodeError:formats={'errors':[{'reason':'format_checker_failed','exit_code':fmt.returncode}]}
    unexpected.extend({'rule':'format',**x} for x in formats['errors'])
    report={'root':str(root),'status':'no_new_structure_errors' if not unexpected else 'failed',
            'link_counts':audit['counts'],'mirrors':mirrors,'formats':formats,
            'retained_diagnostics':known,'unexpected':unexpected}
    print(json.dumps(report,ensure_ascii=False,indent=2));return int(bool(unexpected))
if __name__=='__main__':raise SystemExit(main())
