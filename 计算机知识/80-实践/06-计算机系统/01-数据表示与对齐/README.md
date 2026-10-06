---
type: lab
domain: computer-science
stage: 1
status: ready
difficulty: 基础
estimated_minutes: 50
topics: [数据表示, 字节序, 对齐, C++20]
tags: [computer-science/systems, computer-science/data-representation, computer-science/practice]
---

# 数据表示与对齐

## 目标

用 C++20 观察一个 `uint32_t` 的本机字节序，再对比与主机无关的显式小端编码；用 `sizeof`/`alignof`/`offsetof` 观察结构体的对齐和填充。稳定概念见 [[计算机知识/30-计算机系统/01-数据表示字节序与对齐|数据表示、字节序与对齐]]。

## 构建与运行

```bash
cmake -S . -B build -DCMAKE_BUILD_TYPE=Debug
cmake --build build
ctest --test-dir build --output-on-failure
./build/data_representation
```

macOS 的 AppleClang 与常见 Linux Clang/GCC 均可编译这份 POSIX 无关的 C++20 代码。多配置生成器运行时要在构建、CTest 与可执行路径中加对应配置。

程序使用 `static_assert` 明确要求 8-bit byte 与占 4 byte 的 `uint32_t`。这是编译前提，因为 `bit_cast<array<byte, 4>>` 的两侧必须等大；不支持的目标会在编译时被拒绝，而不是依赖一个编译后才能执行的运行时分支。

默认命令会在本 README 所在目录创建精确的 `./build/`，它不会自动清理。完成后先用 `pwd` 确认仍在 `01-数据表示与对齐`，再只删除该目录：

```bash
cmake -E remove_directory ./build
```

如果不想在 Vault 中创建构建产物，并且本机 `/private/tmp` 存在且可写，可在子 shell 中创建唯一外部目录。`trap` 只清理 `mktemp` 刚返回的精确路径：

```bash
(
  lab_build_dir="$(mktemp -d /private/tmp/workwithllm-data-representation.XXXXXX)" || exit 1
  trap 'cmake -E remove_directory "$lab_build_dir"' EXIT
  cmake -S . -B "$lab_build_dir" -DCMAKE_BUILD_TYPE=Debug
  cmake --build "$lab_build_dir"
  ctest --test-dir "$lab_build_dir" --output-on-failure
  "$lab_build_dir/data_representation"
)
```

## 读输出

- `native_object_bytes` 是这次编译目标的原生对象表示；`explicit_little_endian` 是程序定义的持久化格式。
- `Record` 的字段偏移可能有空洞，`sizeof(Record)` 还可能包含尾部填充，以便数组中的下一个对象保持对齐。
- 静态层面只能说明显式编解码契约；本机字节序和具体 ABI 布局是运行观察，不要原样序列化 `Record`。

## 精确伴随文件

<!-- code-sync: ./CMakeLists.txt -->
```cmake
cmake_minimum_required(VERSION 3.20)
project(data_representation_alignment_lab LANGUAGES CXX)

include(CTest)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

add_executable(data_representation data_representation.cpp)
if(MSVC)
  target_compile_options(data_representation PRIVATE /W4 /permissive-)
else()
  target_compile_options(data_representation PRIVATE -Wall -Wextra -Wpedantic)
endif()

if(BUILD_TESTING)
  add_test(NAME data_representation_self_test COMMAND data_representation --self-test)
endif()
```

