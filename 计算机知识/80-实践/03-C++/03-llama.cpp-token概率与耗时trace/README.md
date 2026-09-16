---
type: practice
stage: 1
status: ready
difficulty: 中级
estimated_minutes: 50
domain: computer-science
tags:
  - computer-science/cpp
  - computer-science/llm
  - computer-science/performance
---

# llama.cpp token 概率与耗时 trace

本练习只读本地 GGUF，显式记录 prompt 的 token 数、一次 prefill 的墙钟时间、实际 context 容量与 logits 的前五个 softmax 概率。它是 API 观察练习，不是基准测试：后端、量化、线程、`n_ctx`、模型文件和首轮预热都会改变结果。调用链背景见 [[AI/20-LLM/50-实现/04-llama.cpp构建后端与调用链|llama.cpp 构建、后端与调用链]]、[[AI/20-LLM/50-实现/05-llama.cpp源码阅读与小型扩展|llama.cpp 源码阅读与小型扩展]]，模型格式边界见 [[AI/20-LLM/60-模型格式与量化/03-GGUF结构转换与验证|GGUF 结构、转换与验证]]。

## 固定提交策略（不复制、不自动拉取上游）

这里没有 vendor 目录、子模块、下载脚本或模型 URL。取得公开 llama.cpp 源码时，由学习者在本目录之外准备独立 checkout，并先把**已审核的完整 40 位 commit SHA**写入自己保管的记录。随后只允许 detached checkout，并把实际 HEAD 与记录逐字比对：

```sh
export LLAMA_CPP_COMMIT='PASTE_A_REVIEWED_40_HEX_COMMIT_SHA'
git clone https://github.com/ggml-org/llama.cpp.git /ABSOLUTE/PATH/TO/llama.cpp
git -C /ABSOLUTE/PATH/TO/llama.cpp checkout --detach "$LLAMA_CPP_COMMIT"
test "$(git -C /ABSOLUTE/PATH/TO/llama.cpp rev-parse HEAD)" = "$LLAMA_CPP_COMMIT"
```

`PASTE_A_REVIEWED_40_HEX_COMMIT_SHA` 不是可执行值；未替换、不是 40 位 SHA 或比对失败时必须停止。不要用会移动的分支名、tag 名或“最新版本”替代记录。不要把模型、私有提示词、路径中可能含身份信息的输出或 commit 以外的外部仓库内容提交进 Vault。

## 先验证不依赖 llama.cpp 的数学测试

即使没有 checkout 或 GGUF，也可以确认稳定 softmax、top-k 排序与非有限输入的拒绝行为：

```sh
cmake -S . -B build -DCMAKE_BUILD_TYPE=Debug
cmake --build build
ctest --test-dir build --output-on-failure
```

这只编译 `trace_math_tests`。配置文件不会联网，也不会下载、转换或扫描模型。测试使用显式条件和非零返回值，所以 Debug 与 Release 都会执行有限值、排序和非法 logit 检查。

## 在已固定的本地 checkout 上启用 API 示例

模型必须是你已有、可合法使用的本地 GGUF；示例不接受 URL，也不会调用网络。为防止把两次不同设置的数字混在一起，运行前记录：完整 SHA、`cmake --build` 配置、GGUF 的 SHA-256、CPU/GPU 后端、线程数、`n_ctx=512`、`n_gpu_layers=0` 和是否首次运行。当前程序明确用 CPU (`n_gpu_layers=0`)；改动该值就等于换了实验条件。

```sh
cmake -S . -B build -DLLAMA_CPP_DIR=/ABSOLUTE/PATH/TO/llama.cpp
cmake --build build --target llama_token_trace
./build/llama_token_trace /ABSOLUTE/PATH/TO/MODEL.GGUF "The compact trace begins"
```

成功输出先有一行 `trace,prompt_tokens=...`，再有五行 `top_token,...`。`probability` 是**当前模型、当前上下文、当前最后 prompt 位置**下的完整词表 softmax 概率，不是生成质量评分，也不是采样后的频率。`piece` 可能含空白、控制字符或 tokenizer 特殊符号，保存日志时应把它视为模型输出数据。

## API 边界

