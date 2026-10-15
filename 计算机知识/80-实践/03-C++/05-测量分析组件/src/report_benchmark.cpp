#include <wwl/report_queue.hpp>
#include <algorithm>
#include <chrono>
#include <iostream>
#include <stdexcept>

int main() {
    try {
        std::string raw;
        for (std::size_t i=0;i<2048;++i) {raw+=std::to_string((i*17)%4096);raw+=' ';}
        std::vector<wwl::ReportTask> tasks;
        for (std::size_t i=0;i<24;++i)
            tasks.push_back({raw,wwl::ReportSettings{wwl::Calibration{},std::chrono::milliseconds{1},wwl::WindowSpec{32,16},"benchmark"}});
        std::size_t reference=0;std::string reference_report;
        const auto run=[&](std::size_t workers) {
            auto results=wwl::run_reports(tasks,{workers,2}); // Copy, startup, execution and join are all timed.
            std::size_t bytes=0;
            for (const auto& result:results) {
                if (result.state!=wwl::TaskState::completed) throw std::runtime_error("benchmark task failed");
                if (reference_report.empty()) reference_report=result.report;
                if (reference_report!=result.report) throw std::runtime_error("benchmark report text differs");
                bytes+=result.report.size();
            }
            if (reference && reference!=bytes) throw std::runtime_error("benchmark result bytes differ");
            reference=bytes;return bytes;
        };
        std::cout<<"workers,trial,microseconds,report_bytes\n";
        for (std::size_t workers:{1,2,3}) {
            run(workers); // One warmup, excluded from samples.
            std::vector<long long> samples;
            for (int trial=1;trial<=7;++trial) {
                const auto before=std::chrono::steady_clock::now();const auto bytes=run(workers);
                const auto elapsed=std::chrono::duration_cast<std::chrono::microseconds>(std::chrono::steady_clock::now()-before).count();
                samples.push_back(elapsed);std::cout<<workers<<','<<trial<<','<<elapsed<<','<<bytes<<'\n';
            }
            std::sort(samples.begin(),samples.end());
            std::cerr<<"workers="<<workers<<" min_us="<<samples.front()<<" median_us="<<samples[3]<<" max_us="<<samples.back()<<'\n';
        }
        std::cout.flush();if (!std::cout) throw std::runtime_error("benchmark output failed");
    } catch (const std::exception& error) {std::cerr<<error.what()<<'\n';return 2;}
}
