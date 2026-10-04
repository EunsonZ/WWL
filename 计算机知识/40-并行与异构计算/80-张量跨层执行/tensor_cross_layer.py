"""标准库教学复算：坐标、view、线程责任、KV字节与最小编译合同。"""
from dataclasses import dataclass

def offset(index, stride):
    if len(index) != len(stride): raise ValueError("rank mismatch")
    return sum(i*s for i, s in zip(index, stride))

def thread_for(k, block=8): return divmod(k, block)
def kv_bytes(layers=2, batch=1, tokens=128, hkv=2, dh=12, itemsize=4):
    return layers * 2 * batch * tokens * hkv * dh * itemsize

@dataclass(frozen=True)
class CompileContract:
    shape: tuple; dtype: str; stride: tuple; aliases_storage: bool
    mask: str; random_seed: int | None; requires_grad: bool

def main():
    assert offset((2,3), (5,1)) == 13
    assert offset((3,2), (1,5)) == 13
    assert 13 * 4 == 52 and thread_for(13) == (1,5)
    assert thread_for(15) == (1,7) and kv_bytes() == 49152
    print("PASS offset=13 bytes=52 thread=(1,5) kv_bytes=49152")

if __name__ == "__main__": main()
