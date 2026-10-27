"""Minimal Triton JIT probe: triggers the cuda_utils.c gcc build with full stderr."""
import torch
import triton
import triton.language as tl

print("triton", triton.__version__, "| torch", torch.__version__)


@triton.jit
def add_kernel(x_ptr, y_ptr, out_ptr, n, BLOCK: tl.constexpr):
    pid = tl.program_id(0)
    offs = pid * BLOCK + tl.arange(0, BLOCK)
    mask = offs < n
    tl.store(out_ptr + offs,
             tl.load(x_ptr + offs, mask=mask) + tl.load(y_ptr + offs, mask=mask),
             mask=mask)


x = torch.randn(1024, device="cuda")
y = torch.randn(1024, device="cuda")
out = torch.empty_like(x)
add_kernel[(1,)](x, y, out, 1024, BLOCK=1024)
print("triton kernel ok; err =", (out - x - y).abs().max().item())
