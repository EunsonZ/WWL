#include "wwl/report.hpp"
#include <algorithm>
#include <charconv>
#include <fstream>
#include <limits>
#include <stdexcept>
#include <utility>

namespace wwl {
WindowSpec::WindowSpec(std::size_t width, std::size_t hop) : width_(width), hop_(hop) {
    if (width == 0 || width > max_samples || hop == 0 || hop > max_samples)
        throw std::invalid_argument("window and hop must be in [1,65536]");
}
ReportSettings::ReportSettings(Calibration calibration, std::chrono::milliseconds interval,
                               WindowSpec window, std::string_view label)
    : calibration_(calibration), interval_(interval), window_(window), label_size_(label.size()) {
    if (interval.count() < 1 || interval.count() > 86400000)
        throw std::invalid_argument("interval-ms must be in [1,86400000]");
    if (label.empty() || label.size() > label_.size())
        throw std::invalid_argument("label must contain 1..40 ASCII letters, digits, _ or -");
    for (char c : label)
        if (!((c>='a' && c<='z') || (c>='A' && c<='Z') || (c>='0' && c<='9') || c=='_' || c=='-'))
            throw std::invalid_argument("label must contain 1..40 ASCII letters, digits, _ or -");
    std::copy(label.begin(),label.end(),label_.begin());
}
std::string ReportSettings::label() const { return {label_.data(),label_size_}; }
struct ReportSession::Snapshot {
    ReportSettings settings;
    Batch batch;
    std::pmr::vector<WindowStatistics> windows;
    std::pmr::string text;
    Snapshot(ReportSettings configuration, Batch input, std::pmr::memory_resource* resource)
        : settings(configuration), batch(std::move(input)), windows(resource), text(resource) {}
};
void ReportSession::Deleter::operator()(Snapshot* pointer) const noexcept {
    std::pmr::polymorphic_allocator<Snapshot>{resource}.delete_object(pointer);
}
ReportSession::ReportSession(std::pmr::memory_resource* resource)
    : resource_(resource), current_(nullptr,Deleter{resource}) {
    if (!resource) throw std::invalid_argument("resource must be non-null");
}
ReportSession::~ReportSession() = default;
namespace {
template<class Number> void append_number(std::pmr::string& text, Number number) {
    std::array<char,128> buffer{};
    const auto [end,error] = std::to_chars(buffer.data(),buffer.data()+buffer.size(),number);
    if (error != std::errc{}) throw std::runtime_error("number formatting failed");
    text.append(buffer.data(),end);
}
void append_field(std::pmr::string& text, std::string_view key, auto number) {
    text.append(key); append_number(text,number);
}
}
void ReportSession::replace(std::istream& input, ReportSettings settings) {
    // Input parsing owns its vector; no old state changes until the final pointer swap.
    const Seconds interval{std::chrono::duration<double>(settings.interval()).count()};
    auto batch = read_batch(input,settings.calibration(),interval);
    std::pmr::polymorphic_allocator<Snapshot> allocator{resource_};
    std::unique_ptr<Snapshot,Deleter> next{
        allocator.new_object<Snapshot>(settings,std::move(batch),resource_),Deleter{resource_}};
    const auto codes = next->batch.codes();
    const auto window = settings.window();
    const auto window_count = codes.size() < window.width() ? 0 :
                              1+(codes.size()-window.width())/window.hop();
    next->windows.reserve(window_count);
    for (std::size_t index=0;index<window_count;++index) {
        const auto begin = index*window.hop();
        const auto end = begin+window.width();
        const auto stats = describe_codes(codes.subspan(begin,window.width()),settings.calibration());
        // Full windows are never empty; integer millisecond time is bounded below 2^43.
        next->windows.push_back({begin,end,settings.interval()*static_cast<std::int64_t>(begin),
                                 settings.interval()*static_cast<std::int64_t>(end-1),*stats});
    }
    auto& text = next->text;
    text.append("label="); text.append(settings.label());
    append_field(text," count=",codes.size());
    append_field(text," interval_ms=",settings.interval().count());
    append_field(text," gain_uV_per_code=",settings.calibration().gain());
    append_field(text," offset_uV=",settings.calibration().offset());
    append_field(text," window=",window.width()); append_field(text," hop=",window.hop());
    append_field(text," windows=",window_count); text.append("\n");
    for (const auto& item : next->windows) {
        append_field(text,"begin=",item.begin); append_field(text," end=",item.end);
        append_field(text," first_ms=",item.first_sample_time.count());
        append_field(text," last_ms=",item.last_sample_time.count());
        append_field(text," sum_mV=",item.statistics.sum.value);
        append_field(text," mean_mV=",item.statistics.mean.value);
        append_field(text," population_variance_mV2=",item.statistics.population_variance.value);
        append_field(text," rms_squared_mV2=",item.statistics.rms_squared.value); text.append("\n");
    }
    current_.swap(next); // Same resource, trivially swappable pointer deleters, no throwing work.
}
std::span<const WindowStatistics> ReportSession::windows() const & noexcept {
    if (!current_) return {};
    return current_->windows;
}
std::string_view ReportSession::text() const & noexcept {
    if (!current_) return {};
    return current_->text;
}
std::optional<ReportSettings> ReportSession::settings() const {
    if (!current_) return std::nullopt;
    return current_->settings;
}
namespace {
template<class Integer> Integer integer_option(std::string_view value) {
    Integer number{};
    const auto [end,error] = std::from_chars(value.data(),value.data()+value.size(),number);
    if (value.empty() || error!=std::errc{} || end!=value.data()+value.size())
        throw std::invalid_argument("option requires a complete decimal integer");
    return number;
}
}
CommandOptions parse_report_options(std::span<const std::string_view> arguments) {
    constexpr std::array<std::string_view,8> names{
        "--input","--output","--window","--hop","--gain-uv","--offset-uv","--interval-ms","--label"};
    std::array<bool,8> seen{};
    std::filesystem::path input;
    std::optional<std::filesystem::path> output;
    std::size_t width=2,hop=1;
    int gain=1000,offset=0;
    std::int64_t interval=1000;
    std::string_view label="measurement";
    for (std::size_t i=0;i<arguments.size();i+=2) {
        const auto found = std::find(names.begin(),names.end(),arguments[i]);
        if (found==names.end()) throw std::invalid_argument("unknown report option");
        const auto index = static_cast<std::size_t>(found-names.begin());
        if (seen[index]) throw std::invalid_argument("duplicate report option");
        if (i+1==arguments.size()) throw std::invalid_argument("report option is missing its value");
        seen[index]=true;
        const auto value=arguments[i+1];
        if (value.empty()) throw std::invalid_argument("report option has an empty value");
        switch (index) {
        case 0: input=std::filesystem::path(value); break;
        case 1: output=std::filesystem::path(value); break;
        case 2: width=integer_option<std::size_t>(value); break;
        case 3: hop=integer_option<std::size_t>(value); break;
        case 4: gain=integer_option<int>(value); break;
        case 5: offset=integer_option<int>(value); break;
        case 6: interval=integer_option<std::int64_t>(value); break;
        case 7: label=value; break;
        }
    }
    if (!seen[0]) throw std::invalid_argument("--input is required");
    return {std::move(input),std::move(output),
            ReportSettings{Calibration{gain,offset},std::chrono::milliseconds{interval},WindowSpec{width,hop},label}};
}
void emit_report(std::ostream& output, std::string_view text) {
    if (text.size()>static_cast<std::size_t>(std::numeric_limits<std::streamsize>::max()))
        throw std::length_error("report is too long for the stream");
    output.write(text.data(),static_cast<std::streamsize>(text.size()));
    output.flush();
    if (!output) throw std::runtime_error("report write or flush failed");
}
void write_report_file(const std::filesystem::path& path, std::string_view text) {
    std::ofstream file(path,std::ios::binary);
    if (!file) throw std::runtime_error("cannot open report output");
    emit_report(file,text);
    file.close();
    if (!file) throw std::runtime_error("report close failed");
}
}
