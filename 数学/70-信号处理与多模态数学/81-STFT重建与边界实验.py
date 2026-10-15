"""Finite complex STFT reconstruction lab; standard library, no import side effects."""
import cmath
import json
import math


def finite(values):
    return all(math.isfinite(complex(v).real) and math.isfinite(complex(v).imag) for v in values)


def transform(values, inverse=False):
    """Unscaled DFT; inverse divides by N. Full complex coefficients only."""
    values = [complex(v) for v in values]
    if not values or not finite(values):
        raise ValueError("nonempty finite vector required")
    n = len(values)
    sign = 1 if inverse else -1
    scale = n if inverse else 1
    return [sum(v * cmath.exp(sign * 2j * math.pi * k * r / n)
                for r, v in enumerate(values)) / scale for k in range(n)]


def stft(samples, window, starts, nfft):
    """Zero extension outside record; zero pad each frame at its right to nfft."""
    samples = [complex(v) for v in samples]
    window = list(window)
    starts = list(starts)
    if not samples or not window or not finite(samples) or not finite(window):
        raise ValueError("nonempty finite record/window required")
    if any(complex(w).imag for w in window):
        raise ValueError("real window required")
    if isinstance(nfft, bool) or not isinstance(nfft, int) or nfft < len(window):
        raise ValueError("integer nfft >= window length required")
    if not starts or any(isinstance(s, bool) or not isinstance(s, int) for s in starts):
        raise ValueError("nonempty integer starts required")
    if len(set(starts)) != len(starts):
        raise ValueError("duplicate starts rejected")
    spectra = []
    for start in starts:
        frame = [(samples[start+r] if 0 <= start+r < len(samples) else 0) * w
                 for r, w in enumerate(window)]
        spectra.append(transform(frame + [0] * (nfft-len(window))))
    return spectra


def reconstruct(spectra, window, starts, length, tolerance=1e-12):
    """Return (samples or None at uncovered points, actual finite denominator)."""
    window, starts, spectra = list(window), list(starts), list(spectra)
    if isinstance(length, bool) or not isinstance(length, int) or length <= 0:
        raise ValueError("positive record length required")
    if not window or not finite(window) or any(complex(w).imag for w in window):
        raise ValueError("nonempty finite real window required")
    if not starts or len(starts) != len(spectra) or len(set(starts)) != len(starts):
        raise ValueError("matching distinct starts and spectra required")
    if any(isinstance(s, bool) or not isinstance(s, int) for s in starts):
        raise ValueError("integer starts required")
    if not math.isfinite(tolerance) or tolerance < 0:
        raise ValueError("finite nonnegative tolerance required")
    nfft = len(spectra[0])
    if nfft < len(window) or any(len(frame) != nfft for frame in spectra):
        raise ValueError("consistent full spectra >= window length required")
    numerator, denominator = [0j] * length, [0.0] * length
    for start, spectrum in zip(starts, spectra):
        frame = transform(spectrum, inverse=True)
        for r, w in enumerate(window):
            index = start+r
            if 0 <= index < length:
                w = float(complex(w).real)
                numerator[index] += frame[r] * w
                denominator[index] += w*w
    return ([a/d if d > tolerance else None for a, d in zip(numerator, denominator)],
            denominator)


def error(restored, original):
    return max((abs(a-b) for a, b in zip(restored, original) if a is not None), default=0.0)


def run_checks():
    # Independent closed form DFT of the index-one impulse: exp(-2 pi i k / 4).
    impulse = [0, 1, 0, 0]
    assert max(abs(a-b) for a, b in zip(transform(impulse), [1, -1j, -1, 1j])) < 1e-14
    # Independent inverse of the constant spectrum is the index-zero impulse.
    assert max(abs(a-b) for a, b in zip(transform([1]*4, True), [1, 0, 0, 0])) < 1e-14
    x, w = list(range(1, 9)), [0, 0.5, 1, 0.5]  # periodic Hann L=4
    starts = [0, 2, 4]
    spectra = stft(x, w, starts, 8)
    result, d = reconstruct(spectra, w, starts, 8)
    # Hand-computed oracle independent of the reconstruction function.
    assert d == [0, 0.25, 1, 0.5, 1, 0.5, 1, 0.25]
    assert result[0] is None and error(result, x) < 1e-12
    # Negative start is a real boundary policy; restore all original indices 0..7.
    padded_starts = [-2, 0, 2, 4, 6]
    full, full_d = reconstruct(stft(x, w, padded_starts, 8), w, padded_starts, 8)
    assert full_d == [1, 0.5, 1, 0.5, 1, 0.5, 1, 0.5]
    assert all(v is not None for v in full) and error(full, x) < 1e-12
    # Dropping middle frame: index 4 loses its only nonzero weight.
    dropped, dropped_d = reconstruct([spectra[0], spectra[2]], w, [0, 4], 8)
    assert dropped_d[4] == 0 and dropped[4] is None
    # Dropping phase fails even when coverage remains positive.
    phase_lost = [[abs(z) for z in frame] for frame in stft(x, w, padded_starts, 8)]
    phase_result, _ = reconstruct(phase_lost, w, padded_starts, 8)
    phase_error = error(phase_result, x)
    assert phase_error > 1
    invalid_checks = 0
    for call in (lambda: transform([]), lambda: transform([float('nan')]),
                 lambda: stft(x, w, [0], 3), lambda: stft(x, w, [0, 0], 8),
                 lambda: stft(x, [1j], [0], 8),
                 lambda: reconstruct(spectra, w, starts, 0),
                 lambda: reconstruct(spectra, w, starts, 8, -1),
                 lambda: reconstruct([spectra[0][:-1], spectra[1]], w, [0, 2], 8)):
        try:
            call()
        except ValueError:
            invalid_checks += 1
        else:
            raise AssertionError("invalid input accepted")
    return {"unextended_recoverable_indices": [1, 7], "unextended_denominator": d,
            "extended_recoverable_indices": [0, 7], "extended_denominator": full_d,
            "unextended_max_error": error(result, x), "extended_max_error": error(full, x),
            "dropped_frame_zero_indices": [i for i, a in enumerate(dropped) if a is None],
            "phase_lost_max_error": phase_error, "invalid_cases_rejected": invalid_checks,
            "fixed_fs_nfft_bin_hz": 16000/512}


if __name__ == "__main__":
    print(json.dumps(run_checks(), indent=2, ensure_ascii=False))
