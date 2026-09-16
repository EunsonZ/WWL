---
type: practice
domain: artificial-intelligence
stage: 4
status: ready
difficulty: 进阶
estimated_minutes: 90
verified: 2026-09-01
topics:
  - safetensors
  - gguf
  - quantization
  - llama-cpp
  - reproducibility
tags:
  - ai/practice
  - ai/llm/formats
  - ai/llm/quantization
---

# safetensors 到 GGUF 与量化

<!-- deep-review-02 -->
> [!tip] 本轮深化：从当前概念继续追问
> 本轮[[AI/80-实践/08-深层机制数值实验/00-数值实验导航与验收|42 项深层机制测试]]补充梯度、概率、缓存与训练状态验证；它与本页实验解决不同层的问题。先读[[AI/20-LLM/80-研究拓展/03-从论文主张到可复现实验|验证层级]]，不要把算子测试成功登记成真实模型或部署验收。


## 本实践做什么，以及尚未做什么

目标是建立一条可审计的部署转换证据链：**可信、固定的模型 revision 与哈希** → `config`、tokenizer、safetensors 的相容性 → **固定 commit** 的转换器 → GGUF 结构验证 → 量化候选 → 固定 `llama.cpp` 的最小加载 → 在同一条件下比较文件大小、内存、速度和质量。

本目录没有权重、下载脚本、访问令牌、模型缓存或真实转换产物。已实际运行的只是同目录的标准库玩具程序：它构造 176 字节的受限 GGUF v3 fixture，验证 header、metadata、tensor info、对齐与边界，并检查一个教学用对称 INT4 网格的误差；它**不是**通用 GGUF 解析器、safetensors 读取器或模型转换器。因此，本页不声称任何真实模型已转换、量化、加载或评测。

先修：[[AI/20-LLM/60-模型格式与量化/00-模型格式与量化-MOC|模型格式与量化 MOC]]、[[AI/20-LLM/50-实现/04-llama.cpp构建后端与调用链|llama.cpp 构建、后端与调用链]]、[[数学/60-数值计算与量化/02-量化Scale-Zero-Point-Group与误差|量化、Scale、Zero-Point、Group 与误差]]。版本与一手资料入口是 [[AI/90-资源/05-官方资料与版本核验记录|官方资料与版本核验记录]]。

## 先分清三层，再谈“4-bit”

| 层 | 负责什么 | 常见对象 | 不应由它证明什么 |
| --- | --- | --- | --- |
| 文本表示 | 字符/字节如何成为 token ID | UTF-8、normalizer、tokenizer、special token、chat template | 权重是否正确、量化是否正确 |
| 容器与序列化 | 张量和元数据怎样放进文件 | `config.json`、safetensors、GGUF、分片索引 | token ID 语义、量化质量、许可 |
| 数值表示 | 每个权重怎样近似存储/恢复 | F16、BF16、INT8、NF4、GPTQ、AWQ、GGUF quant type | 模型身份、容器完整性、推理必然更快 |

`safetensors → GGUF` 主要是**架构感知的容器/布局映射**；GGUF 再转 `Q4_0`、`Q4_K_M` 或 `Q8_0` 时才显著涉及数值表示。即使权重数值没变，遗漏 tokenizer 或 chat template 也会让同一文字输入变成不同 token；即使文件都能加载，也不能由此推出回答质量、许可证或安全性已通过。

### NF4、GPTQ、AWQ、GGUF 与 K-quants 不是一组同义词

| 名称 | 主要层/性质 | 正确理解 | 不能简化成 |
| --- | --- | --- | --- |
| NF4 | 数值编码 | 面向近似正态分布权重的 4-bit 代码表，常见于 QLoRA 的低比特底座存储 | 任意 GGUF 的“普通 4-bit” |
| GPTQ | PTQ 方法/实现布局 | 用近似二阶信息或逐层误差最小化来决定低比特权重表示；具体 pack 格式取决于实现 | 一个通用容器格式 |
| AWQ | activation-aware PTQ 方法 | 利用激活统计来保护重要通道或选择 scale；需要说明校准数据、实现与配置 | 自动保证所有任务质量 |
| GGUF | 容器格式 | 可携带 metadata、词表字段、tensor info、对齐后的 tensor bytes；每个张量可有不同 ggml 类型 | 量化算法或模型来源证明 |
| K-quants / `Q4_K_M` | ggml/GGUF 生态量化类型与混合预设 | K-block 量化使用块内辅助参数；`_M` 是混合张量类型预设，实际 tensor type 和可用标签必须按固定工具版本读取 | “所有权重都是同一种 4-bit” |

