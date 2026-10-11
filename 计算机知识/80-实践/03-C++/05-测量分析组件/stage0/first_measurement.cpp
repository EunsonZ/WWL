#include <charconv>
#include <iostream>
#include <string>
#include <vector>
// First complete program: no class, view, concept or hand-managed allocation.
bool parse_code(const std::string& token, int& code) {
    const auto [end,error] = std::from_chars(token.data(),token.data()+token.size(),code);
    return error == std::errc{} && end == token.data()+token.size() && code >= 0 && code <= 4095;
}
int main() {
    std::vector<int> codes;
    std::string token;
    while (std::cin >> token) {
        int code = 0;
        if (!parse_code(token,code) || codes.size() == 65536) {
            std::cerr << "invalid ADC code or too many samples\n"; return 2;
        }
        codes.push_back(code);
    }
    if (std::cin.bad() || (!std::cin.eof() && std::cin.fail())) {
        std::cerr << "input read failed\n"; return 2;
    }
    long long sum = 0;
    for (int code : codes) sum += code;
    std::cout << "count=" << codes.size() << " sum_mV=" << sum;
    if (!codes.empty()) std::cout << " mean_mV=" << static_cast<double>(sum)/codes.size();
    std::cout << '\n';
}
