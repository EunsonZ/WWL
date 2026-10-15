#include "layout_math.hpp"

#include <algorithm>
#include <chrono>
#include <cstddef>
#include <cstdint>
#include <iostream>
#include <thread>
#include <utility>
#include <vector>

template <class Function>
std::pair<long long, double> measure_us(Function function, int repetitions) {
    const auto start = std::chrono::steady_clock::now();
    double checksum = 0.0;
    for (int repetition = 0; repetition < repetitions; ++repetition) {
        checksum += function();
    }
    const auto elapsed = std::chrono::steady_clock::now() - start;
    return {std::chrono::duration_cast<std::chrono::microseconds>(elapsed).count(), checksum};
}

int main() {
    constexpr std::size_t element_count = 2'000'000;
    constexpr int repetitions = 8;
    std::vector<Sample> aos;
    std::vector<float> soa;
    aos.reserve(element_count);
    soa.reserve(element_count);
    for (std::size_t index = 0; index < element_count; ++index) {
        const float value = static_cast<float>(index % 17);
        aos.push_back({value, static_cast<std::uint32_t>(index)});
        soa.push_back(value);
    }

    const std::size_t workers = std::max(1U, std::thread::hardware_concurrency());
    const auto [aos_us, aos_checksum] = measure_us([&aos] { return sum_aos(aos); }, repetitions);
    const auto [soa_us, soa_checksum] = measure_us([&soa] { return sum_soa(soa); }, repetitions);
    const auto [parallel_us, parallel_checksum] =
        measure_us([&soa, workers] { return parallel_sum_soa(soa, workers); }, repetitions);

    std::cout << "elements=" << element_count << ", repetitions=" << repetitions
              << ", workers=" << workers << '\n'
              << "aos_us=" << aos_us << ", checksum=" << aos_checksum << '\n'
              << "soa_us=" << soa_us << ", checksum=" << soa_checksum << '\n'
              << "parallel_soa_us=" << parallel_us << ", checksum=" << parallel_checksum << '\n';
}
