---
type: lab
domain: computer-science
stage: 7
status: ready
difficulty: 进阶
estimated_minutes: 35
topics: [LLVM, MLIR, IR, toolchain-probe]
tags: [computer-science/compiler, computer-science/llvm, computer-science/practice]
---

# LLVM 与 MLIR 工具链探针

## 目标与边界

这是一个**环境取证探针**：它记录 `clang`、`opt`、`llc`、`lli` 和 `mlir-opt` 实际解析到的路径与版本首行；同时记录两个固定输入的 SHA-256、由 `clang -dumpmachine`（必要时 `-print-target-triple`）给出的 host-default target triple，以及实际执行的命令。随后它用这些输入做最小解析、verifier、object 生成与 `lli` 执行。理论入口是 [[计算机知识/70-编译原理/17-LLVM-IR-Pass与MLIR方言-Lowering|LLVM IR、Pass 与 MLIR 方言/Lowering]]，IR 语义边界见 [[计算机知识/70-编译原理/07-中间表示Lowering与三地址码|中间表示、Lowering 与三地址码]]。

它不会下载、安装、更新或修改任何工具链，也不读写工程外的固定产物路径。所有 `.o` 和规范化 IR 都只进入 `mktemp -d` 创建的唯一目录，退出时由 `trap` 清理。缺少任一命名工具、或 `clang` 无法给出 host-default triple 时，对应项明确记为 `SKIP` 且总进程返回 **77**；不得把 SKIP 写成 PASS。工具已存在但拒绝固定输入、或声称成功却没有产生非空 object 时返回 1，便于区分“没安装”与“版本/调用不兼容”。

## 运行

```bash
./probe_toolchain.sh
status=$?
if [ "$status" -eq 77 ]; then
  printf '%s\n' 'SKIP: optional LLVM/MLIR tools are incomplete'
elif [ "$status" -ne 0 ]; then
  exit "$status"
fi
```

`LLVM` 和 `MLIR` 的文本语法、Pass Manager CLI、默认方言注册及工具拆包方式都会随版本和发行包变化。因此本页的输入是当前尽量保守的小样例，不是永久 CLI 契约。`sample.ll` 故意不写 target triple/data layout，因而 IR 本身近似 target-neutral；一旦生成 object，ABI、数据布局与指令选择就必须依赖目标。本探针把 `clang -dumpmachine` 的结果（不支持时回退 `-print-target-triple`）显式传给 `clang --target=…` 和 `llc -mtriple=…` 并记录下来。若发行包没有未版本化的 `clang` / `llc`、查询 target 失败、或它们对该选项不兼容，应保留 `SKIP`/`FAIL` 证据而不是借另一个工具冒充。若已安装工具报错，先保留路径、版本、target、输入 hash 与完整诊断，再对照该版本官方文档；不要为了让探针变绿而静默改换系统工具。

## 精确伴随文件