- `llama_tokenize` 产生 prompt token；`llama_batch_init` 创建需显式释放的 API batch，因此 `Batch` 在析构时调用 `llama_batch_free`。
- 本练习把 `n_ctx` 和 `n_batch` 都固定为 512，且 token 计数包含代码请求 tokenizer 加入的特殊 token。prompt 编码后超过任一上限时，程序会在创建 context 和 batch 前明确拒绝；这是本页的实验边界，不是 llama.cpp 的通用上限。
- 每个 batch 项都有位置和 sequence id，只有最后一个 token 请求 logits；因此 `llama_decode` 成功后用 `llama_get_logits_ith(..., count - 1)` 读取最后一个 batch 位置，并检查返回指针。不要把“只请求一个输出”误解成它自动改名为 batch 索引 0。
- 概率辅助函数接受有限 logit 与用作 mask 的负无穷，但拒绝 NaN、正无穷和“全为负无穷”的输入，避免将未定义的 softmax 结果继续写入 trace。
- `llama_time_us` 包住 decode，再 `llama_synchronize` 后取时间，避免把尚未完成的后端工作误记为完成；这仍不替代正式 benchmark 的预热、重复、统计和环境控制。
- llama.cpp API 演进很快。固定 SHA 的价值是让头文件、CMake target 和示例一起可审计；若 pinned checkout 没有 `llama` target 或函数签名不同，停止并记录差异，不要在没有重新审阅本页的情况下套用 master API。

## 精确的伴随文件

<!-- code-sync: ./CMakeLists.txt -->
```cmake
cmake_minimum_required(VERSION 3.24)
project(llama_token_trace LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

function(enable_project_warnings target)
  if(MSVC)
    target_compile_options(${target} PRIVATE /W4)
  elseif(CMAKE_CXX_COMPILER_ID MATCHES "GNU|Clang")
    target_compile_options(${target} PRIVATE -Wall -Wextra -Wpedantic)
  endif()
endfunction()

enable_testing()
add_executable(trace_math_tests trace_math_tests.cpp)
enable_project_warnings(trace_math_tests)
add_test(NAME trace_math_tests COMMAND trace_math_tests)

set(LLAMA_CPP_DIR "" CACHE PATH "Pinned local llama.cpp checkout; it is never fetched automatically")
if(LLAMA_CPP_DIR STREQUAL "")
    message(STATUS "Only trace_math_tests is enabled. Set LLAMA_CPP_DIR to a pinned local checkout to build llama_token_trace.")
    return()
endif()

if(NOT EXISTS "${LLAMA_CPP_DIR}/CMakeLists.txt")
    message(FATAL_ERROR "LLAMA_CPP_DIR is not a llama.cpp source checkout: ${LLAMA_CPP_DIR}")
endif()

add_subdirectory("${LLAMA_CPP_DIR}" llama_cpp_build EXCLUDE_FROM_ALL)
if(NOT TARGET llama)
    message(FATAL_ERROR "Pinned llama.cpp checkout did not export target 'llama'; inspect its CMake API before changing this lesson.")
endif()

add_executable(llama_token_trace llama_token_trace.cpp)
target_link_libraries(llama_token_trace PRIVATE llama)
enable_project_warnings(llama_token_trace)
```

<!-- code-sync: ./trace_math.hpp -->
```cpp
#pragma once

#include <algorithm>
#include <cmath>
#include <cstddef>
#include <limits>
#include <numeric>
#include <stdexcept>
#include <vector>

struct TopToken {
    int id;
    float probability;
};

inline std::vector<TopToken> top_probabilities(const float * logits, std::size_t vocab_size,
                                                std::size_t top_k) {
    if (logits == nullptr || vocab_size == 0 || top_k == 0) {
        throw std::invalid_argument("logits, vocabulary size, and top_k must be non-empty");
    }

    bool has_finite_logit = false;
    for (std::size_t i = 0; i < vocab_size; ++i) {
        if (std::isnan(logits[i]) || logits[i] == std::numeric_limits<float>::infinity()) {
            throw std::domain_error("logits must not contain NaN or positive infinity");
        }
        has_finite_logit = has_finite_logit || std::isfinite(logits[i]);
    }
    if (!has_finite_logit) {
        throw std::domain_error("at least one logit must be finite");
    }

    const float maximum = *std::max_element(logits, logits + vocab_size);
    std::vector<float> weights(vocab_size);
    for (std::size_t i = 0; i < vocab_size; ++i) {
        weights[i] = std::exp(logits[i] - maximum);
    }
    const float normalizer = std::accumulate(weights.begin(), weights.end(), 0.0F);
    if (!std::isfinite(normalizer) || normalizer <= 0.0F) {
        throw std::domain_error("softmax normalizer must be finite and positive");
    }
    std::vector<int> ids(vocab_size);
    std::iota(ids.begin(), ids.end(), 0);
    const std::size_t count = std::min(top_k, vocab_size);
    std::partial_sort(ids.begin(), ids.begin() + static_cast<std::ptrdiff_t>(count), ids.end(),
                      [&weights](int left, int right) { return weights[left] > weights[right]; });

    std::vector<TopToken> result;
    result.reserve(count);
    for (std::size_t rank = 0; rank < count; ++rank) {
        const int id = ids[rank];
        result.push_back({id, weights[static_cast<std::size_t>(id)] / normalizer});
    }
    return result;
}
```

