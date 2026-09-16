#include <iostream>

void increment(int& value) {
    ++value;
}

int main() {
    int score = 41;
    int* address = &score;
    const int& read_only = score;

    increment(*address);
    std::cout << read_only << "\n";
}
