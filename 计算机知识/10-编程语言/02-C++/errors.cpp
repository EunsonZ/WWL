#include <charconv>
#include <iostream>
#include <optional>
#include <string_view>

std::optional<int> parse_nonnegative(std::string_view text) {
    int value = 0;
    const char* const begin = text.data();
    const char* const end = begin + text.size();
    const auto [next, error] = std::from_chars(begin, end, value);
    if (error != std::errc{} || next != end || value < 0) {
        return std::nullopt;
    }
    return value;
}

int main() {
    const auto valid = parse_nonnegative("42");
    if (!valid || *valid != 42 || parse_nonnegative("-1") || parse_nonnegative("42x")) {
        std::cerr << "parse contract failed\n";
        return 1;
    }
    std::cout << *valid << '\n';
}
