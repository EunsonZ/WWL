"""A no-download PyTorch offload observation probe for an already installed torch."""

import sys
import time

try:
    import torch
except ImportError:
    print("SKIP: PyTorch is not installed in this interpreter")
    raise SystemExit(77)

if not torch.cuda.is_available():
    print("SKIP: PyTorch cannot see a CUDA device")
    raise SystemExit(77)

device = torch.device("cuda:0")
print(f"device={device}")
print(f"device-name={torch.cuda.get_device_name(device)}")
print(f"allocated-before={torch.cuda.memory_allocated(device)}")

torch.manual_seed(0)
left = torch.randn((1024, 1024), device=device)
right = torch.randn((1024, 1024), device=device)
warmup_result = left @ right  # keep first-use setup out of timed observation
torch.cuda.synchronize(device)
del warmup_result
start = time.perf_counter()
result = left @ right
torch.cuda.synchronize(device)
elapsed_ms = (time.perf_counter() - start) * 1_000
print(f"matmul-ms={elapsed_ms:.3f}")
print(f"allocated-after={torch.cuda.memory_allocated(device)}")
print(f"result-device={result.device}")
print(f"result-finite={torch.isfinite(result).all().item()}")

# A small, separate numerical check.  op/device discovery alone is not a
# correctness test, and a full 1024x1024 CPU reference is unnecessary here.
small_left = torch.randn((32, 48), dtype=torch.float32)
small_right = torch.randn((48, 24), dtype=torch.float32)
small_expected = small_left @ small_right
small_actual = small_left.to(device) @ small_right.to(device)
torch.testing.assert_close(
    small_actual.cpu(), small_expected, rtol=1e-4, atol=1e-5
)
print("reference-close=True")
