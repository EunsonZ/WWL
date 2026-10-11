#include <wwl/report_queue.hpp>
#include <wwl/detail/executor_testing.hpp>
#include <atomic>
#include <chrono>
#include <iostream>
#include <latch>
#include <sstream>
#include <system_error>
#include <thread>

namespace {
int failures=0;
void check(bool value,const char* message) {
    if (!value) {std::cerr<<"FAIL: "<<message<<'\n';++failures;}
}
template<class F> void rejects(F action,const char* message) {
    try {action();check(false,message);} catch (const std::exception&) {}
}
template<class F> bool until(F predicate) {
    const auto deadline=std::chrono::steady_clock::now()+std::chrono::seconds(2);
    while (!predicate()) {
        if (std::chrono::steady_clock::now()>=deadline) return false;
        std::this_thread::yield();
    }
    return true;
}
wwl::WorkItem item(std::size_t index) {return {index,{"2 4 6 8",wwl::ReportSettings{}}};}
void producer_shutdown(bool cancel) {
    wwl::BoundedReportQueue queue(1);check(queue.push(item(0)),"initial push");
    bool accepted=true;
    std::jthread producer([&]{accepted=queue.push(item(1));});
    const bool waited=until([&]{return queue.snapshot().producers_waiting==1;});
    if (cancel) queue.cancel();else queue.close(); // Always wake before checking/joining.
    producer.join();check(waited,"full producer actually waited");
    check(!accepted,"shutdown rejects blocked producer");
    auto first=queue.pop();
    check(cancel ? !first : first && first->index==0,"cancel drops / close drains queued item");
    check(!queue.pop(),"finished queue pop is empty");
    check(!queue.push(item(2)),"shutdown rejects future push");
    queue.close();queue.cancel();queue.cancel();check(queue.snapshot().state==wwl::QueueState::cancelled,"idempotent shutdown");
}
void consumer_shutdown(bool cancel) {
    wwl::BoundedReportQueue queue(1);std::optional<wwl::WorkItem> popped;
    std::jthread consumer([&]{popped=queue.pop();});
    const bool waited=until([&]{return queue.snapshot().consumers_waiting==1;});
    if (cancel) queue.cancel();else queue.close();
    consumer.join();check(waited,"empty consumer actually waited");check(!popped,"shutdown wakes empty consumer");
}
}
int main() {
    using namespace wwl;
    rejects([]{BoundedReportQueue q(0);},"zero capacity");
    rejects([]{BoundedReportQueue q(9);},"large capacity");
    rejects([]{run_reports({}, {0,1});},"zero workers");
    rejects([]{run_reports({}, {4,1});},"large workers");
    rejects([]{run_reports(std::vector<ReportTask>(65));},"too many tasks");
    rejects([]{run_reports({{std::string(max_task_bytes+1,'1'),ReportSettings{}}});},"large task");
    producer_shutdown(false);producer_shutdown(true);consumer_shutdown(false);consumer_shutdown(true);
    {
        BoundedReportQueue queue(2);queue.push(item(0));auto active=queue.pop();queue.push(item(1));queue.cancel();
        check(active && active->task.input=="2 4 6 8" && !queue.pop(),"active item owns data independently of queue cancellation");
        std::istringstream input(active->task.input);ReportSession session;session.replace(input,active->task.settings);
        check(!session.text().empty(),"already acquired work may finish");
    }
    {
        BoundedReportQueue queue(1);queue.push(item(0));bool accepted=false;
        std::jthread producer([&]{accepted=queue.push(item(1));});
        const bool waited=until([&]{return queue.snapshot().producers_waiting==1;});
        auto first=queue.pop();
        const bool resumed=until([&]{return queue.snapshot().queued==1;});
        queue.close();producer.join();auto second=queue.pop();
        check(waited && resumed && accepted && first && first->index==0 && second && second->index==1,"pop frees capacity and wakes producer, preserving FIFO");
    }
    {TaskOutcome result;result.diagnostic.fill('x');check(result.error_message().size()==160,"public diagnostic read is bounded even without NUL");}
    std::string reference;
    for (std::size_t workers:{1,2,3}) {
        auto results=run_reports({{"2 4 6 8",wwl::ReportSettings{}},{"invalid",wwl::ReportSettings{}},{"2 4 6 8",wwl::ReportSettings{}}},{workers,1});
        check(results.size()==3 && results[0].state==TaskState::completed && results[1].state==TaskState::failed && results[2].state==TaskState::completed,"job failure isolated and input order preserved");
        check(!results[1].error_message().empty() && results[1].report.empty(),"failure diagnostic owns bytes");
        if (reference.empty()) reference=results[0].report;
        check(results[0].report==reference && results[2].report==reference,"worker count leaves report bytes unchanged");
    }
    check(run_reports({},{1,1}).empty(),"empty input joins cleanly");
    {
        std::stop_source stop;stop.request_stop();auto results=run_reports({{"2 4",wwl::ReportSettings{}},{"6 8",wwl::ReportSettings{}}},{2,1},stop.get_token());
        check(results[0].state==TaskState::cancelled && results[1].state==TaskState::cancelled,"pre-cancelled tasks never start");
    }
    {
        std::atomic<int> started=0,finished=0;int launches=0;bool threw=false;
        detail::WorkerLauncher launch=[&](std::function<void()> body) {
            if (++launches==3) throw std::system_error(std::make_error_code(std::errc::resource_unavailable_try_again));
            return std::jthread([&,body=std::move(body)]{++started;body();++finished;});
        };
        try {detail::run_reports_with_launcher({{"2 4",wwl::ReportSettings{}}},{3,1},{},launch);}
        catch (const std::system_error&) {threw=true;}
        check(threw && started==2 && finished==2,"partial thread launch failure wakes and joins earlier workers before rethrow");
    }
    {
        int launches=0;std::atomic<int> finished=0;
        detail::WorkerLauncher launch=[&](std::function<void()> body) {
            if (++launches==2) return std::jthread{};
            return std::jthread([&,body=std::move(body)]{body();++finished;});
        };
        rejects([&]{detail::run_reports_with_launcher({},{2,1},{},launch);},"non-joinable launcher rejected");
        check(finished==1,"invalid launcher still joins prior worker");
    }
    {
        std::stop_source stop;std::latch entered(1),release(1);std::vector<TaskOutcome> results;
        detail::WorkerLauncher launch=[&](std::function<void()> body) {
            return std::jthread([&,body=std::move(body)]{entered.count_down();release.wait();body();});
        };
        std::jthread manager([&]{results=detail::run_reports_with_launcher({{"2 4",wwl::ReportSettings{}},{"6 8",wwl::ReportSettings{}},{"1 3",wwl::ReportSettings{}}},{1,1},stop.get_token(),launch);});
        entered.wait();stop.request_stop();release.count_down();manager.join();
        check(results.size()==3,"cancelled dispatcher returned all outcomes");
        for (const auto& result:results) check(result.state==TaskState::cancelled,"stop callback cancels not-started jobs");
    }
    if (failures) return 1;
    std::cout<<"bounded queue, close/cancel, owned task lifetime, isolated failures and partial launch cleanup verified\n";
}
