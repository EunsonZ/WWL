#pragma once
#include <wwl/measurement.hpp>
#include <array>
#include <chrono>
#include <filesystem>
#include <memory>
#include <memory_resource>
#include <optional>
#include <ostream>
#include <string>
#include <string_view>

namespace wwl {
class WindowSpec {
public:
    explicit WindowSpec(std::size_t width = 2, std::size_t hop = 1);
    std::size_t width() const noexcept { return width_; }
    std::size_t hop() const noexcept { return hop_; }
private:
    std::size_t width_, hop_;
};
class ReportSettings {
public:
    explicit ReportSettings(Calibration calibration = Calibration{},
                            std::chrono::milliseconds interval = std::chrono::milliseconds{1000},
                            WindowSpec window = WindowSpec{}, std::string_view label = "measurement");
    Calibration calibration() const noexcept { return calibration_; }
    std::chrono::milliseconds interval() const noexcept { return interval_; }
    WindowSpec window() const noexcept { return window_; }
    // Owning text value: obtaining the label from temporary settings is safe.
    std::string label() const;
private:
    Calibration calibration_;
    std::chrono::milliseconds interval_;
    WindowSpec window_;
    std::array<char,40> label_{};
    std::size_t label_size_;
};
struct WindowStatistics {
    std::size_t begin;       // Inclusive index in the original batch.
    std::size_t end;         // Exclusive index. Only full windows are emitted.
    std::chrono::milliseconds first_sample_time;
    std::chrono::milliseconds last_sample_time; // Time of sample end-1, not end.
    Statistics statistics;
};
// Sequential, single-owner session. resource must outlive this object.
// Replacement failure preserves settings, windows, text and outstanding resource use.
// Successful replacement invalidates borrowed windows/text; reacquire them afterward.
class ReportSession {
public:
    explicit ReportSession(std::pmr::memory_resource* resource = std::pmr::get_default_resource());
    ~ReportSession();
    ReportSession(const ReportSession&) = delete;
    ReportSession& operator=(const ReportSession&) = delete;
    ReportSession(ReportSession&&) = delete;
    ReportSession& operator=(ReportSession&&) = delete;
    void replace(std::istream& input, ReportSettings settings = ReportSettings{});
    std::span<const WindowStatistics> windows() const & noexcept;
    std::span<const WindowStatistics> windows() const && = delete;
    std::string_view text() const & noexcept;
    std::string_view text() const && = delete;
    std::optional<ReportSettings> settings() const;
private:
    struct Snapshot;
    struct Deleter {
        std::pmr::memory_resource* resource;
        void operator()(Snapshot* pointer) const noexcept;
    };
    std::pmr::memory_resource* resource_;
    std::unique_ptr<Snapshot,Deleter> current_;
};
struct CommandOptions {
    std::filesystem::path input;
    std::optional<std::filesystem::path> output; // Missing => stdout.
    ReportSettings settings;
};
// Arguments exclude argv[0]. Values are explicit and duplicate options are rejected.
CommandOptions parse_report_options(std::span<const std::string_view> arguments);
void emit_report(std::ostream& output, std::string_view text);
// Checks open, write/flush and close. Does not promise atomic or durable file output.
void write_report_file(const std::filesystem::path& path, std::string_view text);
}
