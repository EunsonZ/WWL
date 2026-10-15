#include <atomic>
#include <iostream>
#include <mutex>
#include <thread>
#include <utility>
#include <vector>

class Progress {
public:
    void record(int tokens) {
        const std::lock_guard lock(mutex_);
        ++completed_;
        tokens_ += tokens;
    }

    std::pair<int, int> snapshot() const {
        const std::lock_guard lock(mutex_);
        return {completed_, tokens_};
    }

private:
    mutable std::mutex mutex_;
    int completed_ = 0;
    int tokens_ = 0;
};

int main() {
    std::atomic<int> started{0};
    Progress progress;
    std::vector<std::thread> workers;
    for (int i = 0; i < 4; ++i) {
        workers.emplace_back([&started, &progress, i] {
            started.fetch_add(1, std::memory_order_relaxed);
            progress.record(i + 1);
        });
    }
    for (auto& worker : workers) {
        worker.join();
    }
    const auto [completed, tokens] = progress.snapshot();
    if (started.load(std::memory_order_relaxed) != 4 || completed != 4 || tokens != 10) {
        std::cerr << "concurrency contract failed\n";
        return 1;
    }
    std::cout << completed << ' ' << tokens << '\n';
}
