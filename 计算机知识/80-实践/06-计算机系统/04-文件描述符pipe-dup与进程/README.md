---
type: lab
domain: computer-science
stage: 4
status: ready
difficulty: 进阶
estimated_minutes: 60
topics: [file-descriptor, pipe, dup2, fork, C++20]
tags: [computer-science/systems, computer-science/processes, computer-science/practice]
---

# 文件描述符、pipe、dup 与进程

## 要验证的数据流

```text
父进程 pipe() -> [read end, write end]
  ├─ fork() -> 子进程 dup2(write end, STDOUT_FILENO) -> write(stdout)
  └─ close(write end) -> read(read end) 直到 EOF -> waitpid(child)
```

`dup2` 修改的是子进程的文件描述符表；子进程向 1 号描述符写入时，字节进入 pipe。父进程必须关闭自己持有的 write end，否则即使子进程退出，父进程的 `read` 也可能等不到 EOF。稳定课中的进程/调度/IPC 前提见 [[计算机知识/30-计算机系统/09-进程线程调度同步与IPC|进程、线程、调度、同步与 IPC]]，FD 与打开文件状态见 [[计算机知识/30-计算机系统/12-VFS文件描述符Inode目录与路径解析|VFS、文件描述符、inode 与路径解析]]。它也连接 [[计算机知识/20-操作系统/01-Linux/06-用户权限进程与作业控制|用户、权限、进程与作业控制]] 与 [[计算机知识/30-计算机系统/02-进程虚拟地址空间与内存映射|进程的地址空间边界]]。

## 构建与运行

```bash
cmake -S . -B build -DCMAKE_BUILD_TYPE=Debug
cmake --build build
ctest --test-dir build --output-on-failure
./build/fd_pipe_demo
```

实验要求 macOS 或 Linux 的 POSIX `pipe`/`fork`/`dup2`/`waitpid`；Windows 不在保证范围。它不访问文件系统，不向外部 PID 发信号，不留下子进程。

> [!warning] `fork` 时的单线程前提
> 这份教学程序在 `fork()` 时只有一个线程，所以其窄小 child 路径可用于当前实验。不要把里面的 C++ 字符串/异常路径原样搬到“多线程进程 fork 后、exec 前”的 child；那个窗口应遵守目标平台的 async-signal-safe 契约并尽快 `exec`，或评估 `posix_spawn`。本实验的 CTest 只验证当前单线程正常路径。

默认命令会在本 README 所在目录创建精确的 `./build/`，它不会自动清理。完成后先用 `pwd` 确认仍在 `04-文件描述符pipe-dup与进程`，再只删除该目录：

```bash
cmake -E remove_directory ./build
```

如果不想在 Vault 中创建构建产物，并且本机 `/private/tmp` 存在且可写，可在子 shell 中创建唯一外部目录。`trap` 只清理 `mktemp` 刚返回的精确路径：

```bash
(
  lab_build_dir="$(mktemp -d /private/tmp/workwithllm-fd-pipe.XXXXXX)" || exit 1
  trap 'cmake -E remove_directory "$lab_build_dir"' EXIT
  cmake -S . -B "$lab_build_dir" -DCMAKE_BUILD_TYPE=Debug
  cmake --build "$lab_build_dir"
  ctest --test-dir "$lab_build_dir" --output-on-failure
  "$lab_build_dir/fd_pipe_demo"
)
```

## 精确伴随文件

<!-- code-sync: ./CMakeLists.txt -->
```cmake
cmake_minimum_required(VERSION 3.20)
project(file_descriptor_pipe_lab LANGUAGES CXX)

if(NOT UNIX)
  message(FATAL_ERROR "fd_pipe_demo requires a UNIX/POSIX platform such as macOS or Linux")
endif()

include(CTest)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

add_executable(fd_pipe_demo fd_pipe_demo.cpp)
if(MSVC)
  target_compile_options(fd_pipe_demo PRIVATE /W4 /permissive-)
else()
  target_compile_options(fd_pipe_demo PRIVATE -Wall -Wextra -Wpedantic)
endif()

if(BUILD_TESTING)
  add_test(NAME fd_pipe_self_test COMMAND fd_pipe_demo --self-test)
endif()
```

