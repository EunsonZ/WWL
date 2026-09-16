#pragma once

#include <algorithm>
#include <cstddef>
#include <cstdint>
#include <numeric>
#include <span>
#include <stdexcept>
#include <thread>
#include <vector>

struct Sample {
    float value;
    std::uint32_t id;
};

inline double sum_aos(std::span<const Sample> samples) {
    double result = 0.0;
    for (const Sample& sample : samples) {
        result += sample.value;
    }
    return result;
}

inline double sum_soa(std::span<const float> values) {
    double result = 0.0;
    for (const float value : values) {
        result += value;
    }
    return result;
}

inline double parallel_sum_soa(std::span<const float> values, std::size_t worker_count) {
    if (worker_count == 0) {
        throw std::invalid_argument("worker_count must be positive");
    }
    if (values.empty()) {
        return 0.0;
    }

    worker_count = std::min(worker_count, values.size());
    std::vector<double> partials(worker_count, 0.0);
    std::vector<std::jthread> workers;
    workers.reserve(worker_count);

    const std::size_t base = values.size() / worker_count;
    const std::size_t remainder = values.size() % worker_count;

    for (std::size_t worker = 0; worker < worker_count; ++worker) {
        const std::size_t begin = worker * base + std::min(worker, remainder);
        const std::size_t end = begin + base + (worker < remainder ? 1U : 0U);
        workers.emplace_back([values, &partials, worker, begin, end] {
            partials[worker] = sum_soa(values.subspan(begin, end - begin));
        });
    }
    for (std::jthread& worker : workers) {
        worker.join();
    }
    return std::accumulate(partials.begin(), partials.end(), 0.0);
}
