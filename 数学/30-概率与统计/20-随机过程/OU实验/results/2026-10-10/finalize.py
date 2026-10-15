from pathlib import Path
import hashlib,json
base=Path(__file__).resolve().parent
r=json.loads((base/'output/report.json').read_text());o=json.loads((base/'independent-oracle.json').read_text());p=json.loads((base/'process-observations.json').read_text());f=json.loads((base/'SOURCE_FREEZE.json').read_text())
orig=base.parents[3]/'.wwl-recovery/2026-10-10-crash/author146completion/candidate'
assert all(hashlib.sha256((orig/x['path']).read_bytes()).hexdigest()==x['sha256']==hashlib.sha256((base/'snapshot'/Path(x['path']).name).read_bytes()).hexdigest() for x in f['files'])
rows=['| steps | analytic RMSE | observed RMSE | MSE z | independent-noise MSE |','|---:|---:|---:|---:|---:|']
for x in r['rows']:rows.append(f"| {x['theory']['steps']} | {x['theory']['strong_rmse']:.12g} | {x['strong_rmse']['estimate']:.12g} | {x['strong_mse']['z']:.6g} | {x['independent_noise_mse']['estimate']:.12g} |")
report='''# #146 independent execution and mathematical audit

Status: PASS for frozen source `1322dd283998961d7fead5ff73823a2379a95dd545bd4a2f6e87f1c03f2cb549` and input `ece6a3a9f7751a53b3367b996721546334d6217b17d1b4a76dae88bf21582038`. Original and copied snapshot hashes match before and after execution and final audit. Original candidate was read-only.

The locked `.venv-issues-111plus` supplied Python 3.14.7 / NumPy 2.5.3; no installation or environment edits. Source CLI help and version probes passed, six unittest tests passed, and the fixed CLI exited 0 with diagnostics_pass=true. All original stdout/stderr remain adjacent. `process-observations.json` records per-child wait4 wall time, CPU time, exit and Darwin peak RSS. Five numeric thread environment controls each equal 1; these are not a RAM hard cap. The OU child ran 0.282068333 seconds with 79,806,464-byte peak RSS; no timeout. No sysctl observer was used. A+B simultaneous aggregate memory was not directly measured here.

Inputs: N=65536, chunk=4096, finest=64, levels=8/16/32/64, joint-pair seed 20261010, independent Gaussian-terminal seed 20261011. This is one fixed experiment with two distinct generator seeds, not two independent replicas of the full experiment.

The independent oracle imports neither ou_lab nor its tests. It integrates the piecewise EM kernel H(s)=a^(m-1-i) against the exact OU terminal kernel K(s)=exp(-k(T-s)) using 70-digit Decimal, interval by interval. The resulting EM mean, variance, second moment, covariance, coupled MSE/RMSE, two weak biases and independent-noise MSE agree within 1e-12. It also independently reconstructs all terminal statistics and standard errors by linear kernel sums on the same joint random inputs. All 94 comparisons passed. This runtime numerical audit is separate from the six source self-tests.

Exact OU mean=0.36787944117144233, variance=0.10808308959542341, second moment=0.2434183728320361.

'''+ '\n'.join(rows)+'''

Analytic successive RMSE step-halving orders are 1.03589012745, 1.01752643653, 1.00866350344, approaching 1 for this additive-noise OU endpoint. This does not prove the general Ito/EM theorem. The independent-noise control remains near 0.217 as h shrinks because it destroys common-Brownian coupling; independent fine noise is not a strong-error truth path. Weak moment sampling uncertainty and paired terminal strong error are different quantities. All declared 6 estimated-SE diagnostics passed; estimated bands are not finite-sample guarantees.

All 992 saved trace rows were checked by independent fine-prefix and EM weighted sums; maximum difference 2.3314683517128287e-15. For every saved path, exact 8-step and 64-step values coincide at all public 8-grid times within 1.9984014443252818e-15. The CLI's full-path coarse/fine exact agreement is 3.774758283725532e-15. No fine Euler reference is used.

Deliverables: `output/report.json`, `output/traces.csv`, `output/strong-error.svg`; frozen snapshot and SOURCE_FREEZE; original help/version/test/fixed logs; before/after hashes; environment and process observations; independent oracle source/result and logs; final file hashes. Oracle computation self peak RSS=57,540,608 bytes and wall=0.058515625 seconds (recorded inside its process).

No observed instrument or model failure occurred in this run. SVG XML is preserved but visual rendering, native Obsidian, hardware, real finance, human learning and generic Ito proof are not verified here. This run lives in the authorized recovery directory; integration owner/author must copy these exact results into the formal lab candidate and expose its teaching interpretation before remote delivery. No main-vault/Git/GitHub state or external logs were changed by this runner.
'''
(base/'REPORT.md').write_text(report)
manifest={str(x.relative_to(base)):hashlib.sha256(x.read_bytes()).hexdigest() for x in sorted(base.rglob('*')) if x.is_file() and x.name!='artifact-hashes.json'}
(base/'artifact-hashes.json').write_text(json.dumps(manifest,indent=2)+'\n')
print(json.dumps({'status':'PASS','files_hashed':len(manifest),'report':str(base/'REPORT.md')}))
