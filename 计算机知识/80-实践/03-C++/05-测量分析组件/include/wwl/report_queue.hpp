#pragma once
#include <wwl/report.hpp>
#include <array>
#include <cstddef>
#include <optional>
#include <string>
#include <vector>
#include <condition_variable>
#include <deque>
#include <mutex>
#include <stop_token>

namespace wwl {
inline constexpr std::size_t max_report_tasks=64;
inline constexpr std::size_t max_task_bytes=512*1024;
inline constexpr std::size_t max_result_bytes=32*1024*1024;
struct ReportTask {
    std::string input; // Owning raw input; never a string_view saved for later.
    ReportSettings settings;
};
struct WorkItem { std::size_t index; ReportTask task; };
enum class QueueState { open, draining, cancelled };
struct QueueSnapshot {
    QueueState state;
    std::size_t queued;
    std::size_t producers_waiting;
    std::size_t consumers_waiting;
};
// Caller owns thread lifetime: this queue must outlive every push/pop caller.
// close/cancel wake callers but do not join them; destroy only after all have returned.
class BoundedReportQueue {
public:
    explicit BoundedReportQueue(std::size_t capacity);
    bool push(WorkItem item); // Validates byte limit first; false if closed/cancelled. Owns item while waiting.
    std::optional<WorkItem> pop(); // Empty after drain or cancellation.
    void close(); // Idempotent. Reject new work; drain accepted work.
    void cancel() noexcept; // Idempotent. Drop queued work and wake both sides.
    QueueSnapshot snapshot() const; // Diagnostic snapshot, not a synchronization promise.
private:
    const std::size_t capacity_;
    mutable std::mutex mutex_;
    std::condition_variable available_,space_;
    std::deque<WorkItem> items_;
    QueueState state_=QueueState::open;
    std::size_t producers_waiting_=0,consumers_waiting_=0;
};
enum class TaskState { completed, failed, cancelled };
struct TaskOutcome {
    TaskState state=TaskState::cancelled;
    std::string report;
    std::array<char,160> diagnostic{}; // Worker failure recording performs no allocation.
    std::string error_message() const {
        std::size_t size=0;while (size<diagnostic.size() && diagnostic[size]) ++size;
        return std::string(diagnostic.data(),size);
    }
};
struct RunOptions { std::size_t workers=2; std::size_t capacity=2; };
// Owns all input tasks, assigns unique indices and joins all workers before returning.
// Start is the worker's successful pop plus a false stop check. A concurrent later
// cancellation discards queued/not-started work; started work may finish normally.
// One malformed task becomes failed and does not cancel other tasks.
// Results retain input order. 1..3 workers (+ calling thread: at most 4 total), 1..8 queue slots, <=64 tasks.
std::vector<TaskOutcome> run_reports(std::vector<ReportTask> tasks, RunOptions options={},
                                     std::stop_token stop={});
}
