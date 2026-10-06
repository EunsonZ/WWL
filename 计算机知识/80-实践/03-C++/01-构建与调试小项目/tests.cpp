#include "word_counter.hpp"

#include <iostream>

int main() {
    const auto counts = count_words("Hello, hello! C++20; C++20.");
    if (counts.at("hello") != 2 || counts.at("c") != 2 || counts.at("20") != 2 ||
        counts.size() != 3) {
        std::cerr << "word counter result did not match the expected table\n";
        return 1;
    }
}
