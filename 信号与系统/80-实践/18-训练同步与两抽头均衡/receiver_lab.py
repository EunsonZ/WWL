#!/usr/bin/env python3
"""Finite complex energy-coordinate receiver. No RF/ADC or continuous clock model."""
import argparse
import csv
import json
import math
import platform
import sys
from pathlib import Path
import numpy as np


def bits(s):
    return np.array([int(x) for x in s], dtype=int)


def syndrome(word, weights):
    """Consume the network lesson's seven columns of the GF(2) remainder map."""
    out = 0
    for b, w in zip(word, weights):
        if b:
            out ^= w
    return out


def encode(message, weights):
    m = bits(message)
    rem = syndrome(np.r_[m, [0, 0, 0]], weights)
    return np.r_[m, [(rem >> k) & 1 for k in [2, 1, 0]]]


def channel_matrix(h, K):
    """Full linear convolution, (K+1) x K. Keep the trailing observation."""
    H = np.zeros((K + 1, K), dtype=complex)
    j = np.arange(K)
    H[j, j], H[j + 1, j] = h[0], h[1]
    return H


def equalizer(H, lam):
    return np.linalg.solve(H.conj().T @ H + lam * np.eye(H.shape[1]), H.conj().T)


def cn(rng, shape, v):
    return math.sqrt(v / 2) * (rng.standard_normal(shape) + 1j * rng.standard_normal(shape))


def constellation(kind):
    levels = np.array([-3, -1, 3, 1])  # labels 00,01,10,11: adjacent labels differ by one bit
    if kind == '4PAM':
        return levels / math.sqrt(5), ['00', '01', '10', '11']
    if kind == 'QPSK':
        labels = [f'{x:02b}' for x in range(4)]
        return np.array([(2 * int(x[0]) - 1 + 1j * (2 * int(x[1]) - 1)) / math.sqrt(2) for x in labels]), labels
    if kind == '16QAM':
        return np.array([(i + 1j * q) / math.sqrt(10) for i in levels for q in levels]), [f'{i:02b}{q:02b}' for i in range(4) for q in range(4)]
    raise ValueError('unknown constellation')


def models(c):
    L, P, G = c['samples_per_symbol'], len(c['pilot']), c['guard_symbols']
    pulse = np.ones(L) / math.sqrt(L)
    train = np.repeat(2 * bits(c['pilot']) - 1, L) / math.sqrt(L)
    npre = max(c['delay_candidates']) + (P + 1) * L
    nall = max(c['delay_candidates']) + (P + G + 8) * L
    fs = L / c['T_s']
    n = np.arange(npre)
    bank = []
    for d in c['delay_candidates']:
        X = np.zeros((npre, 2), complex)
        for l in range(2):
            X[d + l * L:d + l * L + len(train), l] = train
        for f in c['cfo_candidates_Hz']:
            A = np.exp(2j * np.pi * f * n / fs)[:, None] * X
            bank.append((d, f, A, np.linalg.pinv(A)))
    return pulse, train, npre, nall, bank


def acquire(r, npre, bank):
    """Same observation window for every candidate. No use of true d/f in fitting."""
    y = r[:, :npre]
    total = np.sum(np.abs(y) ** 2, axis=1)
    scores = []
    channels = []
    for _, _, A, pinv in bank:
        h = y @ pinv.T
        # Orthogonal projection: min residual = ||y||² - ||A h||².
        score = total - np.sum(np.abs(h @ A.T) ** 2, axis=1)
        scores.append(score)
        channels.append(h)
    scores = np.array(scores).T
    best = np.argmin(scores, axis=1)  # fixed list order breaks exact ties
    hh = np.array(channels).transpose(1, 0, 2)[np.arange(len(y)), best]
    return best, hh, scores


