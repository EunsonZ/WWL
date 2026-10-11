#include <wwl/report.hpp>
#include <sstream>
#include <iostream>
int main() {
    std::istringstream input("2 4 6 8");
    wwl::ReportSession session;
    session.replace(input,wwl::ReportSettings{wwl::Calibration{500,1000},
                    std::chrono::milliseconds{250},wwl::WindowSpec{2,1},"sensor-A"});
    if (session.windows().size()!=3 || session.windows()[0].statistics.mean.value!=2.5 ||
        session.windows()[2].last_sample_time!=std::chrono::milliseconds{750}) return 1;
    std::cout << session.text();
}
