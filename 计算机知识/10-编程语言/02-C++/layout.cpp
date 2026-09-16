#include <cstddef>
#include <iostream>
#include <span>
#include <vector>

struct TokenStat {
    float logit;
    int token_id;
    bool selected;
};

float sum_contiguous(std::span<const float> values) {
    float result = 0.0F;
    for (const float value : values) {
        result += value;
    }
    return result;
}

int main() {
    const std::vector<float> logits{1.0F, 2.0F, 3.0F, 4.0F};
    const float sum = sum_contiguous(logits);
    if (sum != 10.0F) {
        std::cerr << "sum contract failed\n";
        return 1;
    }
    std::cout << "TokenStat size=" << sizeof(TokenStat)
              << ", alignment=" << alignof(TokenStat)
              << ", sum=" << sum << '\n';
}