位宽不是总大小，也不是质量结论：分组参数、scale/min、少量保持高精度的张量、对齐、KV cache、计算 buffer、mmap/page cache 和后端都会改变观察值。误差的定义、分组和离群值影响回到 [[数学/60-数值计算与量化/80-量化误差实验|量化误差实验]]；不要把这页的玩具 INT4 结果外推成 NF4、GPTQ、AWQ 或 K-quants 的质量证据。

## 0. 每次真实运行先建身份清单

从同目录的 [run-manifest.template.json](run-manifest.template.json) 复制出一份**位于 Vault/Git 之外**的新 manifest；将其状态从 `template-not-run` 改成真实状态前，填完下列不可互相替代的证据。模板故意不含真实路径、下载 URL 参数、提示词或权重。

1. **来源与授权：** 发布者、模型仓库 ID、不可变 revision（不能写浮动的 `main`）、模型卡 URL、权重许可证与使用条款。工具代码许可证和权重许可证分别记录。
2. **每个输入字节：** safetensors 全部分片、分片 index、`config.json`、tokenizer 文件、聊天模板来源，均记录相对名称、字节数与 SHA-256。摘要须从可信发布者或你亲自保存的同一 revision 清单获得；“算出了哈希”不自动建立信任。
3. **三方相容性：** `config` 的 architecture/layers/hidden size/heads/vocab size；safetensors 分片索引中各 tensor name 与 shape；tokenizer 的 vocab、added/special token ID、normalizer 和 chat template。任意一项没有证据就停止，不用“转换试一下”代替检查。
4. **工具与环境：** `llama.cpp` 的远端、40 位 commit、转换器 `--help` 输出、运行时二进制版本、OS、CPU、内存、GPU、driver/runtime。分支名、网页说明和“最新版”不是固定 commit。

> [!warning] 不可信文件边界
> 不要为看键名而反序列化不可信 pickle checkpoint。safetensors/GGUF 没有 pickle 的任意对象图，并不表示文件可信：仍可能有伪造 metadata、异常 shape/offset、资源耗尽、恶意模型行为或不兼容许可证。真实运行应在无密钥、无私人数据、可设磁盘/内存上限且默认无网络的可恢复环境中进行。

## 1. 真实转换的防覆盖门禁（模板，未在本机执行）

以下是**先填空、后执行**的 shell 模板。所有变量初值为空；任一个为空、源目录不存在、磁盘余量不足、固定 commit 不匹配，或任一输出路径已存在，脚本立即拒绝继续。它只允许创建新的派生目录，不改写原始 safetensors。转换器具体入口、参数、支持架构和量化标签随 commit 改变，必须以该 commit 的 `--help` 和上游文档为准后填入 manifest，不能照抄猜测参数。

