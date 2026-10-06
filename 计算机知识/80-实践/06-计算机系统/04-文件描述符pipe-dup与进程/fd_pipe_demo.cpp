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
