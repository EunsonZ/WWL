#include "tensor_buffer.hpp"

#include <iostream>
#include <stdexcept>

int main() {
    TensorBuffer<int> tensor({2, 3, 4});
    if (tensor.size() != 24) {
        std::cerr << "tensor element count was not 24\n";
        return 1;
    }
    tensor.at({1, 2, 3}) = 42;
    if (tensor.at({1, 2, 3}) != 42) {
        std::cerr << "tensor read/write check failed\n";
        return 1;
    }

    bool caught = false;
    try {
        static_cast<void>(tensor.at({2, 0, 0}));
    } catch (const std::out_of_range &) {
        caught = true;
    }
    if (!caught) {
        std::cerr << "out-of-range tensor access did not throw\n";
        return 1;
    }
}
