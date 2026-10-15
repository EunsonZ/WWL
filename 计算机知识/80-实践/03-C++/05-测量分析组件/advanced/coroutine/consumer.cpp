#include "owned_report_task.hpp"
#include <iostream>
#include <string>
#include <utility>

int main() {
    using namespace wwl::advanced;
    try {
        OwnedReportTask task;
        {
            std::string input = "2 4 6 8";
            wwl::ReportSettings settings{wwl::Calibration{500, 1000},
                std::chrono::milliseconds{250}, wwl::WindowSpec{2, 1}, "sensor-A"};
            task = make_owned_report(input, settings);
            input = "bad"; // Neither this object nor settings needs to survive.
        }
        if (task.state() != TaskState::created || !task.resume() ||
            task.state() != TaskState::suspended) return 1;
        auto owner = std::move(task);
        if (task.state() != TaskState::empty || task.resume() || !owner.resume() ||
            owner.state() != TaskState::completed) return 2;
        const std::string report = owner.take_report();
        if (OwnedReportTask::live_frames() != 0 || owner.resume() ||
            report.find("mean_mV=2.5") == std::string::npos ||
            report.find("last_ms=750") == std::string::npos) return 3;
        std::cout << report << "consumer: owned result survives frame destruction\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "consumer failed: " << error.what() << '\n';
        return 4;
    }
}