<!-- code-sync: ./trace_math_tests.cpp -->
```cpp
#include "trace_math.hpp"

#include <cmath>
#include <iostream>
#include <limits>
#include <stdexcept>

namespace {
bool rejects_non_finite(const float * logits, std::size_t count) {
    try {
        static_cast<void>(top_probabilities(logits, count, 1));
    } catch (const std::domain_error &) {
        return true;
    }
    return false;
}
}  // namespace

int main() {
    const float logits[] = {0.0F, 2.0F, 1.0F};
    const auto top = top_probabilities(logits, 3, 2);
    if (top.size() != 2 || top[0].id != 1 || top[0].probability <= top[1].probability ||
        std::abs(top[0].probability + top[1].probability - 0.9099694F) >= 0.0001F) {
        std::cerr << "finite softmax/top-k check failed\n";
        return 1;
    }

    const float with_negative_infinity[] = {
        0.0F, -std::numeric_limits<float>::infinity(), 1.0F};
    const auto finite_top = top_probabilities(with_negative_infinity, 3, 2);
    if (finite_top.size() != 2 || !std::isfinite(finite_top[0].probability) ||
        !std::isfinite(finite_top[1].probability)) {
        std::cerr << "negative-infinity masking check failed\n";
        return 1;
    }

    const float with_nan[] = {0.0F, std::numeric_limits<float>::quiet_NaN()};
    const float with_positive_infinity[] = {
        0.0F, std::numeric_limits<float>::infinity()};
    const float all_negative_infinity[] = {
        -std::numeric_limits<float>::infinity(), -std::numeric_limits<float>::infinity()};
    if (!rejects_non_finite(with_nan, 2) || !rejects_non_finite(with_positive_infinity, 2) ||
        !rejects_non_finite(all_negative_infinity, 2)) {
        std::cerr << "invalid-logit rejection check failed\n";
        return 1;
    }
}
```