<!-- code-sync: ./preflight.template.sh -->
```bash
#!/usr/bin/env bash
# Fill every empty variable after consulting the fixed llama.cpp commit. This
# template only records provenance and refuses unsafe preconditions; it does
# not download, convert, quantize, compile, or overwrite files.
set -euo pipefail

RUN_ROOT="${RUN_ROOT:-}"             # Example: /Volumes/ExternalSSD/llm-runs/2026-09-01-example
SOURCE_DIR="${SOURCE_DIR:-}"         # Read-only model directory with checked provenance
LLAMA_CPP_DIR="${LLAMA_CPP_DIR:-}"   # Existing fixed llama.cpp checkout
LLAMA_CPP_COMMIT="${LLAMA_CPP_COMMIT:-}" # Exactly 40 lowercase hexadecimal characters
REQUIRED_KIB="${REQUIRED_KIB:-}"     # Conservative source + outputs + reserve total
HIGH_GGUF="${HIGH_GGUF:-}"
QUANT_GGUF="${QUANT_GGUF:-}"

require_nonempty() { test -n "$2" || { echo "missing $1" >&2; exit 2; }; }
require_nonempty RUN_ROOT "$RUN_ROOT"
require_nonempty SOURCE_DIR "$SOURCE_DIR"
require_nonempty LLAMA_CPP_DIR "$LLAMA_CPP_DIR"
require_nonempty LLAMA_CPP_COMMIT "$LLAMA_CPP_COMMIT"
require_nonempty REQUIRED_KIB "$REQUIRED_KIB"
require_nonempty HIGH_GGUF "$HIGH_GGUF"
require_nonempty QUANT_GGUF "$QUANT_GGUF"

test -d "$RUN_ROOT" && test -d "$RUN_ROOT/out" && test -d "$SOURCE_DIR" && test -d "$LLAMA_CPP_DIR" || {
  echo "run root, source, or fixed checkout does not exist" >&2; exit 2;
}
for path in "$RUN_ROOT" "$RUN_ROOT/out" "$SOURCE_DIR" "$LLAMA_CPP_DIR"; do
  test ! -L "$path" || { echo "directory must not be a symlink: $path" >&2; exit 2; }
done
canonical_dir() { (cd -P -- "$1" && pwd -P); }
path_is_within() { case "$1/" in "$2/"*) return 0 ;; *) return 1 ;; esac; }
canonical_new_file() {
  test "${1#/}" != "$1" || { echo "output path must be absolute: $1" >&2; exit 2; }
  parent="$(canonical_dir "$(dirname -- "$1")")"
  name="$(basename -- "$1")"
  test "$name" != "." && test "$name" != ".." || { echo "invalid output filename" >&2; exit 2; }
  printf '%s/%s\n' "$parent" "$name"
}
RUN_ROOT="$(canonical_dir "$RUN_ROOT")"
OUT_DIR="$(canonical_dir "$RUN_ROOT/out")"
SOURCE_DIR="$(canonical_dir "$SOURCE_DIR")"
LLAMA_CPP_DIR="$(canonical_dir "$LLAMA_CPP_DIR")"
HIGH_GGUF="$(canonical_new_file "$HIGH_GGUF")"
QUANT_GGUF="$(canonical_new_file "$QUANT_GGUF")"
SOURCE_HASHES="$RUN_ROOT/source-sha256.txt"
COMMIT_RECORD="$RUN_ROOT/llama-cpp-commit.txt"

for pair in "$RUN_ROOT|$SOURCE_DIR" "$RUN_ROOT|$LLAMA_CPP_DIR" "$SOURCE_DIR|$LLAMA_CPP_DIR"; do
  left="${pair%%|*}"; right="${pair#*|}"
  if path_is_within "$left" "$right" || path_is_within "$right" "$left"; then
    echo "run root, source, and fixed checkout must not overlap" >&2; exit 2
  fi
done
test "$HIGH_GGUF" != "$QUANT_GGUF" || { echo "output files must be distinct" >&2; exit 2; }
test "$(dirname -- "$HIGH_GGUF")" = "$OUT_DIR" || { echo "high-precision output must be directly under RUN_ROOT/out" >&2; exit 2; }
test "$(dirname -- "$QUANT_GGUF")" = "$OUT_DIR" || { echo "quantized output must be directly under RUN_ROOT/out" >&2; exit 2; }
printf '%s' "$REQUIRED_KIB" | grep -Eq '^[1-9][0-9]*$' || { echo "REQUIRED_KIB must be a positive integer" >&2; exit 2; }
test -f "$SOURCE_DIR/config.json" || { echo "source is missing config.json" >&2; exit 2; }
find "$SOURCE_DIR" -maxdepth 1 -type l -print -quit | grep -q . && {
  echo "source directory must not contain symlinked top-level inputs" >&2; exit 2;
}
find "$SOURCE_DIR" -maxdepth 1 -type f -name '*.safetensors' -print -quit | grep -q . || {
  echo "source has no safetensors shard" >&2; exit 2;
}
find "$SOURCE_DIR" -maxdepth 1 -type f \( -name tokenizer.json -o -name tokenizer.model -o -name vocab.json \) -print -quit | grep -q . || {
  echo "source has no recognized tokenizer file" >&2; exit 2;
}
test "${#LLAMA_CPP_COMMIT}" -eq 40 && printf '%s' "$LLAMA_CPP_COMMIT" | grep -Eq '^[0-9a-f]{40}$' || {
  echo "commit must be exactly 40 lowercase hexadecimal characters" >&2; exit 2;
}
test "$(git -C "$LLAMA_CPP_DIR" rev-parse HEAD)" = "$LLAMA_CPP_COMMIT" || {
  echo "llama.cpp HEAD differs from the manifest" >&2; exit 2;
}
test -z "$(git -C "$LLAMA_CPP_DIR" status --porcelain)" || {
  echo "fixed checkout has uncommitted changes" >&2; exit 2;
}
test ! -e "$HIGH_GGUF" && test ! -L "$HIGH_GGUF" || { echo "refusing to overwrite high-precision GGUF" >&2; exit 2; }
test ! -e "$QUANT_GGUF" && test ! -L "$QUANT_GGUF" || { echo "refusing to overwrite quantized GGUF" >&2; exit 2; }
test ! -e "$SOURCE_HASHES" && test ! -L "$SOURCE_HASHES" || { echo "refusing to overwrite source hash record" >&2; exit 2; }
test ! -e "$COMMIT_RECORD" && test ! -L "$COMMIT_RECORD" || { echo "refusing to overwrite commit record" >&2; exit 2; }
AVAILABLE_KIB="$(df -Pk "$RUN_ROOT" | awk 'NR == 2 { print $4 }')"
test "$AVAILABLE_KIB" -ge "$REQUIRED_KIB" || { echo "insufficient disk space" >&2; exit 2; }

find "$SOURCE_DIR" -maxdepth 1 -type f -print0 | sort -z | xargs -0 shasum -a 256 > "$SOURCE_HASHES"
git -C "$LLAMA_CPP_DIR" rev-parse HEAD > "$COMMIT_RECORD"
```

