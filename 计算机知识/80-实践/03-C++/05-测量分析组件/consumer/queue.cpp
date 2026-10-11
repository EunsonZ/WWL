#include <wwl/report_queue.hpp>
#include <iostream>
int main() {
    std::vector<wwl::ReportTask> tasks;
    tasks.push_back({"2 4 6 8",wwl::ReportSettings{}});
    tasks.push_back({"2 invalid",wwl::ReportSettings{}});
    tasks.push_back({"1 3",wwl::ReportSettings{}});
    const auto result=wwl::run_reports(std::move(tasks),{2,1});
    if (result.size()!=3 || result[0].state!=wwl::TaskState::completed ||
        result[1].state!=wwl::TaskState::failed || result[2].state!=wwl::TaskState::completed) return 1;
    std::stop_source source;source.request_stop();
    const auto cancelled=wwl::run_reports({{"2 4",wwl::ReportSettings{}}},{1,1},source.get_token());
    if (cancelled[0].state!=wwl::TaskState::cancelled) return 1;
    std::cout << "queue consumer: ordered results, isolated failure, cancellation and join verified\n";
}
