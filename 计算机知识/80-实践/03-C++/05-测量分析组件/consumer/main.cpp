#include <wwl/measurement.hpp>
#include <iostream>
#include <sstream>
int main() {
    std::istringstream input("2 4 6 8");
    auto batch = wwl::read_batch(input);
    auto stats = wwl::describe(batch);
    if (!stats || stats->sum.value != 20 || stats->mean.value != 5) return 1;
    std::cout << "consumer: sum=20 mV, mean=5 mV\n";
}
