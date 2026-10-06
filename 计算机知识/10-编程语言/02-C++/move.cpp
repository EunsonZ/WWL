#include <iostream>
#include <string>
#include <utility>

class Packet {
public:
    explicit Packet(std::string bytes) : bytes_(std::move(bytes)) {}
    std::size_t size() const { return bytes_.size(); }

private:
    std::string bytes_;
};

int main() {
    std::string payload(1'000, 'x');
    Packet packet(std::move(payload));
    std::cout << packet.size() << "\n";
}
