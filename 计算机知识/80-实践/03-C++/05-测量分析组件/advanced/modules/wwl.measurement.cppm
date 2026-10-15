module;
#include <wwl/report.hpp>
export module wwl.measurement;

// Existing entities remain attached to the global module: one implementation,
// one type identity. These exported aliases are the named-module facade.
export namespace wwl::modules {
using ::wwl::RawCode;
using ::wwl::Calibration;
using ::wwl::Batch;
using ::wwl::Seconds;
using ::wwl::Statistics;
using ::wwl::WindowSpec;
using ::wwl::ReportSettings;
using ::wwl::WindowStatistics;
using ::wwl::ReportSession;
using ::wwl::describe;
using ::wwl::read_batch;
// This function is genuinely attached to wwl.measurement and is defined in
// an implementation unit; importing its declaration is not linking its body.
int interface_revision() noexcept;
}
