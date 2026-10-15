#include "wwl/report_queue.hpp"
#include "wwl/detail/executor_testing.hpp"
#include <atomic>
#include <sstream>
#include <type_traits>
#include <utility>

namespace wwl {
static_assert(std::is_nothrow_move_constructible_v<WorkItem>);
BoundedReportQueue::BoundedReportQueue(std::size_t capacity) : capacity_(capacity) {
    if (capacity==0 || capacity>8) throw std::invalid_argument("queue capacity must be in [1,8]");
}
namespace {
struct Waiting {
    std::size_t& counter;
    explicit Waiting(std::size_t& value) : counter(value) {++counter;}
    ~Waiting() {--counter;}
};
}
bool BoundedReportQueue::push(WorkItem item) {
    if (item.task.input.size()>max_task_bytes) throw std::length_error("task input exceeds 512 KiB");
    std::unique_lock lock(mutex_);
    if (state_==QueueState::open && items_.size()==capacity_) {
        Waiting waiting(producers_waiting_);
        space_.wait(lock,[&]{return state_!=QueueState::open || items_.size()<capacity_;});
    }
    if (state_!=QueueState::open) return false;
    items_.push_back(std::move(item));
    lock.unlock();available_.notify_one();return true;
}
std::optional<WorkItem> BoundedReportQueue::pop() {
    std::unique_lock lock(mutex_);
    if (state_==QueueState::open && items_.empty()) {
        Waiting waiting(consumers_waiting_);
        available_.wait(lock,[&]{return state_!=QueueState::open || !items_.empty();});
    }
    if (state_==QueueState::cancelled || items_.empty()) return std::nullopt;
    WorkItem item=std::move(items_.front());items_.pop_front();
    lock.unlock();space_.notify_one();return std::optional<WorkItem>{std::move(item)};
}
void BoundedReportQueue::close() {
    {std::lock_guard lock(mutex_);if (state_==QueueState::open) state_=QueueState::draining;}
    available_.notify_all();space_.notify_all();
}
void BoundedReportQueue::cancel() noexcept {
    {std::lock_guard lock(mutex_);state_=QueueState::cancelled;items_.clear();}
    available_.notify_all();space_.notify_all();
}
QueueSnapshot BoundedReportQueue::snapshot() const {
    std::lock_guard lock(mutex_);return {state_,items_.size(),producers_waiting_,consumers_waiting_};
}
namespace {
void record_error(TaskOutcome& result,const char* message) noexcept {
    result.report.clear();result.state=TaskState::failed;
    std::size_t i=0;
    while (i+1<result.diagnostic.size() && message[i]) {result.diagnostic[i]=message[i];++i;}
    result.diagnostic[i]='\0';
}
}
std::vector<TaskOutcome> detail::run_reports_with_launcher(std::vector<ReportTask> tasks,
        RunOptions options,std::stop_token stop,const WorkerLauncher& launch) {
    if (options.workers==0 || options.workers>3) throw std::invalid_argument("workers must be in [1,3]");
    if (tasks.size()>max_report_tasks) throw std::length_error("at most 64 report tasks");
    for (const auto& task:tasks)
        if (task.input.size()>max_task_bytes) throw std::length_error("task input exceeds 512 KiB");
    BoundedReportQueue queue(options.capacity);
    std::vector<TaskOutcome> results(tasks.size()); // Never resized while workers run.
    std::vector<std::jthread> workers;workers.reserve(options.workers);
    std::atomic<bool> protocol_failure=false;
    std::stop_callback cancel_on_stop(stop,[&queue]() noexcept {queue.cancel();});
    const auto body=[&]() noexcept {
        try {
            while (auto item=queue.pop()) {
                if (stop.stop_requested()) break; // Popped but not started => cancelled.
                auto& result=results[item->index]; // Each index is assigned to exactly one task.
                try {
                    std::istringstream input(std::move(item->task.input));
                    // Do not share a possibly unsynchronized default PMR resource across workers.
                    ReportSession session(std::pmr::new_delete_resource());
                    session.replace(input,item->task.settings);
                    if (session.text().size()>max_result_bytes) throw std::length_error("report exceeds 32 MiB");
                    result.report.assign(session.text()); // Owning copy before the session is destroyed.
                    result.state=TaskState::completed;
                } catch (const std::exception& error) {record_error(result,error.what());}
                  catch (...) {record_error(result,"non-standard task exception");}
            }
        } catch (...) {protocol_failure.store(true);queue.cancel();}
    };
    try {
        for (std::size_t i=0;i<options.workers;++i) {
            auto worker=launch(body);
            if (!worker.joinable()) throw std::runtime_error("launcher returned non-joinable worker");
            workers.push_back(std::move(worker));
        }
        for (std::size_t i=0;i<tasks.size();++i)
            if (!queue.push({i,std::move(tasks[i])})) break;
        queue.close();
        for (auto& worker:workers) worker.join();
    } catch (...) {
        // Critical: jthread requests stop alone cannot wake this ordinary condition_variable.
        queue.cancel();
        for (auto& worker:workers) if (worker.joinable()) worker.join();
        throw;
    }
    if (protocol_failure.load()) throw std::runtime_error("worker queue protocol failure");
    return results;
}
std::vector<TaskOutcome> run_reports(std::vector<ReportTask> tasks,RunOptions options,std::stop_token stop) {
    return detail::run_reports_with_launcher(std::move(tasks),options,stop,
        [](std::function<void()> body) {return std::jthread(std::move(body));});
}
}
