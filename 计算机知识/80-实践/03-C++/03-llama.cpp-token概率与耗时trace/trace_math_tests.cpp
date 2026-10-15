#include "trace_math.hpp"

#include <cmath>
#include <iostream>
#include <limits>
#include <stdexcept>

namespace {
bool rejects_non_finite(const float * logits, std::size_t count) {
    try {
        static_cast<void>(top_probabilities(logits, count, 1));
    } catch (const std::domain_error &) {
        return true;
    }
    return false;
}
}  // namespace

int main() {
    const float logits[] = {0.0F, 2.0F, 1.0F};
    const auto top = top_probabilities(logits, 3, 2);
    if (top.size() != 2 || top[0].id != 1 || top[0].probability <= top[1].probability ||
        std::abs(top[0].probability + top[1].probability - 0.9099694F) >= 0.0001F) {
        std::cerr << "finite softmax/top-k check failed\n";
        return 1;
    }

    const float with_negative_infinity[] = {
        0.0F, -std::numeric_limits<float>::infinity(), 1.0F};
    const auto finite_top = top_probabilities(with_negative_infinity, 3, 2);
    if (finite_top.size() != 2 || !std::isfinite(finite_top[0].probability) ||
        !std::isfinite(finite_top[1].probability)) {
        std::cerr << "negative-infinity masking check failed\n";
        return 1;
    }

    const float with_nan[] = {0.0F, std::numeric_limits<float>::quiet_NaN()};
    const float with_positive_infinity[] = {
        0.0F, std::numeric_limits<float>::infinity()};
    const float all_negative_infinity[] = {
        -std::numeric_limits<float>::infinity(), -std::numeric_limits<float>::infinity()};
    if (!rejects_non_finite(with_nan, 2) || !rejects_non_finite(with_positive_infinity, 2) ||
        !rejects_non_finite(all_negative_infinity, 2)) {
        std::cerr << "invalid-logit rejection check failed\n";
        return 1;
    }
}
