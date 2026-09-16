#include "word_counter.hpp"

#include <cctype>

std::map<std::string, std::size_t> count_words(std::string_view text) {
    std::map<std::string, std::size_t> counts;
    std::string word;

    for (unsigned char ch : text) {
        if (std::isalnum(ch) != 0) {
            word += static_cast<char>(std::tolower(ch));
            continue;
        }
        if (!word.empty()) {
            ++counts[word];
            word.clear();
        }
    }
    if (!word.empty()) {
        ++counts[word];
    }
    return counts;
}
