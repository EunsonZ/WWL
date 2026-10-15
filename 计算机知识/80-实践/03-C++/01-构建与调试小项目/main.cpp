#include "word_counter.hpp"

#include <iostream>
#include <string>

int main(int argc, char * argv[]) {
    const std::string text = argc > 1 ? argv[1] : "RAII makes ownership visible";
    const auto counts = count_words(text);

    for (const auto & [word, count] : counts) {
        std::cout << word << ": " << count << '\n';
    }

    if (argc > 2 && std::string(argv[2]) == "--debug-fail") {
        return counts.at("this-token-is-not-present");
    }
}
