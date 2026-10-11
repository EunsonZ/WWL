#include "wwl/measurement.hpp"
#include "tensor_buffer.hpp"
#include "layout_math.hpp"
#include <algorithm>
#include <charconv>
#include <cmath>
#include <limits>
#include <stdexcept>
#include <string>
#include <utility>

namespace wwl {
RawCode::RawCode(int value) : value_(value) {
    if (value < 0 || value > 4095) throw std::invalid_argument("ADC code must be in [0,4095]");
}
Calibration::Calibration(int gain, int offset) : gain_(gain), offset_(offset) {
    if (gain < 1 || gain > 1000 || offset < -1000000 || offset > 1000000)
        throw std::invalid_argument("gain must be [1,1000] uV/code; offset [-1000000,1000000] uV");
}
std::int64_t Calibration::microvolts(RawCode code) const noexcept {
    return static_cast<std::int64_t>(gain_) * code.value() + offset_;
}
Batch::Batch(std::vector<RawCode> codes, Calibration calibration, Seconds interval)
    : codes_(std::move(codes)), calibration_(calibration), interval_(interval) {
    if (codes_.size() > max_samples) throw std::length_error("too many samples");
    if (!std::isfinite(interval.value) || interval.value <= 0 || interval.value > 86400)
        throw std::invalid_argument("interval must be finite and in (0,86400] seconds");
}
void Batch::swap(Batch& other) noexcept {
    codes_.swap(other.codes_);
    std::swap(calibration_, other.calibration_);
    std::swap(interval_, other.interval_);
}
Batch read_batch(std::istream& input, Calibration calibration, Seconds interval) {
    std::vector<RawCode> codes;
    std::string token;
    while (input >> token) {
        if (codes.size() == max_samples) throw std::length_error("too many samples");
        int code = 0;
        const auto [end, error] = std::from_chars(token.data(), token.data()+token.size(), code);
        if (error != std::errc{} || end != token.data()+token.size())
            throw std::invalid_argument("each token must be a complete decimal ADC code");
        codes.emplace_back(code);
    }
    if (input.bad() || (!input.eof() && input.fail())) throw std::runtime_error("input read failed");
    return Batch{std::move(codes), calibration, interval};
}
void replace_from_stream(Batch& current, std::istream& input) {
    auto next = read_batch(input, current.calibration(), current.interval());
    current.swap(next);
}
std::optional<Statistics> describe_codes(std::span<const RawCode> codes, Calibration calibration) {
    if (codes.size() > max_samples) throw std::length_error("too many samples");
    if (codes.empty()) return std::nullopt;
    // Both integer totals are exact in binary64 under the bounded input contract.
    std::uint64_t sum = sum_codes(codes), squares = 0;
    for (auto code : codes) {
        const auto value = static_cast<std::uint64_t>(code.value());
        squares += value * value;
    }
    std::int64_t sum_uv = 0;
    for (auto code : codes) sum_uv += calibration.microvolts(code);
    const auto n = static_cast<double>(codes.size());
    const auto mean_code = static_cast<double>(sum)/n;
    const auto mean_code_square = static_cast<double>(squares)/n;
    const auto gain_mv = calibration.gain()/1000.0;
    const auto mean_mv = static_cast<double>(sum_uv)/1000.0/n;
    const auto var_code = std::max(0.0, mean_code_square-mean_code*mean_code);
    const auto variance = gain_mv*gain_mv*var_code;
    const auto rms2 = variance+mean_mv*mean_mv;
    std::optional<MillivoltsSquared> sample;
    if (codes.size() > 1) sample = MillivoltsSquared{variance*n/(n-1)};
    return Statistics{codes.size(), {static_cast<double>(sum_uv)/1000.0}, {mean_mv},
                      {variance}, {rms2}, sample};
}
std::optional<Statistics> describe(const Batch& batch) {
    return describe_codes(batch.codes(), batch.calibration());
}
std::vector<float> calibrated_values(const Batch& batch) {
    std::vector<float> values;
    values.reserve(batch.codes().size());
    for (auto code : batch.codes())
        values.push_back(static_cast<float>(batch.calibration().microvolts(code)/1000.0));
    return values;
}
Reduction compare_reductions(const Batch& batch, std::size_t workers) {
    const auto values = calibrated_values(batch);
    std::int64_t sum_uv = 0, abs_uv = 0;
    for (auto code : batch.codes()) {
        const auto uv = batch.calibration().microvolts(code);
        sum_uv += uv;
        abs_uv += std::abs(uv);
    }
    // Covers decimal->binary64->binary32 conversion plus any reduction path with
    // <=n additions along a path and final binary64 reference conversion.
    const double u32 = std::ldexp(1.0, -24), u64 = std::ldexp(1.0, -53);
    const double gamma = values.size()*u64/(1-values.size()*u64);
    const double computed_bound = (u32+2*u64+gamma*(1+u32+2*u64))*
                                  (static_cast<double>(abs_uv)/1000.0);
    const double bound = std::nextafter(computed_bound*(1+32*u64),
                                        std::numeric_limits<double>::infinity());
    return {{sum_soa(values)}, {parallel_sum_soa(values, workers)},
            {static_cast<double>(sum_uv)/1000.0}, {bound}};
}
std::vector<Millivolts> channel_means(std::span<const Batch> channels) {
    if (channels.empty()) throw std::invalid_argument("at least one channel required");
    const auto count = channels.front().codes().size();
    if (count == 0) throw std::invalid_argument("empty channels have no tensor shape");
    for (const auto& channel : channels)
        if (channel.codes().size() != count || channel.interval().value != channels.front().interval().value)
            throw std::invalid_argument("channels must have equal counts and intervals");
    TensorBuffer<double> tensor({channels.size(), count});
    for (std::size_t row = 0; row < channels.size(); ++row)
        for (std::size_t col = 0; col < count; ++col)
            tensor.at({row,col}) = channels[row].calibration().microvolts(channels[row].codes()[col])/1000.0;
    std::vector<Millivolts> means;
    for (std::size_t row = 0; row < channels.size(); ++row) {
        double total = 0;
        for (std::size_t col = 0; col < count; ++col) total += tensor.at({row,col});
        means.push_back({total/static_cast<double>(count)});
    }
    return means;
}
}