def transmit(c, words, h, rng, noise_ratio):
    L, P, G = c['samples_per_symbol'], len(c['pilot']), c['guard_symbols']
    _, _, _, nall, _ = models(c)
    ns = P + G + 7
    a = np.zeros((len(words), ns))
    a[:, :P] = 2 * bits(c['pilot']) - 1
    a[:, P + G:] = 2 * words - 1
    x = np.repeat(a, L, axis=1) / math.sqrt(L)
    base = np.zeros((len(words), nall), complex)
    d = c['delay_samples']
    for l in range(2):
        base[:, d + l * L:d + l * L + x.shape[1]] += h[l] * x
    n = np.arange(nall)
    r = base * np.exp(2j * np.pi * c['cfo_Hz'] * n / (L / c['T_s']))
    r += cn(rng, r.shape, noise_ratio)
    # All arrays divided by sqrt(Eb); actual coordinates are multiplied by sqrt(Eb_J).
    return r


def extract(c, r, d, f):
    L = c['samples_per_symbol']
    start = d + (len(c['pilot']) + c['guard_symbols']) * L
    n = start + np.arange(8 * L)
    derot = r[:, n] * np.exp(-2j * np.pi * f * n / (L / c['T_s']))
    return derot.reshape(len(r), 8, L).sum(axis=2) / math.sqrt(L)


def counts(est, words, weights, attempted):
    hat = (est.real > 0).astype(int)
    e = np.any(hat != words, axis=1)
    passed = np.array([syndrome(row, weights) == 0 for row in hat])
    err = int(e.sum())
    und = int(np.sum(e & passed))
    n = len(words)
    return dict(attempted=attempted, synchronized=n, sync_failures=attempted-n,
                compared_bits=7*n, bit_errors=int(np.sum(hat != words)), frame_errors=err,
                crc_pass=int(passed.sum()), undetected_errors=und,
                BER_given_sync=float(np.sum(hat != words)/(7*n)) if n else None,
                FER_given_sync=err/n if n else None,
                undetected_per_attempt=und/attempted,
                undetected_given_sync=und/n if n else None,
                undetected_given_frame_error=und/err if err else None)


def batch_equalize(hhat, z, lam):
    H = np.zeros((len(z), 8, 7), complex)
    j = np.arange(7)
    H[:, j, j] = hhat[:, 0, None]
    H[:, j+1, j] = hhat[:, 1, None]
    Hstar = H.conj().transpose(0, 2, 1)
    return np.linalg.solve(Hstar @ H + lam*np.eye(7), (Hstar @ z[:, :, None]))[:, :, 0]


def metrics(h, K, ratio):
    H = channel_matrix(h, K)
    rows = []
    for name, lam in [('ZF', 0), ('LMMSE', ratio)]:
        W = equalizer(H, lam)
        B = W @ H - np.eye(K)
        bias = float(np.sum(np.abs(B)**2)/K)
        noise = float(ratio*np.sum(np.abs(W)**2)/K)
        rows.append(dict(K=K, equalizer=name, min_singular=float(np.linalg.svd(H, compute_uv=False)[-1]),
                         noise_gain=float(np.sum(np.abs(W)**2)/K), bias_MSE_over_Eb=bias,
                         noise_MSE_over_Eb=noise, total_MSE_over_Eb=bias+noise))
    return rows


