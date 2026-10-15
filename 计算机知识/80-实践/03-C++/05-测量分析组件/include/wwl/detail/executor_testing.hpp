#pragma once
#include <wwl/report_queue.hpp>
#include <functional>
#include <thread>
namespace wwl::detail {
// Internal test seam: default production launcher is std::jthread.
// A test launcher must return a joinable thread running exactly the supplied body.
using WorkerLauncher=std::function<std::jthread(std::function<void()>)>;
std::vector<TaskOutcome> run_reports_with_launcher(std::vector<ReportTask> tasks,
    RunOptions options,std::stop_token stop,const WorkerLauncher& launch);
}