<!-- code-sync: ./probe_toolchain.sh -->
```bash
#!/usr/bin/env bash
set -uo pipefail

readonly script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
cd -- "$script_dir" || {
  printf '%s\n' "probe status=FAIL reason=course-directory-unavailable" >&2
  exit 1
}
printf 'input_directory=%s\n' "$script_dir"
work_dir=""

cleanup() {
  if [[ -n "$work_dir" && -d "$work_dir" ]]; then
    rm -rf -- "$work_dir"
  fi
}
trap cleanup EXIT HUP INT TERM

work_dir="$(mktemp -d "${TMPDIR:-/tmp}/llvm-mlir-probe.XXXXXX")" || {
  printf '%s\n' "probe status=FAIL reason=mktemp-failed" >&2
  exit 1
}
printf 'workspace=%s lifecycle=temporary\n' "$work_dir"

missing=0
failed=0
for tool_name in clang opt llc lli mlir-opt; do
  tool_location="$(command -v "$tool_name" 2>/dev/null || true)"
  if [[ -z "$tool_location" ]]; then
    printf 'tool=%s status=SKIP reason=not-found\n' "$tool_name"
    missing=1
    continue
  fi
  version_line="$("$tool_location" --version 2>&1 | sed -n '1p')"
  printf 'tool=%s status=FOUND path=%s version=%s\n' \
    "$tool_name" "$tool_location" "$version_line"
done

print_command() {
  local argument
  printf 'command='
  for argument in "$@"; do
    printf '%q ' "$argument"
  done
  printf '\n'
}

run_probe() {
  local probe_name="$1"
  local tool_name="$2"
  shift 2
  if ! command -v "$tool_name" >/dev/null 2>&1; then
    printf 'probe=%s status=SKIP reason=%s-not-found\n' "$probe_name" "$tool_name"
    return 77
  fi
  print_command "$@"
  if "$@"; then
    printf 'probe=%s status=PASS\n' "$probe_name"
    return 0
  else
    probe_status=$?
    printf 'probe=%s status=FAIL exit=%s\n' "$probe_name" "$probe_status" >&2
    failed=1
    return "$probe_status"
  fi
}

clang_path="$(command -v clang 2>/dev/null || true)"
opt_path="$(command -v opt 2>/dev/null || true)"
llc_path="$(command -v llc 2>/dev/null || true)"
lli_path="$(command -v lli 2>/dev/null || true)"
mlir_opt_path="$(command -v mlir-opt 2>/dev/null || true)"

for input_path in sample.ll sample.mlir; do
  if command -v shasum >/dev/null 2>&1; then
    input_hash="$(shasum -a 256 "$input_path" | awk '{print $1}')"
  elif command -v sha256sum >/dev/null 2>&1; then
    input_hash="$(sha256sum "$input_path" | awk '{print $1}')"
  else
    input_hash="unavailable"
  fi
  printf 'input=%s sha256=%s\n' "$(basename -- "$input_path")" "$input_hash"
done

host_target=""
target_provenance=""
if [[ -n "$clang_path" ]]; then
  host_target="$("$clang_path" -dumpmachine 2>/dev/null | sed -n '1p')"
  target_provenance="clang-dumpmachine"
  if [[ -z "$host_target" ]]; then
    host_target="$("$clang_path" -print-target-triple 2>/dev/null | sed -n '1p')"
    target_provenance="clang-print-target-triple"
  fi
fi
if [[ -z "$host_target" ]]; then
  printf '%s\n' 'target=host-default status=SKIP reason=clang-target-query-unavailable'
  missing=1
else
  printf 'target=host-default triple=%s provenance=%s\n' "$host_target" "$target_provenance"
fi

# The input LLVM IR intentionally has no target triple or data layout. Object
# generation is therefore made reproducible by supplying this recorded target.
if [[ -n "$host_target" ]]; then
  if run_probe llvm-clang clang "$clang_path" --target="$host_target" -c sample.ll -o "$work_dir/clang-sample.o"; then
    if [[ -s "$work_dir/clang-sample.o" ]]; then
      printf 'artifact=clang-sample.o status=PASS bytes=%s\n' "$(wc -c < "$work_dir/clang-sample.o")"
    else
      printf '%s\n' 'artifact=clang-sample.o status=FAIL reason=missing-or-empty' >&2
      failed=1
    fi
  fi
  if run_probe llvm-llc llc "$llc_path" -mtriple="$host_target" -filetype=obj sample.ll -o "$work_dir/llc-sample.o"; then
    if [[ -s "$work_dir/llc-sample.o" ]]; then
      printf 'artifact=llc-sample.o status=PASS bytes=%s\n' "$(wc -c < "$work_dir/llc-sample.o")"
    else
      printf '%s\n' 'artifact=llc-sample.o status=FAIL reason=missing-or-empty' >&2
      failed=1
    fi
  fi
else
  printf '%s\n' 'probe=llvm-clang status=SKIP reason=host-target-unavailable'
  printf '%s\n' 'probe=llvm-llc status=SKIP reason=host-target-unavailable'
fi

run_probe llvm-opt-verify opt "$opt_path" -passes=verify -disable-output sample.ll || true
run_probe llvm-lli lli "$lli_path" sample.ll || true
run_probe mlir-verify mlir-opt "$mlir_opt_path" --verify-each sample.mlir -o "$work_dir/verified.mlir" || true

if [[ "$failed" -ne 0 ]]; then
  printf '%s\n' "probe status=FAIL reason=installed-tool-rejected-fixed-input" >&2
  exit 1
fi
if [[ "$missing" -ne 0 ]]; then
  printf '%s\n' "probe status=SKIP exit=77 reason=incomplete-toolchain"
  exit 77
fi
printf '%s\n' "probe status=PASS exit=0"
```

