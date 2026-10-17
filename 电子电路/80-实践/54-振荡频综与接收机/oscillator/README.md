# Finite cross-coupled NMOS LC oscillator evidence

Five actual ngspice47 cases use the fixed-inputs.json educational LEVEL1 card; no PDK or hardware is claimed.
Each side is VDD→10ohm→100nH→drain,25pF to ground, cross gate to opposite drain, NMOS body0,
ideal tail2mA. TEMP/TNOM27C; Meyer intrinsic capacitance retained, no explicit transistor noise in transient.
A 1mV differential seed is split ±0.5mV around exact analytical Q; inductors start at tail/2.
Default all five2us Gear2 runs use10ps maxstep, refinement5ps. Command/actual exit/log per case retained;
completion checked log for aborted analysis even when CLI exits0. Startup is finite, not stochastic.

Default actual Q is dp=dn1.78999999997V, source.97631434827V, each Id1.000000003mA,
gm6.37580964mS/gds19.6797uS, intrinsic Cgs11.51048fF/cgd,cgb0.
Approximate differential active conductance(gds−gm)/2≈−3.178mS versus tank1/(2Rp)=1.25mS,
Rp≈L/(Rs*C)=400ohm. This is an approximate high-Q small-signal test, not an exact pole certificate.
Lossless1/(2πsqrt(LC))≈100.658MHz; actual nonlinear finite oscillation99.231840MHz.
Actual tail/rail power mean3.600000mW. Final device-current switching and triode entry provide nonlinear
amplitude regulation in the model. Saturated-pair small-signal formulas do not describe the full cycle.

Zero explicit seed ALSO starts in this numerical solver. Exact symmetry is an invariant of ideal equations,
but floating-point numerical perturbations are not a physical noise model; no measured startup distribution follows.
Lowtail1uA with the same1mV seed decays (late peak2.31e−13V); C30p lowers frequency90.368894MHz.
Default5ps refinement changes late frequency about9.55ppm and peak0.415ppm. These are finite time-step
comparisons, not a universal convergence proof. No phase-noise/PSS/PSD or device silicon result is claimed.
Physical phase-noise work needs an actual stochastic/PSS model, explicit noise source/bias/PSD conventions,
validated process data and separate output evidence; deterministic FFT alone is insufficient.

Reader evidence is this directory only (finite compact package). The process parent holds pilot failure and full text gzip;
do not integrate that process tree. Per case interface.json gives original full text SHA/columns and compact
selection hashes. startup.csv.gz retains every actual row0..200ns; late.csv.gz retains every actual row1..2us including supply current for complete late power recomputation,
no uniform resampling or decimation. 200ns..1us is omitted from reader samples, retained in parent full gzip;
summary startup bins are derived from full output. device-cycle.csv.gz retains all original columns for the last
whole positive-zero-crossing cycle with actual bracketing samples (low-tail uses last100ns, no cycle asserted).
summary.json records full-run results; recomputed-final.json is actual independent compact-file processing.
Device-region fractions in summary use20 late cycles, recomputed uses the selected one cycle: do not demand
bitwise equality of those fractions. Frequency/peak/CM/power use the identical full late window and must agree.

Recompute with numpy: python recompute.py --output NEW.json (fresh output, broken symlinks rejected).
To regenerate simulations in an isolated copy: set NGSPICE to actual CLI and WWL_RUNNER to run_local.py;
python generate.py; python run.py; python analyze.py. Each SPICE process uses shared two-slot runner/thread1.
Analysis archives full waveform.txt into per-case waveform.txt.gz outside any copied reader-only publication.
Use a fresh work directory. Packaged generate/run inputs were path/card parameterized after execution and AST
checked only; original successful argv remains in each command.json. No additional numerical run was hidden.
