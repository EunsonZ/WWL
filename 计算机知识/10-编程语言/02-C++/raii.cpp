#include <iostream>
#include <memory>

class FileLikeResource {
public:
    FileLikeResource() { std::cout << "acquire\n"; }
    ~FileLikeResource() { std::cout << "release\n"; }
    FileLikeResource(const FileLikeResource&) = delete;
    FileLikeResource& operator=(const FileLikeResource&) = delete;
};

int main() {
    auto value = std::make_unique<int>(42);
    FileLikeResource resource;
    std::cout << *value << "\n";
}
