#include "wwl/report_queue.hpp"
#include <charconv>
#include <fstream>
#include <iostream>
namespace {
std::size_t number(const char* value) {
    const std::string_view text(value);std::size_t result{};
    auto [end,error]=std::from_chars(text.data(),text.data()+text.size(),result);
    if (error!=std::errc{} || end!=text.data()+text.size()) throw std::invalid_argument("complete integer required");
    return result;
}
std::string read_limited(const std::filesystem::path& path) {
    std::ifstream input(path,std::ios::binary);
    if (!input) throw std::runtime_error("cannot open batch input");
    std::string text;std::array<char,4096> buffer{};
    while (input.read(buffer.data(),buffer.size()) || input.gcount()>0) {
        const auto size=static_cast<std::size_t>(input.gcount());
        if (size>wwl::max_task_bytes-text.size()) throw std::length_error("task input exceeds 512 KiB");
        text.append(buffer.data(),size);
    }
    if (input.bad() || (!input.eof() && input.fail())) throw std::runtime_error("batch input read failed");
    return text;
}
}
int main(int argc,char** argv) {
    try {
        wwl::RunOptions options;std::vector<wwl::ReportTask> tasks;bool seen_workers=false,seen_capacity=false;
        for (int i=1;i<argc;++i) {
            const std::string_view word(argv[i]);
            if (word=="--workers" || word=="--capacity") {
                bool& seen=word=="--workers" ? seen_workers : seen_capacity;
                if (seen || i+1==argc) throw std::invalid_argument("duplicate option or missing value");
                seen=true;auto value=number(argv[++i]);
                if (word=="--workers") options.workers=value;else options.capacity=value;
            } else {
                if (word.starts_with("--")) throw std::invalid_argument("unknown batch option");
                if (tasks.size()==wwl::max_report_tasks) throw std::length_error("at most 64 report tasks");
                tasks.push_back({read_limited(std::filesystem::path(word)),wwl::ReportSettings{}});
            }
        }
        if (tasks.empty()) throw std::invalid_argument("usage: measurement_batch --workers N --capacity N FILE...");
        const auto results=wwl::run_reports(std::move(tasks),options);
        int status=0;
        for (std::size_t i=0;i<results.size();++i) {
            std::cout << "task=" << i << " ";
            if (results[i].state==wwl::TaskState::completed) std::cout << "completed\n" << results[i].report;
            else {status=2;std::cout << (results[i].state==wwl::TaskState::failed ? "failed: " : "cancelled: ")
                                      << results[i].error_message() << '\n';}
        }
        std::cout.flush();if (!std::cout) throw std::runtime_error("batch output failed");
        return status;
    } catch (const std::exception& error) {std::cerr << "measurement_batch: " << error.what() << '\n';return 2;}
}