<!-- code-sync: ./llama_token_trace.cpp -->
```cpp
#include "trace_math.hpp"

#include <llama.h>

#include <cstdlib>
#include <iostream>
#include <memory>
#include <string>
#include <vector>

namespace {
struct ModelDeleter {
    void operator()(llama_model * model) const { llama_model_free(model); }
};

struct ContextDeleter {
    void operator()(llama_context * context) const { llama_free(context); }
};

struct Batch {
    explicit Batch(int tokens) : value(llama_batch_init(tokens, 0, 1)) {}
    ~Batch() { llama_batch_free(value); }
    Batch(const Batch&) = delete;
    Batch& operator=(const Batch&) = delete;
    llama_batch value;
};

struct BackendGuard {
    ~BackendGuard() { llama_backend_free(); }
};

std::string token_piece(const llama_vocab * vocab, llama_token token) {
    std::vector<char> buffer(128);
    int count = llama_token_to_piece(vocab, token, buffer.data(), buffer.size(), 0, true);
    if (count < 0) {
        buffer.resize(static_cast<std::size_t>(-count));
        count = llama_token_to_piece(vocab, token, buffer.data(), buffer.size(), 0, true);
    }
    return count >= 0 ? std::string(buffer.data(), static_cast<std::size_t>(count)) : "<unprintable>";
}
}  // namespace

int main(int argc, char * argv[]) {
    if (argc != 3) {
        std::cerr << "usage: llama_token_trace MODEL.GGUF PROMPT\n";
        return EXIT_FAILURE;
    }

    llama_backend_init();
    BackendGuard backend_guard;

    auto model_params = llama_model_default_params();
    model_params.n_gpu_layers = 0;  // CPU trace: record a different value explicitly when comparing.
    std::unique_ptr<llama_model, ModelDeleter> model(
        llama_model_load_from_file(argv[1], model_params));
    if (!model) {
        std::cerr << "could not load the local GGUF model\n";
        return EXIT_FAILURE;
    }
    const llama_vocab * vocab = llama_model_get_vocab(model.get());
    const std::string prompt = argv[2];
    const int count = -llama_tokenize(vocab, prompt.c_str(), prompt.size(), nullptr, 0, true, true);
    if (count <= 0) {
        std::cerr << "could not tokenize prompt\n";
        return EXIT_FAILURE;
    }
    std::vector<llama_token> tokens(static_cast<std::size_t>(count));
    if (llama_tokenize(vocab, prompt.c_str(), prompt.size(), tokens.data(), count, true, true) < 0) {
        std::cerr << "tokenization buffer was unexpectedly too small\n";
        return EXIT_FAILURE;
    }

    auto context_params = llama_context_default_params();
    context_params.n_ctx = 512;
    context_params.n_batch = 512;
    if (count > static_cast<int>(context_params.n_ctx) ||
        count > static_cast<int>(context_params.n_batch)) {
        std::cerr << "prompt token count " << count
                  << " exceeds this lesson's n_ctx/n_batch limit of 512\n";
        return EXIT_FAILURE;
    }
    std::unique_ptr<llama_context, ContextDeleter> context(
        llama_init_from_model(model.get(), context_params));
    if (!context) {
        std::cerr << "could not create context\n";
        return EXIT_FAILURE;
    }

    Batch batch(count);
    for (int i = 0; i < count; ++i) {
        batch.value.token[i] = tokens[static_cast<std::size_t>(i)];
        batch.value.pos[i] = i;
        batch.value.n_seq_id[i] = 1;
        batch.value.seq_id[i][0] = 0;
        batch.value.logits[i] = i == count - 1;
    }
    const int64_t started_us = llama_time_us();
    const int decode_result = llama_decode(context.get(), batch.value);
    if (decode_result != 0) {
        std::cerr << "llama_decode returned " << decode_result << '\n';
        return EXIT_FAILURE;
    }
    llama_synchronize(context.get());
    const int64_t elapsed_us = llama_time_us() - started_us;

    const float * logits = llama_get_logits_ith(context.get(), count - 1);
    if (logits == nullptr) {
        std::cerr << "last prompt token did not produce logits\n";
        return EXIT_FAILURE;
    }
    const auto top = top_probabilities(logits, llama_vocab_n_tokens(vocab), 5);
    std::cout << "trace,prompt_tokens=" << count << ",prefill_us=" << elapsed_us
              << ",n_ctx=" << llama_n_ctx(context.get()) << ",gpu_layers=0\n";
    for (const auto & item : top) {
        std::cout << "top_token,id=" << item.id << ",probability=" << item.probability
                  << ",piece=" << token_piece(vocab, item.id) << '\n';
    }
}
```

## 恢复

先用 `ctest --test-dir build --output-on-failure` 确认纯数学部分仍可复现。若且仅若当前目录是本项目且 `build/CMakeCache.txt` 存在，才删除这个项目的 `build/` 并重新配置；绝不清理外部 llama.cpp checkout、模型目录或上级实验室目录。更换 API 版本时保留旧的 SHA 与 trace 记录，建立新的独立 build 目录重新验证。

返回 [[计算机知识/80-实践/03-C++/00-C++实验室|C++ 实验室]]、[[计算机知识/10-编程语言/02-C++/00-C++-MOC|C++ MOC]] 与 [[计算机知识/40-并行与异构计算/01-CUDA/00-CUDA-MOC|CUDA 学习路线]]。


<!-- revision-2-navigation -->
## 本轮课程定位与机制补充

课程顺序与原稿入口：[[计算机知识/00-开始/课程地图/02-C++-课程地图|C++ · 课程地图]]。进一步的机制推演与反例：[[计算机知识/10-编程语言/02-C++/11-对象模型值类别与异常安全|C++ 深化：对象模型、值类别和异常安全]]。跨学科辨析：[[计算机知识/90-资源/11-跨学科概念辨析|跨学科概念辨析]]。
