#pragma once
#include <concepts>
#include <cstddef>
#include <cstdint>
#include <functional>
#include <istream>
#include <optional>
#include <ranges>
#include <span>
#include <stdexcept>
#include <type_traits>
#include <vector>

namespace wwl {
inline constexpr std::size_t max_samples = 65536;
class RawCode {
public:
    explicit RawCode(int value);
    int value() const noexcept { return value_; }
private:
    int value_;
};
struct Seconds { double value; };
struct Millivolts { double value; };
struct MillivoltsSquared { double value; };
class Calibration {
public:
    // Integer microvolts keep the acquisition/calibration reference exact.
    explicit Calibration(int gain_microvolts_per_code = 1000, int offset_microvolts = 0);
    std::int64_t microvolts(RawCode code) const noexcept;
    int gain() const noexcept { return gain_; }
    int offset() const noexcept { return offset_; }
private:
    int gain_;
    int offset_;
};
class Batch {
public:
    explicit Batch(std::vector<RawCode> codes, Calibration calibration = Calibration{},
                   Seconds interval = Seconds{1.0});
    std::span<const RawCode> codes() const & noexcept { return codes_; }
    std::span<const RawCode> codes() const && = delete;
    // Small owning value, safe even when the Batch is a temporary.
    Calibration calibration() const noexcept { return calibration_; }
    Seconds interval() const noexcept { return interval_; }
    void swap(Batch& other) noexcept;
private:
    std::vector<RawCode> codes_;
    Calibration calibration_;
    Seconds interval_;
};
// One pass over any input range whose projection returns precisely RawCode.
// A concept checks syntax/types; RawCode checks the numerical domain at runtime.
template<std::ranges::input_range Range, class Projection = std::identity>
requires std::same_as<std::remove_cvref_t<std::invoke_result_t<Projection&,
                         std::ranges::range_reference_t<Range>>>, RawCode>
std::uint64_t sum_codes(Range&& range, Projection projection = {}) {
    std::uint64_t total = 0;
    std::size_t count = 0;
    for (auto&& item : range) {
        if (++count > max_samples) throw std::length_error("too many samples");
        total += static_cast<std::uint64_t>(std::invoke(projection, item).value());
    }
    return total;
}
struct Statistics {
    std::size_t count;
    Millivolts sum;
    Millivolts mean;
    MillivoltsSquared population_variance;
    MillivoltsSquared rms_squared;
    std::optional<MillivoltsSquared> sample_variance;
};
Batch read_batch(std::istream& input, Calibration calibration = Calibration{},
                 Seconds interval = Seconds{1.0});
void replace_from_stream(Batch& current, std::istream& input);
// Validated RawCodes; empty input => nullopt; more than max_samples => length_error.
std::optional<Statistics> describe_codes(std::span<const RawCode> codes, Calibration calibration);
std::optional<Statistics> describe(const Batch& batch);
std::vector<float> calibrated_values(const Batch& batch);
struct Reduction {
    Millivolts serial;
    Millivolts parallel;
    Millivolts reference;
    Millivolts absolute_error_bound;
};
Reduction compare_reductions(const Batch& batch, std::size_t workers);
// Returns an owning one-dimensional vector: result[channel] is that channel's mean.
// The internal TensorBuffer input is [channel][sample], row-major,
// with strides [sample_count,1]; the returned vector has no sample axis.
// Empty batches are rejected here, before constructing TensorBuffer.
std::vector<Millivolts> channel_means(std::span<const Batch> channels);
}