def run(c, frames):
    pulse, train, npre, nall, bank = models(c)
    h = np.array([complex(*v) for v in c['h_re_im']]) * np.exp(1j*c['phase_rad'])
    weights = c['syndrome_weights_x6_to_x0']
    codebook = np.array([encode(f'{m:04b}', weights) for m in range(16)])
    signs = 2*codebook - 1
    out = dict(inputs=c, frames_used=frames, environment=dict(python=platform.python_version(),
          numpy=np.__version__, platform=platform.platform()),
          codebook=[''.join(map(str,row)) for row in codebook],
          code_mean=signs.mean(axis=0).tolist(), code_second_moment=(signs.T@signs/16).tolist(),
          cases=[], known_channel_metrics=[])
    fixed = encode(c['message'], weights)[None,:]
    r = transmit(c, fixed, h, np.random.default_rng(c['demo_seed']), c['demo_N0_over_Eb'])
    best, hh, scores = acquire(r, npre, bank)
    dh, fh = bank[int(best[0])][:2]
    z = extract(c, r, dh, fh)
    demo = dict(word=''.join(map(str,fixed[0])), delay_hat=int(dh), cfo_hat_Hz=float(fh),
                hhat=hh[0], true_h=h, raw=extract(c,r,0,0)[0], matched=z[0],
                ZF=batch_equalize(hh,z,0)[0], LMMSE=batch_equalize(hh,z,c['demo_N0_over_Eb'])[0],
                targets=2*fixed[0]-1, scores=scores[0], received=r[0])
    out['demo'] = demo
    # Noise-free acquisition is a deterministic contract, including absolute CFO phase indexing.
    r0 = transmit(c, fixed, h, np.random.default_rng(0), 0)
    b0, hh0, s0 = acquire(r0,npre,bank)
    d0,f0 = bank[int(b0[0])][:2]
    z0 = extract(c,r0,d0,f0)
    a0 = batch_equalize(hh0,z0,0)[0]
    out['noiseless'] = dict(delay_hat=int(d0), cfo_hat_Hz=float(f0),
           max_channel_error=float(np.max(np.abs(hh0[0]-h))),
           max_symbol_error=float(np.max(np.abs(a0-(2*fixed[0]-1)))),
           residual=float(s0[0,int(b0[0])]))
    if (d0 != c['delay_samples'] or f0 != c['cfo_Hz'] or out['noiseless']['max_symbol_error'] > 1e-10):
        raise RuntimeError('noiseless contract failed')
    for row in c['cases']:
        rng = np.random.default_rng(row['seed'])
        words = codebook[rng.integers(0,16,size=frames)]
        hc = h*row['fade']
        r = transmit(c,words,hc,rng,row['N0_over_Eb'])
        ix, hh, scores = acquire(r,npre,bank)
        dsel=np.array([bank[i][0] for i in ix]); fsel=np.array([bank[i][1] for i in ix])
        ok=(dsel==c['delay_samples']) & (fsel==c['cfo_Hz'])
        z=extract(c,r[ok],c['delay_samples'],c['cfo_Hz'])
        cr=dict(name=row['name'],N0_over_Eb=row['N0_over_Eb'],fade=row['fade'],seed=row['seed'],
                h_LS_RMSE_given_sync=float(np.sqrt(np.mean(np.abs(hh[ok]-hc)**2))) if ok.any() else None,
                results=[])
        for name,lam in [('ZF',0),('LMMSE',row['N0_over_Eb'])]:
            est=batch_equalize(hh[ok],z,lam) if ok.any() else np.empty((0,7))
            cr['results'].append(dict(equalizer=name,**counts(est,words[ok],weights,frames),
               symbol_MSE_over_Eb_given_sync=float(np.mean(np.abs(est-(2*words[ok]-1))**2)) if ok.any() else None))
        out['cases'].append(cr)
        for mr in metrics(hc,7,row['N0_over_Eb']):
            out['known_channel_metrics'].append(dict(case=row['name'],**mr))
    for K in [7,31,127]:
        for mr in metrics([1,-0.98],K,0.4):
            out['known_channel_metrics'].append(dict(case='spectral_notch',**mr))
    # Separate known-channel ensemble: validates complex noise and linear-MSE formula.
    rng=np.random.default_rng(1812026105)
    a=signs[rng.integers(0,16,size=frames)]
    H=channel_matrix(h,7); noise=cn(rng,(frames,8),0.4); z=a@H.T+noise
    out['known_channel_MC']=[]
    for mr in metrics(h,7,0.4):
        W=equalizer(H,0 if mr['equalizer']=='ZF' else 0.4)
        loss=np.mean(np.abs(z@W.T-a)**2,axis=1)
        se=float(np.std(loss,ddof=1)/math.sqrt(frames))
        empirical=float(np.mean(loss)); expected=mr['total_MSE_over_Eb']
        tol=6*se+1e-12
        if abs(empirical-expected)>tol:
            raise RuntimeError('linear-MSE diagnostic outside prespecified 6 empirical SE band')
        out['known_channel_MC'].append(dict(equalizer=mr['equalizer'],empirical_MSE=empirical,
                 expected_MSE=expected,SE=se,diagnostic_tolerance=tol))
    return out,bank


def serial(v):
    if isinstance(v,np.ndarray): return serial(v.tolist())
    if isinstance(v,complex): return [v.real,v.imag]
    if isinstance(v,dict): return {k:serial(x) for k,x in v.items()}
    if isinstance(v,(tuple,list)): return [serial(x) for x in v]
    return v


