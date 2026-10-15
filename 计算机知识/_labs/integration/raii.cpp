#include <cassert>
#include <memory>
#include <stdexcept>
#include <type_traits>
#include <vector>

struct Resource {
    std::unique_ptr<int> p;
    explicit Resource(int x): p(std::make_unique<int>(x)) {}
    Resource(Resource&&) noexcept = default;
    Resource& operator=(Resource&&) noexcept = default;
    Resource(const Resource&) = delete;
    Resource& operator=(const Resource&) = delete;
};
struct Bomb {
    int value;
    static inline int copies_before_throw = 100;
    explicit Bomb(int x): value(x) {}
    Bomb(const Bomb& other): value(other.value) {
        if (copies_before_throw-- == 0) throw std::runtime_error("injected copy failure");
    }
    Bomb(Bomb&& other) noexcept(false): value(other.value) { other.value = -1; }
};
int main() {
    static_assert(!std::is_copy_constructible_v<Resource>);
    static_assert(std::is_nothrow_move_constructible_v<Resource>);
    std::vector<Resource> values;
    values.emplace_back(7); values.emplace_back(9);
    values.reserve(32);
    assert(*values[0].p == 7 && *values[1].p == 9);
    auto owner = std::make_shared<int>(5);
    std::weak_ptr<int> observer = owner;
    assert(!observer.expired()); owner.reset(); assert(observer.expired());
    std::vector<Bomb> bombs;
    bombs.reserve(3); bombs.emplace_back(10); bombs.emplace_back(20); bombs.emplace_back(30);
    const auto cap = bombs.capacity();
    Bomb::copies_before_throw = 1;
    bool threw = false;
    try { bombs.reserve(cap + 10); } catch (const std::runtime_error&) { threw = true; }
    assert(threw && bombs.size() == 3 && bombs.capacity() == cap);
    assert(bombs[0].value == 10 && bombs[1].value == 20 && bombs[2].value == 30);
}