对应的负向测试只在临时目录中创建极小假输入和一个假的只读 `git` 查询入口；它不下载、编译、转换或量化任何模型，并确认符号链接目录与目录重叠会被拒绝。

<!-- code-sync: ./test_preflight.py -->
```python
"""Negative-path tests for the conversion preflight; no conversion is run."""
from __future__ import annotations

import os
import subprocess
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).with_name("preflight.template.sh")
COMMIT = "0123456789abcdef0123456789abcdef01234567"


class PreflightTests(unittest.TestCase):
    def make_fixture(self, base: Path, *, overlap: bool = False, symlink_out: bool = False) -> dict[str, str]:
        run = base / "run"
        source = run / "source" if overlap else base / "source"
        checkout = base / "llama.cpp"
        bin_dir = base / "bin"
        run.mkdir()
        if symlink_out:
            real_out = base / "real-out"
            real_out.mkdir()
            (run / "out").symlink_to(real_out, target_is_directory=True)
        else:
            (run / "out").mkdir()
        source.mkdir()
        checkout.mkdir()
        bin_dir.mkdir()
        (source / "config.json").write_text("{}\n", encoding="utf-8")
        (source / "weights.safetensors").write_bytes(b"safe-fixture")
        (source / "tokenizer.json").write_text("{}\n", encoding="utf-8")
        fake_git = bin_dir / "git"
        fake_git.write_text(
            "#!/bin/sh\ncase \"$*\" in\n*'rev-parse HEAD'*) echo '" + COMMIT + "' ;;\n"
            "*'status --porcelain'*) exit 0 ;;\n*) exit 2 ;;\nesac\n",
            encoding="utf-8",
        )
        fake_git.chmod(0o755)
        return {
            **os.environ,
            "PATH": f"{bin_dir}{os.pathsep}{os.environ['PATH']}",
            "RUN_ROOT": str(run),
            "SOURCE_DIR": str(source),
            "LLAMA_CPP_DIR": str(checkout),
            "LLAMA_CPP_COMMIT": COMMIT,
            "REQUIRED_KIB": "1",
            "HIGH_GGUF": str(run / "out" / "model-f16.gguf"),
            "QUANT_GGUF": str(run / "out" / "model-q4.gguf"),
        }

    def run_preflight(self, env: dict[str, str]) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["bash", str(SCRIPT)], env=env, text=True, capture_output=True, check=False
        )

    def test_valid_isolated_directories_record_provenance_only(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            env = self.make_fixture(Path(temporary))
            result = self.run_preflight(env)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue((Path(env["RUN_ROOT"]) / "source-sha256.txt").is_file())
            self.assertTrue((Path(env["RUN_ROOT"]) / "llama-cpp-commit.txt").is_file())
            self.assertFalse(Path(env["HIGH_GGUF"]).exists())

    def test_symlinked_output_directory_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            env = self.make_fixture(Path(temporary), symlink_out=True)
            result = self.run_preflight(env)
            self.assertEqual(result.returncode, 2)
            self.assertIn("must not be a symlink", result.stderr)

    def test_run_root_and_source_overlap_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            env = self.make_fixture(Path(temporary), overlap=True)
            result = self.run_preflight(env)
            self.assertEqual(result.returncode, 2)
            self.assertIn("must not overlap", result.stderr)


if __name__ == "__main__":
    unittest.main()
```

这里的 shell 模板有意不包含下载、`git clone`、编译或转换命令。先从固定 checkout 阅读转换器的 `--help`，把**实际命令、实际输入目录、输出名称、量化 label 和工具输出**写进外部 manifest；然后用该 commit 所支持的转换器生成一个新的高精度 GGUF，再只从它生成新的量化 GGUF。高精度 GGUF 与量化 GGUF 都要各自重新计算 SHA-256，且 `derived_from_sha256` 必须指向刚验证过的高精度文件，而非模糊的模型名。

### 转换与 GGUF 验收顺序