def validate(c, frames):
    if not 100 <= frames <= 50000: raise ValueError('frames must be 100..50000')
    # This is a declared finite laboratory card, with bounded numeric parameters.
    if c['samples_per_symbol'] != 4 or c['guard_symbols'] != 3: raise ValueError('card requires L=4 and guard=3')
    if not isinstance(c['pilot'],str) or len(c['pilot'])!=16 or set(c['pilot']) != {'0','1'}: raise ValueError('16-bit nonconstant pilot required')
    if not isinstance(c['message'],str) or len(c['message'])!=4 or set(c['message'])-{'0','1'}: raise ValueError('4-bit message required')
    if c['syndrome_weights_x6_to_x0'] != [5,7,6,3,4,2,1]: raise ValueError('network CRC columns fixed')
    if c['delay_candidates'] != list(range(8)): raise ValueError('delay grid fixed at 0..7')
    if c['cfo_candidates_Hz'] != list(range(-80,81,20)): raise ValueError('CFO grid fixed at -80:20:80 Hz')
    if c['delay_samples'] not in c['delay_candidates'] or c['cfo_Hz'] not in c['cfo_candidates_Hz']: raise ValueError('true delay/frequency must be in grid')
    if not isinstance(c['T_s'],(int,float)) or not math.isfinite(c['T_s']) or not 0.0005<=c['T_s']<=0.002: raise ValueError('T_s out of range')
    if not isinstance(c['Eb_J'],(int,float)) or not math.isfinite(c['Eb_J']) or not 1e-12<=c['Eb_J']<=1: raise ValueError('Eb_J out of range')
    for ratio in [c['demo_N0_over_Eb']]+[x['N0_over_Eb'] for x in c['cases']]:
        if not math.isfinite(ratio) or not 0<ratio<=5: raise ValueError('noise ratio must be (0,5]')
    for case in c['cases']:
        if not math.isfinite(case['fade']) or not 0<case['fade']<=2: raise ValueError('fade must be (0,2]')
    h=np.array(c['h_re_im'],dtype=float)
    if h.shape!=(2,2) or not np.isfinite(h).all() or not 0.05<=np.linalg.norm(h)<=3 or np.linalg.norm(h[0])<0.01: raise ValueError('nonzero two-tap channel required')
    if not math.isfinite(c['phase_rad']): raise ValueError('finite phase required')
    seeds=[c['demo_seed']]+[x['seed'] for x in c['cases']]+[1812026105]
    if any(type(x) is not int or not 0<=x<2**63 for x in seeds) or len(set(seeds))!=len(seeds): raise ValueError('distinct integer seeds required')


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--inputs',type=Path,default=Path(__file__).with_name('fixed-inputs.json'))
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--frames',type=int,default=None)
    args=p.parse_args()
    try:
        c=json.loads(args.inputs.read_text()); frames=args.frames if args.frames is not None else c['frames']
        validate(c,frames)
        if args.output.exists(): raise ValueError('output must not exist')
        out,bank=run(c,frames)
    except (ValueError,KeyError,TypeError,np.linalg.LinAlgError) as exc:
        p.error(str(exc))
    args.output.mkdir(parents=True)
    (args.output/'results.json').write_text(json.dumps(serial(out),ensure_ascii=False,indent=2,allow_nan=False)+'\n')
    with (args.output/'acquisition.csv').open('w',newline='') as f:
        w=csv.writer(f,lineterminator='\n');w.writerow(['delay_samples','CFO_Hz','residual_over_Eb'])
        for row,score in zip(bank,out['demo']['scores']): w.writerow([row[0],row[1],float(score)])
    with (args.output/'constellations.csv').open('w',newline='') as f:
        w=csv.writer(f,lineterminator='\n');w.writerow(['modulation','label','I_over_sqrtEs','Q_over_sqrtEs'])
        for name in ['4PAM','QPSK','16QAM']:
            points,labels=constellation(name)
            for z,label in zip(points,labels): w.writerow([name,label,float(z.real),float(z.imag)])
    print(json.dumps(dict(noiseless=out['noiseless'],cases=out['cases'],known_channel_MC=out['known_channel_MC']),indent=2))

if __name__=='__main__': main()
