#include "layout_math.hpp"

#include <iostream>
#include <stdexcept>
#include <string_view>
#include <vector>

int main() {
    const std::vector<Sample> aos{{1.0F, 10}, {2.0F, 11}, {3.0F, 12}, {4.0F, 13}};
    const std::vector<float> soa{1.0F, 2.0F, 3.0F, 4.0F};

    int failures = 0;
    const auto check = [&failures](bool condition, std::string_view name) {
        if (!condition) {
            std::cerr << "FAILED: " << name << '\n';
            ++failures;
        }
    };

    check(sum_aos(aos) == 10.0, "AoS sum");
    check(sum_soa(soa) == 10.0, "SoA sum");
    check(parallel_sum_soa(soa, 1) == 10.0, "one-worker reduction");
    check(parallel_sum_soa(soa, 3) == 10.0, "three-worker reduction");
    check(parallel_sum_soa({}, 2) == 0.0, "empty input");

    bool rejected_zero_workers = false;
    try {
        static_cast<void>(parallel_sum_soa(soa, 0));
    } catch (const std::invalid_argument&) {
        rejected_zero_workers = true;
    }
    check(rejected_zero_workers, "zero workers rejected");
    if (failures == 0) {
        std::cout << "layout and reduction tests passed\n";
    }
    return failures == 0 ? 0 : 1;
}