1. 转换前：确认 config、tokenizer、chat template、所有 safetensors 分片与索引同属一个 immutable revision；保存每个输入的哈希和字节数。
2. 在固定 `llama.cpp` commit 上生成新的高精度 GGUF。不要把输入扩展名改为 `.gguf`，不要就地覆盖任何分片。
3. 对高精度 GGUF 用同一 commit 的 info/inspect 能力做结构检查：magic/version、metadata 中的 architecture/context/tokenizer 相关字段、tensor count、每个关键 tensor 的名称/shape/type、数据区对齐和每个 offset/length 都在文件范围内。解析成功只是结构证据，不能单独证明张量数值或模型语义。
4. 从验证过的高精度 GGUF 生成候选量化（例如当前 commit 真实支持的 `Q8_0`、`Q4_0` 与某个 K-quant）；记录每个输出实际 tensor type 分布，不能只记录文件名标签。
5. 用相同固定 commit 的 `llama.cpp` 运行时分别作最小本地加载和固定提示集生成。加载成功后仍须继续比较质量与资源；量化和运行时错误应记录为失败证据，不要删除高精度基线掩盖失败。

## 2. 实际可运行：受限 toy GGUF 与 INT4 误差

这个小程序只用标准库，默认不写文件、不联网、不读真实模型。它自行构造一个固定的 GGUF v3 bytes，严格限制为两个 metadata 类型、一个 F32 tensor、1 MiB 上限、有限 tensor/字符串数与对齐范围。解析器拒绝截断、错误 magic/version、未知元数据类型、重叠或越界 tensor range。`--write` 也只会写入一个**尚不存在**且父目录已存在的指定路径。

运行：

```bash
python3 -B gguf_toy_validator.py
python3 -B test_gguf_toy_validator.py
```

本次实际输出：`toy GGUF: 176 bytes; data starts at byte 160`，metadata 为 `general.architecture=toy` 与 `general.alignment=32`；教学 INT4 的 `scale=0.178571`、`MAE=0.044643`、`max_abs=0.071429`。测试还主动篡改 magic、version、截断字节和 tensor offset，全部被拒绝。它没有读取、转换或量化任何真实权重。

