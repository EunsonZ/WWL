"""Periodic finite-array checks of the stated infinite-grid examples."""
import cmath
import json
import math
from pathlib import Path


def ideal_lowpass_periodic(samples):
    """Keep periodic DFT bins strictly inside |omega| < pi/2."""
    n = len(samples)
    spectrum = [sum(x*cmath.exp(-2j*math.pi*k*t/n) for t,x in enumerate(samples))
                for k in range(n)]
    kept = [v if abs(k if k <= n//2 else k-n) < n/4 else 0j
            for k,v in enumerate(spectrum)]
    return [sum(v*cmath.exp(2j*math.pi*k*t/n) for k,v in enumerate(kept)).real/n
            for t in range(n)]


def calculate(config):
    n = config['period_samples']
    if type(n) is not int or n <= 0 or n % 24 or n > 240:
        raise ValueError('Use a positive multiple of 24, at most 240.')
    low = [math.cos(math.pi*t/4) for t in range(n)]
    high = [math.cos(3*math.pi*t/4) for t in range(n)]
    original = [math.cos(math.pi*t/3) for t in range(n)]
    squared = [x*x for x in original]
    prefiltered = ideal_lowpass_periodic(original)
    gains = [abs((1+cmath.exp(-1j*w))/2) for w in (math.pi/4,3*math.pi/4,math.pi)]
    return {'low_first_eight': low[:8], 'high_first_eight': high[:8],
            'low_downsampled': low[::2], 'high_downsampled': high[::2],
            'gains': gains, 'square_downsampled': squared[::2],
            'filter_square_downsampled': [x*x for x in prefiltered][::2],
            'square_filter_downsampled': ideal_lowpass_periodic(squared)[::2]}


if __name__ == '__main__':
    config=json.loads(Path(__file__).with_name('aliasing_inputs.json').read_text())
    print(json.dumps(calculate(config),indent=2))