<!-- code-sync: ./sample.ll -->
```llvm
; A deliberately small target-neutral LLVM IR input: it intentionally omits
; target triple/data layout; the probe supplies and records its codegen target.
define i32 @add(i32 %lhs, i32 %rhs) {
entry:
  %sum = add i32 %lhs, %rhs
  ret i32 %sum
}

define i32 @main() {
entry:
  %answer = call i32 @add(i32 20, i32 22)
  %ok = icmp eq i32 %answer, 42
  %status = select i1 %ok, i32 0, i32 1
  ret i32 %status
}
```

<!-- code-sync: ./sample.mlir -->
```mlir
// A small generic MLIR module using only common upstream dialects.
module {
  func.func @add(%lhs: i32, %rhs: i32) -> i32 {
    %sum = arith.addi %lhs, %rhs : i32
    return %sum : i32
  }
}
```

## 练习

1. 把两次运行的 `FOUND path/version`、输入 hash 与 target triple 放在一起比较，解释 PATH 变化、工具升级、输入变化和目标变化为什么是四种不同的漂移。
2. 只在实验副本里给 `sample.ll` 加一个类型错误，确认已存在的 verifier 报 `FAIL/1`，而不是 `SKIP/77`。
3. 将 `clang --target=…` 的 object 与 `llc -mtriple=…` 的 object 分开观察：二者同为非空只是生成成功的证据，不能证明二进制布局或优化结果相同。
4. 阅读当前 `mlir-opt --help`，找到一个只做规范化的 Pass，把命令和版本写进自己的实验记录；不改系统安装。

## 成功标准

- 五个工具都有 `FOUND` 或 `SKIP` 记录，`FOUND` 同时显示真实路径和版本首行；两个输入都有 hash，且 codegen 路径会记录 host-default target 的来源。
- `clang` / `llc` 成功时各自留下“非空 object”证据；IR 可以不含 target triple，但 object 不得被误称为 target-neutral。
- 工具齐全且全部接受固定输入时返回 0；工具或 target 查询缺失时返回 77；已安装工具失败、或 object 为空时返回 1。
- 运行后没有在实验目录留下 `.o` 或改写输入，能说明 verifier 通过不能证明优化语义正确。

---

**上一站**：[[计算机知识/80-实践/08-编译原理/06-指令选择寄存器分配与重定位/README|指令选择、寄存器分配与重定位]] · **下一站**：[[计算机知识/80-实践/08-编译原理/08-AI计算图Lowering融合与Shape特化/README|AI 计算图 Lowering、融合与 Shape 特化]] · **返回**：[[计算机知识/80-实践/08-编译原理/00-编译原理实践-MOC|编译原理实践 MOC]]


<!-- revision-2-navigation -->
## 本轮课程定位与机制补充

课程顺序与原稿入口：[[计算机知识/00-开始/课程地图/12-编译原理-课程地图|编译原理 · 课程地图]]。进一步的机制推演与反例：[[计算机知识/70-编译原理/20-数据流优化正确性与编译知识全景|编译原理深化：数据流、不动点和优化正确性]]。跨学科辨析：[[计算机知识/90-资源/11-跨学科概念辨析|跨学科概念辨析]]。
