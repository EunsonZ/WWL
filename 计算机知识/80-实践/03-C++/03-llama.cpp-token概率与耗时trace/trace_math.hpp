#pragma once

#include <algorithm>
#include <cmath>
#include <cstddef>
#include <limits>
#include <numeric>
#include <stdexcept>
#include <vector>

struct TopToken {
    int id;
    float probability;
};

inline std::vector<TopToken> top_probabilities(const float * logits, std::size_t vocab_size,
                                                std::size_t top_k) {
    if (logits == nullptr || vocab_size == 0 || top_k == 0) {
        throw std::invalid_argument("logits, vocabulary size, and top_k must be non-empty");
    }

    bool has_finite_logit = false;
    for (std::size_t i = 0; i < vocab_size; ++i) {
        if (std::isnan(logits[i]) || logits[i] == std::numeric_limits<float>::infinity()) {
            throw std::domain_error("logits must not contain NaN or positive infinity");
        }
        has_finite_logit = has_finite_logit || std::isfinite(logits[i]);
    }
    if (!has_finite_logit) {
        throw std::domain_error("at least one logit must be finite");
    }

    const float maximum = *std::max_element(logits, logits + vocab_size);
    std::vector<float> weights(vocab_size);
    for (std::size_t i = 0; i < vocab_size; ++i) {
        weights[i] = std::exp(logits[i] - maximum);
    }
    const float normalizer = std::accumulate(weights.begin(), weights.end(), 0.0F);
    if (!std::isfinite(normalizer) || normalizer <= 0.0F) {
        throw std::domain_error("softmax normalizer must be finite and positive");
    }
    std::vector<int> ids(vocab_size);
    std::iota(ids.begin(), ids.end(), 0);
    const std::size_t count = std::min(top_k, vocab_size);
    std::partial_sort(ids.begin(), ids.begin() + static_cast<std::ptrdiff_t>(count), ids.end(),
                      [&weights](int left, int right) { return weights[left] > weights[right]; });

    std::vector<TopToken> result;
    result.reserve(count);
    for (std::size_t rank = 0; rank < count; ++rank) {
        const int id = ids[rank];
        result.push_back({id, weights[static_cast<std::size_t>(id)] / normalizer});
    }
    return result;
}
