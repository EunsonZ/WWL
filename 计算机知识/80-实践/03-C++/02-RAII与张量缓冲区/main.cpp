#include "tensor_buffer.hpp"

#include <iostream>

int main() {
    TensorBuffer<float> activation({2, 3});
    activation.at({1, 2}) = 0.75F;

    std::cout << "elements=" << activation.size()
              << ", activation[1,2]=" << activation.at({1, 2}) << '\n';
}
