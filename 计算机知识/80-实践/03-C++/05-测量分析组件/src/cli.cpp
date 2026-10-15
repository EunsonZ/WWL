#include "wwl/measurement.hpp"
#include <fstream>
#include <iomanip>
#include <iostream>
#include <stdexcept>
int main(int argc, char** argv) {
    try {
        if (argc != 2) throw std::invalid_argument("usage: measurement_cli CODES_FILE");
        std::ifstream file(argv[1]);
        if (!file) throw std::runtime_error("cannot open input file");
        const auto batch = wwl::read_batch(file);
        const auto result = wwl::describe(batch);
        if (!result) { std::cout << "count=0; no statistics\n"; return 0; }
        std::cout << std::setprecision(17) << "count=" << result->count
                  << " sum_mV=" << result->sum.value << " mean_mV=" << result->mean.value
                  << " population_variance_mV2=" << result->population_variance.value
                  << " rms_squared_mV2=" << result->rms_squared.value << '\n';
        const auto sums = wwl::compare_reductions(batch, 2);
        std::cout << "serial_mV=" << sums.serial.value << " parallel_mV=" << sums.parallel.value
                  << " reference_mV=" << sums.reference.value
                  << " absolute_error_bound_mV=" << sums.absolute_error_bound.value << '\n';
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "measurement: " << error.what() << '\n';
        return 2;
    }
}
