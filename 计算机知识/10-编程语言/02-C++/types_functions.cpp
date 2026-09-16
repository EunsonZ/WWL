#include <iostream>
#include <string_view>

int twice(int value) {
    return value * 2;
}

void greet(std::string_view name) {
    std::cout << "Hello, " << name << "\n";
}

int main() {
    const int answer = twice(21);
    greet("C++");
    std::cout << answer << "\n";
}