<!-- code-sync: ./gguf_toy_validator.py -->
```python
#!/usr/bin/env python3
"""Build and validate a deliberately tiny, safe subset of a GGUF file.

This is a format-learning fixture, not a model converter or a general GGUF
loader.  It accepts only the exact subset written by ``build_toy_gguf``:
GGUF v3, two known metadata value types, and F32 tensors.  Its bounded parser
is intentionally useful for checking header, metadata, tensor offsets, and
alignment without downloading or opening a real model.
"""

from __future__ import annotations

import argparse
import math
import struct
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Final


MAGIC: Final[bytes] = b"GGUF"
VERSION: Final[int] = 3
VALUE_TYPE_UINT32: Final[int] = 4
VALUE_TYPE_STRING: Final[int] = 8
GGML_TYPE_F32: Final[int] = 0
MAX_FILE_BYTES: Final[int] = 1 << 20
MAX_COUNT: Final[int] = 32
MAX_STRING_BYTES: Final[int] = 4096


class FormatError(ValueError):
    """Raised when a fixture violates this teaching parser's strict subset."""


@dataclass(frozen=True)
class TensorInfo:
    name: str
    shape: tuple[int, ...]
    ggml_type: int
    offset: int
    byte_length: int


@dataclass(frozen=True)
class ToyGguf:
    version: int
    metadata: dict[str, int | str]
    tensors: tuple[TensorInfo, ...]
    data_offset: int
    byte_length: int


class Reader:
    """A length-bounded little-endian reader with explicit size limits."""

    def __init__(self, payload: bytes) -> None:
        if len(payload) > MAX_FILE_BYTES:
            raise FormatError(f"fixture exceeds {MAX_FILE_BYTES} bytes")
        self.payload = payload
        self.position = 0

    def take(self, size: int) -> bytes:
        if size < 0 or self.position + size > len(self.payload):
            raise FormatError("truncated field")
        result = self.payload[self.position : self.position + size]
        self.position += size
        return result

    def u32(self) -> int:
        return struct.unpack("<I", self.take(4))[0]

    def u64(self) -> int:
        return struct.unpack("<Q", self.take(8))[0]

    def string(self) -> str:
        size = self.u64()
        if size > MAX_STRING_BYTES:
            raise FormatError(f"string is larger than {MAX_STRING_BYTES} bytes")
        try:
            return self.take(size).decode("utf-8")
        except UnicodeDecodeError as error:
            raise FormatError("string is not valid UTF-8") from error


def append_string(buffer: bytearray, value: str) -> None:
    encoded = value.encode("utf-8")
    buffer.extend(struct.pack("<Q", len(encoded)))
    buffer.extend(encoded)


def append_metadata_string(buffer: bytearray, key: str, value: str) -> None:
    append_string(buffer, key)
    buffer.extend(struct.pack("<I", VALUE_TYPE_STRING))
    append_string(buffer, value)


def append_metadata_u32(buffer: bytearray, key: str, value: int) -> None:
    append_string(buffer, key)
    buffer.extend(struct.pack("<I", VALUE_TYPE_UINT32))
    buffer.extend(struct.pack("<I", value))


def align_up(value: int, alignment: int) -> int:
    if alignment < 8 or alignment > 4096 or alignment & (alignment - 1):
        raise ValueError("alignment must be a power of two from 8 through 4096")
    return (value + alignment - 1) & -alignment


def build_toy_gguf() -> bytes:
    """Return one deterministic, valid-for-this-lesson GGUF v3 byte string."""
    alignment = 32
    values = (-1.0, -0.25, 0.5, 1.25)
    buffer = bytearray()
    buffer.extend(MAGIC)
    buffer.extend(struct.pack("<IQQ", VERSION, 1, 2))
    append_metadata_string(buffer, "general.architecture", "toy")
    append_metadata_u32(buffer, "general.alignment", alignment)
    append_string(buffer, "toy.weight")
    buffer.extend(struct.pack("<I", 1))
    buffer.extend(struct.pack("<Q", len(values)))
    buffer.extend(struct.pack("<IQ", GGML_TYPE_F32, 0))
    data_offset = align_up(len(buffer), alignment)
    buffer.extend(b"\x00" * (data_offset - len(buffer)))
    buffer.extend(struct.pack("<4f", *values))
    return bytes(buffer)


def checked_product(shape: tuple[int, ...]) -> int:
    result = 1
    for dimension in shape:
        if not 1 <= dimension <= 4096:
            raise FormatError("tensor dimension is outside the fixture limit")
        result *= dimension
        if result > MAX_FILE_BYTES // 4:
            raise FormatError("tensor element count is too large")
    return result


def parse_toy_gguf(payload: bytes) -> ToyGguf:
    """Parse and validate only the documented toy subset; never execute data."""
    reader = Reader(payload)
    if reader.take(4) != MAGIC:
        raise FormatError("not a GGUF magic value")
    version = reader.u32()
    if version != VERSION:
        raise FormatError(f"expected GGUF v{VERSION}, found v{version}")
    tensor_count = reader.u64()
    metadata_count = reader.u64()
    if not 1 <= tensor_count <= MAX_COUNT or metadata_count > MAX_COUNT:
        raise FormatError("unreasonable tensor or metadata count")

    metadata: dict[str, int | str] = {}
    for _ in range(metadata_count):
        key = reader.string()
        if not key or key in metadata:
            raise FormatError("metadata key is empty or duplicated")
        value_type = reader.u32()
        if value_type == VALUE_TYPE_STRING:
            value: int | str = reader.string()
        elif value_type == VALUE_TYPE_UINT32:
            value = reader.u32()
        else:
            raise FormatError(f"unsupported metadata value type {value_type}")
        metadata[key] = value

    architecture = metadata.get("general.architecture")
    alignment = metadata.get("general.alignment")
    if architecture != "toy":
        raise FormatError("toy fixture requires general.architecture=toy")
    if not isinstance(alignment, int):
        raise FormatError("toy fixture needs an integer general.alignment")
    tensor_info_start = reader.position
    try:
        data_offset = align_up(tensor_info_start + _tensor_info_size(reader, tensor_count), alignment)
    except ValueError as error:
        raise FormatError(str(error)) from error

    # Re-read tensor infos after calculating their exact fixed/variable length.
    # A second bounded Reader avoids speculative offsets into tensor data.
    tensor_reader = Reader(payload)
    tensor_reader.position = tensor_info_start
    tensors: list[TensorInfo] = []
    for _ in range(tensor_count):
        name = tensor_reader.string()
        ndim = tensor_reader.u32()
        if not 1 <= ndim <= 4:
            raise FormatError("toy tensors need one through four dimensions")
        shape = tuple(tensor_reader.u64() for _ in range(ndim))
        ggml_type = tensor_reader.u32()
        relative_offset = tensor_reader.u64()
        if not name or ggml_type != GGML_TYPE_F32:
            raise FormatError("toy fixture accepts named F32 tensors only")
        byte_length = checked_product(shape) * 4
        tensors.append(TensorInfo(name, shape, ggml_type, relative_offset, byte_length))
    if tensor_reader.position > data_offset:
        raise FormatError("tensor information overlaps aligned data")

    ranges: list[tuple[int, int]] = []
    for tensor in tensors:
        start = data_offset + tensor.offset
        end = start + tensor.byte_length
        if start < data_offset or end > len(payload):
            raise FormatError(f"tensor {tensor.name!r} points outside the file")
        ranges.append((start, end))
    if any(right[0] < left[1] for left, right in zip(sorted(ranges), sorted(ranges)[1:])):
        raise FormatError("tensor byte ranges overlap")

    return ToyGguf(version, metadata, tuple(tensors), data_offset, len(payload))


def _tensor_info_size(reader: Reader, tensor_count: int) -> int:
    """Measure tensor infos without trusting their offsets or materializing them."""
    start = reader.position
    for _ in range(tensor_count):
        reader.string()
        ndim = reader.u32()
        if not 1 <= ndim <= 4:
            raise FormatError("toy tensors need one through four dimensions")
        reader.take(8 * ndim + 4 + 8)
    return reader.position - start


def symmetric_int4_error(values: tuple[float, ...]) -> dict[str, float]:
    """Return deterministic error metrics for a simple teaching-only 4-bit grid."""
    if not values or not all(math.isfinite(value) for value in values):
        raise ValueError("values must be non-empty finite numbers")
    scale = max(abs(value) for value in values) / 7.0 or 1.0
    reconstructed = tuple(max(-7, min(7, round(value / scale))) * scale for value in values)
    errors = tuple(approximation - reference for reference, approximation in zip(values, reconstructed))
    return {
        "scale": scale,
        "mae": sum(abs(error) for error in errors) / len(errors),
        "max_abs": max(abs(error) for error in errors),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--write",
        type=Path,
        help="write the toy fixture only to a path that does not already exist",
    )
    args = parser.parse_args(argv)
    payload = build_toy_gguf()
    parsed = parse_toy_gguf(payload)
    metrics = symmetric_int4_error((-1.0, -0.25, 0.5, 1.25))
    print(f"toy GGUF: {parsed.byte_length} bytes; data starts at byte {parsed.data_offset}")
    print(f"metadata: {parsed.metadata}")
    print(f"tensor: {parsed.tensors[0].name} shape={parsed.tensors[0].shape} offset=0")
    print("teaching-only symmetric INT4: " + ", ".join(f"{key}={value:.6f}" for key, value in metrics.items()))
    if args.write is not None:
        destination = args.write
        if not destination.parent.is_dir():
            parser.error("--write parent directory must already exist")
        if destination.exists() or destination.is_symlink():
            parser.error("refusing to overwrite or replace an existing path")
        destination.write_bytes(payload)
        print(f"wrote new toy fixture: {destination}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

测试同样只处理 toy bytes，并验证拒绝路径：

<!-- code-sync: ./test_gguf_toy_validator.py -->
```python
#!/usr/bin/env python3
"""Unit tests for the bounded toy GGUF format fixture."""