<!-- code-sync: ./fd_pipe_demo.cpp -->
```cpp
#include <cerrno>
#include <cstring>
#include <iostream>
#include <stdexcept>
#include <string>
#include <string_view>

#include <sys/types.h>
#include <sys/wait.h>
#include <unistd.h>

class FileDescriptor {
public:
    explicit FileDescriptor(int value = -1) : value_(value) {}
    ~FileDescriptor() {
        if (value_ >= 0) {
            ::close(value_);
        }
    }
    FileDescriptor(const FileDescriptor&) = delete;
    FileDescriptor& operator=(const FileDescriptor&) = delete;
    FileDescriptor(FileDescriptor&& other) noexcept : value_(other.release()) {}
    FileDescriptor& operator=(FileDescriptor&& other) noexcept {
        if (this != &other) {
            if (value_ >= 0) {
                ::close(value_);
            }
            value_ = other.release();
        }
        return *this;
    }
    int get() const { return value_; }
    int release() {
        const int result = value_;
        value_ = -1;
        return result;
    }

private:
    int value_;
};

void throw_system_error(std::string_view operation) {
    throw std::runtime_error(std::string(operation) + ": " + std::strerror(errno));
}

void write_all(int fd, std::string_view text) {
    while (!text.empty()) {
        const ssize_t written = ::write(fd, text.data(), text.size());
        if (written < 0) {
            if (errno == EINTR) {
                continue;
            }
            throw_system_error("write");
        }
        text.remove_prefix(static_cast<std::size_t>(written));
    }
}

std::string read_all(int fd) {
    std::string result;
    char buffer[256];
    for (;;) {
        const ssize_t count = ::read(fd, buffer, sizeof(buffer));
        if (count == 0) {
            break;
        }
        if (count < 0) {
            if (errno == EINTR) {
                continue;
            }
            throw_system_error("read");
        }
        result.append(buffer, static_cast<std::size_t>(count));
    }
    return result;
}

std::string capture_child_stdout(std::string_view message) {
    int raw_pipe[2];
    if (::pipe(raw_pipe) != 0) {
        throw_system_error("pipe");
    }
    FileDescriptor read_end(raw_pipe[0]);
    FileDescriptor write_end(raw_pipe[1]);

    // This teaching process is single-threaded at fork(). Do not generalize the
    // C++ child path to a multi-threaded parent; keep such children within the
    // platform's async-signal-safe contract until exec, or use posix_spawn.
    const pid_t child = ::fork();
    if (child < 0) {
        throw_system_error("fork");
    }
    if (child == 0) {
        ::close(read_end.release());
        if (write_end.get() != STDOUT_FILENO) {
            if (::dup2(write_end.get(), STDOUT_FILENO) < 0) {
                _exit(120);
            }
            ::close(write_end.release());
        } else {
            write_end.release();
        }
        try {
            write_all(STDOUT_FILENO, message);
        } catch (...) {
            _exit(121);
        }
        _exit(0);
    }

    ::close(write_end.release());
    const std::string captured = read_all(read_end.get());
    int status = 0;
    while (::waitpid(child, &status, 0) < 0) {
        if (errno != EINTR) {
            throw_system_error("waitpid");
        }
    }
    if (!WIFEXITED(status) || WEXITSTATUS(status) != 0) {
        throw std::runtime_error("child did not exit successfully");
    }
    return captured;
}

int main(int argc, char* argv[]) {
    const std::string message = "child stdout reached parent through pipe\n";
    try {
        const std::string captured = capture_child_stdout(message);
        if (argc == 2 && std::string_view(argv[1]) == "--self-test") {
            const bool passed = captured == message;
            std::cout << (passed ? "self-test passed\n" : "self-test failed\n");
            return passed ? 0 : 1;
        }
        std::cout << "parent_pid=" << ::getpid() << '\n'
                  << "captured_bytes=" << captured.size() << '\n'
                  << "captured=" << captured;
    } catch (const std::exception& error) {
        std::cerr << "error: " << error.what() << '\n';
        return 1;
    }
}
```

## 读程序的三个细节

1. `FileDescriptor` 将 `close` 绑定到作用域，又用 `release()` 防止手工关闭后析构重复关闭。
2. `read`/`write` 可短读短写，也可被信号中断；循环不把“返回正数”误当作完整传输。
3. fork 后子进程使用 `_exit`，避免重复刷新从父进程复制的 C++ iostream 缓冲区；子进程只执行很窄的已知路径。这条路径仍只能在本实验的单线程 fork 前提下解读，不是多线程 fork-child 的通用模板。

## 练习与成功标准

1. 在实验副本中暂时注释父进程关闭 write end 的一行，预测阻塞点；只用终端的 `Ctrl-C` 中止本次实验，立即恢复源码，不对任意 PID 用 `kill`/`pkill`。
2. 把 message 扩展至大于常见 pipe 容量，解释为何父子必须并发地写与读，不能先等子进程退出再读。
3. 成功标准：CTest 验证捕获字节精确相等；正常运行打印父 PID、字节数和捕获文本；能指出 pipe EOF 与所有 write end 关闭的关系。

---

**上一站**：[[计算机知识/80-实践/06-计算机系统/03-缓存局部性benchmark/README|缓存局部性 benchmark]] · **下一站**：[[计算机知识/80-实践/06-计算机系统/05-文件系统原子替换与fsync/README|文件系统原子替换与 fsync]] · **返回**：[[计算机知识/80-实践/06-计算机系统/00-计算机系统实践-MOC|计算机系统实践 MOC]]


<!-- revision-2-navigation -->
## 本轮课程定位与机制补充

课程顺序与原稿入口：[[计算机知识/00-开始/课程地图/08-操作系统-课程地图|操作系统 · 课程地图]]。进一步的机制推演与反例：[[计算机知识/20-操作系统/02-操作系统原理/03-虚拟内存置换文件系统与崩溃边界|操作系统：虚拟内存、置换与崩溃一致性]]。跨学科辨析：[[计算机知识/90-资源/11-跨学科概念辨析|跨学科概念辨析]]。
