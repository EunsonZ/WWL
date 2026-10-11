#pragma once
#include <wwl/report.hpp>
#include <coroutine>
#include <cstddef>
#include <exception>
#include <memory_resource>
#include <sstream>
#include <stdexcept>
#include <string>
#include <utility>

namespace wwl::advanced {
// Every operation, including destruction and diagnostics, is single-thread only.
enum class TaskState { empty, created, suspended, completed, cancelled, failed };

class OwnedReportTask {
public:
    struct promise_type;
    OwnedReportTask() noexcept = default;
    OwnedReportTask(const OwnedReportTask&) = delete;
    OwnedReportTask& operator=(const OwnedReportTask&) = delete;
    OwnedReportTask(OwnedReportTask&& other) noexcept
        : handle_(std::exchange(other.handle_, {})),
          last_(std::exchange(other.last_, TaskState::empty)) {}
    OwnedReportTask& operator=(OwnedReportTask&& other) noexcept {
        if (this != &other) {
            destroy_frame();
            handle_ = std::exchange(other.handle_, {});
            last_ = std::exchange(other.last_, TaskState::empty);
        }
        return *this;
    }
    ~OwnedReportTask() { destroy_frame(); }

    TaskState state() const noexcept;
    // True means a resume occurred, not that it completed successfully.
    bool resume();
    // Only created/suspended tasks are cancelled. Terminal states are preserved.
    bool cancel() noexcept;
    // Returns an owning value once, destroys the completed frame; rethrows failure.
    std::string take_report();
    void rethrow_if_failed() const;
    // Counts live promise objects, NOT heap allocations, bytes, or all resources.
    static std::size_t live_frames() noexcept { return live_frames_; }

    struct promise_type {
        promise_type() noexcept { ++live_frames_; }
        ~promise_type() { --live_frames_; }
        OwnedReportTask get_return_object() noexcept {
            return OwnedReportTask{Handle::from_promise(*this)};
        }
        std::suspend_always initial_suspend() const noexcept { return {}; }
        std::suspend_always final_suspend() const noexcept { return {}; }
        void return_value(std::string value) noexcept {
            report = std::move(value);
            phase = TaskState::completed;
        }
        void unhandled_exception() noexcept {
            error = std::current_exception();
            phase = TaskState::failed;
        }
        TaskState phase = TaskState::created;
        std::string report;
        std::exception_ptr error;
    };
private:
    using Handle = std::coroutine_handle<promise_type>;
    explicit OwnedReportTask(Handle handle) noexcept : handle_(handle) {}
    void destroy_frame() noexcept {
        if (handle_) {
            handle_.destroy();
            handle_ = {};
        }
    }
    Handle handle_{};
    TaskState last_ = TaskState::empty;
    inline static std::size_t live_frames_ = 0;
};

inline TaskState OwnedReportTask::state() const noexcept {
    return handle_ ? handle_.promise().phase : last_;
}
inline bool OwnedReportTask::resume() {
    const auto phase = state();
    if (phase != TaskState::created && phase != TaskState::suspended) return false;
    // No user callbacks, handles, threads, or scheduler registrations escape.
    handle_.resume();
    if (!handle_.done()) handle_.promise().phase = TaskState::suspended;
    return true;
}
inline bool OwnedReportTask::cancel() noexcept {
    const auto phase = state();
    if (phase != TaskState::created && phase != TaskState::suspended) return false;
    destroy_frame();
    last_ = TaskState::cancelled;
    return true;
}
inline void OwnedReportTask::rethrow_if_failed() const {
    if (state() == TaskState::failed) std::rethrow_exception(handle_.promise().error);
}
inline std::string OwnedReportTask::take_report() {
    rethrow_if_failed();
    if (!handle_ || state() != TaskState::completed)
        throw std::logic_error("report is not completed or was already taken");
    std::string result = std::move(handle_.promise().report);
    destroy_frame();
    last_ = TaskState::completed;
    return result;
}

// By-value parameters become owned coroutine parameters before initial suspension.
// This is a free function: no captured lambda closure or implicit this must survive.
inline OwnedReportTask make_owned_report(std::string input,
                                        ReportSettings settings = ReportSettings{}) {
    std::istringstream stream(std::move(input));
    ReportSession session(std::pmr::new_delete_resource());
    session.replace(stream, settings);
    co_await std::suspend_always{}; // Session and its snapshot survive this pause.
    co_return std::string(session.text()); // Copy the borrow BEFORE Session dies.
}
} // namespace wwl::advanced