from __future__ import annotations

import struct
import unittest

import gguf_toy_validator as toy


class ToyGgufTests(unittest.TestCase):
    def setUp(self) -> None:
        self.payload = toy.build_toy_gguf()

    def test_fixture_has_expected_header_metadata_tensor_and_alignment(self) -> None:
        parsed = toy.parse_toy_gguf(self.payload)
        self.assertEqual(parsed.version, 3)
        self.assertEqual(parsed.metadata["general.architecture"], "toy")
        self.assertEqual(parsed.metadata["general.alignment"], 32)
        self.assertEqual(parsed.data_offset % 32, 0)
        self.assertEqual(len(parsed.tensors), 1)
        self.assertEqual(parsed.tensors[0].name, "toy.weight")
        self.assertEqual(parsed.tensors[0].shape, (4,))
        self.assertEqual(parsed.tensors[0].byte_length, 16)

    def test_rejects_truncation_bad_magic_and_unsupported_version(self) -> None:
        with self.assertRaises(toy.FormatError):
            toy.parse_toy_gguf(self.payload[:-1])
        with self.assertRaises(toy.FormatError):
            toy.parse_toy_gguf(b"NOPE" + self.payload[4:])
        unsupported = bytearray(self.payload)
        struct.pack_into("<I", unsupported, 4, 99)
        with self.assertRaises(toy.FormatError):
            toy.parse_toy_gguf(bytes(unsupported))

    def test_rejects_tensor_offset_outside_file(self) -> None:
        corrupted = bytearray(self.payload)
        marker = b"toy.weight"
        name_offset = corrupted.index(marker)
        # name starts after an eight-byte GGUF string length; then ndim and dim.
        relative_offset_position = name_offset + len(marker) + 4 + 8 + 4
        struct.pack_into("<Q", corrupted, relative_offset_position, 10_000)
        with self.assertRaises(toy.FormatError):
            toy.parse_toy_gguf(bytes(corrupted))

    def test_four_bit_grid_has_bounded_error_without_out_of_range_codes(self) -> None:
        metrics = toy.symmetric_int4_error((-1.0, -0.25, 0.5, 1.25))
        self.assertGreater(metrics["scale"], 0.0)
        self.assertLessEqual(metrics["max_abs"], metrics["scale"] / 2.0 + 1e-12)