<!-- code-sync: ./data_representation.cpp -->
```cpp
#include <array>
#include <bit>
#include <climits>
#include <cstddef>
#include <cstdint>
#include <iomanip>
#include <iostream>
#include <string_view>

static_assert(CHAR_BIT == 8, "This teaching example requires 8-bit bytes.");
static_assert(sizeof(std::uint32_t) == 4, "This teaching example requires a four-byte uint32_t.");

struct Record {
    std::uint8_t tag;
    std::uint32_t count;
    std::uint16_t flags;
};

std::array<std::byte, 4> encode_u32_little_endian(std::uint32_t value) {
    return {
        static_cast<std::byte>(value & 0xffU),
        static_cast<std::byte>((value >> 8U) & 0xffU),
        static_cast<std::byte>((value >> 16U) & 0xffU),
        static_cast<std::byte>((value >> 24U) & 0xffU),
    };
}

std::uint32_t decode_u32_little_endian(const std::array<std::byte, 4>& bytes) {
    return std::to_integer<std::uint32_t>(bytes[0]) |
           (std::to_integer<std::uint32_t>(bytes[1]) << 8U) |
           (std::to_integer<std::uint32_t>(bytes[2]) << 16U) |
           (std::to_integer<std::uint32_t>(bytes[3]) << 24U);
}

bool self_test() {
    const std::array<std::uint32_t, 5> cases{0U, 1U, 0x12345678U, 0xffffffffU, 0xa5a55a5aU};
    for (const auto value : cases) {
        if (decode_u32_little_endian(encode_u32_little_endian(value)) != value) {
            return false;
        }
    }
    return offsetof(Record, tag) == 0 && offsetof(Record, count) % alignof(std::uint32_t) == 0 &&
           offsetof(Record, flags) % alignof(std::uint16_t) == 0 && sizeof(Record) >= 7;
}

int main(int argc, char* argv[]) {
    if (argc == 2 && std::string_view(argv[1]) == "--self-test") {
        const bool passed = self_test();
        std::cout << (passed ? "self-test passed\n" : "self-test failed\n");
        return passed ? 0 : 1;
    }

    constexpr std::uint32_t value = 0x12345678U;
    const auto explicit_bytes = encode_u32_little_endian(value);
    const auto native_bytes = std::bit_cast<std::array<std::byte, 4>>(value);

    std::cout << "native_endian=";
    if constexpr (std::endian::native == std::endian::little) {
        std::cout << "little\n";
    } else if constexpr (std::endian::native == std::endian::big) {
        std::cout << "big\n";
    } else {
        std::cout << "mixed\n";
    }

    const auto print_bytes = [](std::string_view label, const auto& bytes) {
        std::cout << label << '=';
        for (const auto byte : bytes) {
            std::cout << ' ' << std::hex << std::setw(2) << std::setfill('0')
                      << std::to_integer<unsigned int>(byte);
        }
        std::cout << std::dec << '\n';
    };

    print_bytes("native_object_bytes", native_bytes);
    print_bytes("explicit_little_endian", explicit_bytes);
    std::cout << "Record sizeof=" << sizeof(Record) << " alignof=" << alignof(Record)
              << " offsets={tag:" << offsetof(Record, tag) << ",count:" << offsetof(Record, count)
              << ",flags:" << offsetof(Record, flags) << "}\n";
    std::cout << "round_trip=0x" << std::hex << decode_u32_little_endian(explicit_bytes) << std::dec
              << '\n';
}
```

## 练习与成功标准

1. 调换 `Record` 字段顺序，重新编译并记录偏移/大小；不要预设一定变小。
2. 为显式大端编码增加一组函数和 round-trip case。
3. 成功标准：CTest 通过；能指出原生对象字节和持久化格式的边界；不把本机输出推广为 C++ 对所有 ABI 的保证。

---

**返回**：[[计算机知识/80-实践/06-计算机系统/00-计算机系统实践-MOC|计算机系统实践 MOC]] · **下一站**：[[计算机知识/80-实践/06-计算机系统/02-虚拟内存mmap与页错误/README|虚拟内存、mmap 与页错误]]


<!-- revision-2-navigation -->
## 本轮课程定位与机制补充

课程顺序与原稿入口：[[计算机知识/00-开始/课程地图/07-计算机组成原理-课程地图|计算机组成原理 · 课程地图]]。进一步的机制推演与反例：[[计算机知识/30-计算机系统/21-逻辑电路整数运算与CPU性能推演|组成原理深化：从逻辑电路到 CPU 性能]]。跨学科辨析：[[计算机知识/90-资源/11-跨学科概念辨析|跨学科概念辨析]]。
