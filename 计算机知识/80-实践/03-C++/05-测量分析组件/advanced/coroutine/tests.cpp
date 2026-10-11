#include "owned_report_task.hpp"
#include <iostream>
#include <sstream>
#include <string>
#include <type_traits>
#include <utility>

using wwl::advanced::OwnedReportTask;
using wwl::advanced::TaskState;
using wwl::advanced::make_owned_report;
static_assert(!std::is_copy_constructible_v<OwnedReportTask>);
static_assert(!std::is_copy_assignable_v<OwnedReportTask>);
static_assert(std::is_nothrow_move_constructible_v<OwnedReportTask>);
static_assert(std::is_nothrow_move_assignable_v<OwnedReportTask>);
static_assert(std::is_same_v<decltype(std::declval<OwnedReportTask&>().take_report()), std::string>);

int failures = 0;
void check(bool value, const char* message) {
    if (!value) { ++failures; std::cerr << "FAIL: " << message << '\n'; }
}
template<class F> void throws(F action, const char* message) {
    bool caught = false;
    try { action(); } catch (const std::exception&) { caught = true; }
    check(caught, message);
}
std::string reference(const std::string& input, const wwl::ReportSettings& settings) {
    std::istringstream stream(input);
    wwl::ReportSession session(std::pmr::new_delete_resource());
    session.replace(stream, settings);
    return std::string(session.text());
}
// Test-only coroutine exercises unhandled_exception after a real body suspension.
OwnedReportTask fail_after_pause() {
    co_await std::suspend_always{};
    throw std::runtime_error("injected after pause");
    co_return std::string{};
}
int main() {
    try {
        check(OwnedReportTask::live_frames() == 0, "initial zero");
        OwnedReportTask empty;
        check(empty.state() == TaskState::empty && !empty.resume() && !empty.cancel(), "empty safe");
        throws([&] { empty.take_report(); }, "empty result rejected");
        const wwl::ReportSettings settings{wwl::Calibration{500,1000},
            std::chrono::milliseconds{250},wwl::WindowSpec{2,1},"sensor-A"};
        const auto expected = reference("2 4 6 8", settings);
        std::string result;
        {
            OwnedReportTask task;
            {
                std::string input = "2 4 6 8";
                auto local_settings = settings;
                task = make_owned_report(input, local_settings);
                input.assign(10000, 'x');
                local_settings = wwl::ReportSettings{};
            }
            check(task.state() == TaskState::created && OwnedReportTask::live_frames() == 1, "created owns frame");
            throws([&] { task.take_report(); }, "early read rejected");
            check(task.resume() && task.state() == TaskState::suspended, "actual body suspension");
            throws([&] { task.take_report(); }, "suspended read rejected");
            check(task.resume() && task.state() == TaskState::completed, "normal final suspension");
            check(OwnedReportTask::live_frames() == 1, "completion retains promise");
            check(!task.resume() && !task.cancel(), "terminal does not resume or cancel");
            result = task.take_report();
            check(task.state() == TaskState::completed && OwnedReportTask::live_frames() == 0, "take destroys frame");
            throws([&] { task.take_report(); }, "result consumed only once");
        }
        check(result == expected && result.find("mean_mV=2.5") != std::string::npos, "owned output after owner and inputs die");
        for (bool start : {false, true}) {
            auto task = make_owned_report("2 4 6 8");
            if (start) check(task.resume(), "start cancellable frame");
            check(task.cancel() && task.state() == TaskState::cancelled, "cancel active frame");
            check(OwnedReportTask::live_frames() == 0 && !task.resume() && !task.cancel(), "cancel releases and is idempotent");
            throws([&] { task.take_report(); }, "cancelled read rejected");
        }
        {
            auto bad = make_owned_report("2 4oops 6");
            check(bad.resume() && bad.state() == TaskState::failed, "parse exception stored");
            check(!bad.resume() && !bad.cancel(), "failed terminal preserved");
            throws([&] { bad.rethrow_if_failed(); }, "failed exception rethrown");
            throws([&] { bad.take_report(); }, "failed result rethrows");
            check(OwnedReportTask::live_frames() == 1, "failed promise awaits owner cleanup");
        }
        check(OwnedReportTask::live_frames() == 0, "failed destructor releases");
        {
            auto bad = fail_after_pause();
            check(bad.resume() && bad.state() == TaskState::suspended, "fault fixture paused");
            check(bad.resume() && bad.state() == TaskState::failed, "exception after pause stored");
            auto moved_failure = std::move(bad);
            check(bad.state() == TaskState::empty, "failed owner moves");
            throws([&] { moved_failure.take_report(); }, "moved failure rethrows");
        }
        check(OwnedReportTask::live_frames() == 0, "post-pause failure releases");
        {
            auto task = make_owned_report("2 4 6 8", settings);
            check(task.resume() && task.resume(), "prepare completed move");
            auto moved = std::move(task);
            check(task.state() == TaskState::empty && moved.take_report() == expected, "completed owner moves");
        }
        for (int resumes : {0, 1, 2}) {
            { auto task = make_owned_report("2 4 6 8");
              for (int i = 0; i < resumes; ++i) check(task.resume(), "prepare abandonment"); }
            check(OwnedReportTask::live_frames() == 0, "destructor releases every reachable pause");
        }
        {
            auto from = make_owned_report("2 4 6 8", settings);
            check(from.resume(), "prepare move");
            auto moved = std::move(from);
            check(from.state() == TaskState::empty && !from.resume() && !from.cancel(), "move source empty");
            auto replaced = make_owned_report("0 1");
            check(replaced.resume() && OwnedReportTask::live_frames() == 2, "two suspended owners");
            replaced = std::move(moved);
            check(moved.state() == TaskState::empty && OwnedReportTask::live_frames() == 1, "move assignment destroys old frame");
            auto* alias = &replaced;
            replaced = std::move(*alias);
            check(replaced.state() == TaskState::suspended && OwnedReportTask::live_frames() == 1, "self move safe");
            check(replaced.resume() && replaced.take_report() == expected, "moved frame resumes correctly");
        }
        check(OwnedReportTask::live_frames() == 0, "moves release exactly once");
        for (const std::string input : {std::string{}, std::string{"1"}, std::string{"0 4095"}}) {
            auto task = make_owned_report(input);
            check(task.resume() && task.resume(), "alternate input resumes");
            check(task.take_report() == reference(input, wwl::ReportSettings{}), "alternate input matches installed API");
        }
    } catch (const std::exception& error) {
        ++failures;
        std::cerr << "unexpected exception: " << error.what() << '\n';
    }
    check(OwnedReportTask::live_frames() == 0, "final frame count");
    std::cout << "coroutine contracts: live_frames=" << OwnedReportTask::live_frames()
              << " failures=" << failures << '\n';
    return failures == 0 ? 0 : 1;
}