if __name__ == "__main__":
    unittest.main(verbosity=2)
```

## 3. 比较表：先固定条件，再比较四类结果

每个候选（高精度基线、`Q8_0`、低比特候选、某个 K-quant）都在相同硬件、同一固定运行时 commit、同一后端/threads/GPU offload、相同 context、同一 prompt 集、相同 seed 与生成参数下完成。冷启动和热启动分别记录；prefill 与 decode 分开，避免把首 token 延迟混成“tokens/s”。

| 候选 | SHA-256 | 文件字节 | Host RAM 峰值 | VRAM 峰值 | prefill tok/s | decode tok/s | 质量分数/失败例 | 接受？ |
| --- | --- | ---: | ---: | ---: | ---: | ---: | --- | --- |
| 高精度 GGUF | 待填 | 待填 | 待填 | 待填 | 待填 | 待填 | 基线 | 待填 |
| `Q8_0`（若该 commit 支持） | 待填 | 待填 | 待填 | 待填 | 待填 | 待填 | 待填 | 待填 |
| 低比特候选 | 待填 | 待填 | 待填 | 待填 | 待填 | 待填 | 待填 | 待填 |
| K-quant 候选 | 待填 | 待填 | 待填 | 待填 | 待填 | 待填 | 待填 | 待填 |

质量至少使用一个与用途匹配、许可清楚的固定评测集或公开 prompt 集；保存指标定义、样本数、解析规则和失败样本的可分享/脱敏状态。只比较文件大小不够；只比较一条漂亮回答也不够。若候选加载失败、输出 token 数与基线不同或 tokenizer/chat template 不一致，先判为不可比并回到结构/文本层排查，不要把它写成“量化质量下降”。

### 最终成功标准

- [ ] manifest 中 revision、每个输入/输出 SHA-256、许可证和固定 `llama.cpp` commit 均已填写；没有 secret 或真实权重进入 Vault/Git。
- [ ] config、tokenizer、chat template、分片索引及 safetensors 张量名/shape 已同 revision 核对。
- [ ] 高精度 GGUF 的 header/version、metadata、tensor info、alignment、offset/length 已验证；随后才量化。
- [ ] 每个量化输出可由 manifest 追溯到高精度 GGUF 哈希，并在固定运行时最小加载。
- [ ] 比较表的大小、RAM/VRAM、prefill/decode 和质量在相同条件下取得，失败与不可比项目没有被隐藏。
- [ ] 已区分文本、容器、数值三层，并没有把 toy 运行结果冒充为 NF4/GPTQ/AWQ/K-quant 或真实模型结果。

## 许可证、恢复与清理

- 先分别确认模型/adapter 权重许可、模型卡使用条款、tokenizer 许可、评测集许可、`llama.cpp` 与其他工具代码许可；“能转换”不等于可再分发。
- 原始 safetensors 是输入基线：保持其只读/不覆盖。所有派生 GGUF、日志、benchmark 和 manifest 只创建在本次 `RUN_ROOT` 下，且列入 manifest 的 `cleanup_paths_created_by_this_run_only`。
- 要恢复到转换前，停止运行时、保留 manifest 与哈希文本，然后只删除 manifest 中本次创建的派生目录；绝不以 glob 删除模型父目录，更不要删除源分片。若需要保留可复核记录，只保留无敏感信息的 manifest 与摘要。
- 本课程实际运行未创建任何权重或 toy 文件（默认脚本只在内存中构造 bytes），所以没有需要清理的产物。

---

**返回**：[[AI/80-实践/00-AI实践-MOC|AI 实践 MOC]] · **格式路线**：[[AI/20-LLM/60-模型格式与量化/00-模型格式与量化-MOC|模型格式与量化 MOC]] · **数值基础**：[[数学/60-数值计算与量化/00-数值计算与量化-MOC|数值计算与量化 MOC]] · **运行时**：[[AI/20-LLM/50-实现/04-llama.cpp构建后端与调用链|llama.cpp 构建、后端与调用链]] · **资料核验**：[[AI/90-资源/05-官方资料与版本核验记录|官方资料与版本核验记录]]
