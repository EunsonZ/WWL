#include <type_traits>
#include <wwl/report.hpp>
import wwl.measurement;
static_assert(std::is_same_v<wwl::ReportSession, wwl::modules::ReportSession>);
static_assert(std::is_same_v<wwl::Calibration, wwl::modules::Calibration>);
int main() { return wwl::modules::interface_revision() == 1 ? 0 : 1; }
