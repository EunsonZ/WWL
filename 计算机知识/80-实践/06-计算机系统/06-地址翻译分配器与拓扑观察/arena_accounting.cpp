#include <algorithm>
#include <cstddef>
#include <cstdlib>
#include <iostream>
#include <limits>
#include <optional>
#include <string_view>
#include <vector>

struct Allocation {
    std::size_t offset;
    std::size_t requested;
    std::size_t padding;
};

class FixedArena {
public:
    explicit FixedArena(std::size_t capacity) : storage_(capacity) {}

    // This teaching arena aligns only offsets within storage_. std::vector<std::byte>
    // does not promise that storage_.data() itself has every requested alignment.
    // Therefore an Allocation is accounting metadata, not an over-aligned pointer.
    std::optional<Allocation> allocate(std::size_t requested, std::size_t offset_alignment) {
        if (requested == 0 || offset_alignment == 0 ||
            (offset_alignment & (offset_alignment - 1)) != 0) {
            return std::nullopt;
        }
        const std::size_t mask = offset_alignment - 1;
        if (cursor_ > std::numeric_limits<std::size_t>::max() - mask) {
            return std::nullopt;
        }
        const std::size_t aligned = (cursor_ + mask) & ~mask;
        if (aligned > storage_.size() || requested > storage_.size() - aligned) {
            return std::nullopt;
        }

        const Allocation result{aligned, requested, aligned - cursor_};
        cursor_ = aligned + requested;
        live_requested_ += requested;
        allocations_.push_back(result);
        return result;
    }

    void touch(const Allocation& allocation, std::size_t stride) {
        if (stride == 0 || allocation.offset > storage_.size() ||
            allocation.requested > storage_.size() - allocation.offset) {
            return;
        }
        for (std::size_t index = 0; index < allocation.requested; index += stride) {
            storage_[allocation.offset + index] = std::byte{0x2a};
        }
        if (allocation.requested > 0) {
            storage_[allocation.offset + allocation.requested - 1] = std::byte{0x2a};
        }
    }

    void reset_logical_allocations() {
        cursor_ = 0;
        live_requested_ = 0;
        allocations_.clear();
    }

    std::size_t capacity() const { return storage_.size(); }
    std::size_t used() const { return cursor_; }
    std::size_t live_requested() const { return live_requested_; }
    std::size_t allocation_count() const { return allocations_.size(); }

private:
    std::vector<std::byte> storage_;
    std::size_t cursor_ = 0;
    std::size_t live_requested_ = 0;
    std::vector<Allocation> allocations_;
};

bool self_test() {
    FixedArena arena(256);
    const auto first = arena.allocate(31, 16);
    const auto second = arena.allocate(32, 64);
    const auto invalid_alignment = arena.allocate(1, 3);
    const auto too_large = arena.allocate(1024, 8);
    if (!first || !second || invalid_alignment || too_large) {
        return false;
    }
    if (first->offset % 16 != 0 || second->offset % 64 != 0) {
        return false;
    }
    if (first->offset + first->requested > second->offset) {
        return false;
    }
    if (arena.live_requested() != 63 || arena.allocation_count() != 2 ||
        arena.used() < arena.live_requested()) {
        return false;
    }
    arena.reset_logical_allocations();
    return arena.capacity() == 256 && arena.used() == 0 && arena.live_requested() == 0 &&
           arena.allocation_count() == 0;
}

int main(int argc, char* argv[]) {
    if (argc == 2 && std::string_view(argv[1]) == "--self-test") {
        const bool passed = self_test();
        std::cout << (passed ? "self-test passed\n" : "self-test failed\n");
        return passed ? EXIT_SUCCESS : EXIT_FAILURE;
    }

    constexpr std::size_t kib = 1024;
    constexpr std::size_t mib = 1024 * kib;
    constexpr std::size_t arena_bytes = 4 * mib;
    constexpr std::size_t illustrative_page_stride = 4096;

    FixedArena arena(arena_bytes);
    const auto weights = arena.allocate(1 * mib + 13, 64);
    const auto scratch = arena.allocate(768 * kib + 7, 4096);
    const auto request = arena.allocate(640 * kib + 3, 256);
    if (!weights || !scratch || !request) {
        std::cerr << "fixed arena configuration unexpectedly failed\n";
        return EXIT_FAILURE;
    }

    arena.touch(*weights, illustrative_page_stride);
    arena.touch(*scratch, illustrative_page_stride);
    arena.touch(*request, illustrative_page_stride);

    std::cout << "arena_capacity_bytes=" << arena.capacity() << '\n'
              << "allocator_used_bytes=" << arena.used() << '\n'
              << "live_requested_bytes=" << arena.live_requested() << '\n'
              << "logical_offset_padding_bytes=" << arena.used() - arena.live_requested() << '\n'
              << "unused_tail_bytes=" << arena.capacity() - arena.used() << '\n'
              << "allocation_count=" << arena.allocation_count() << '\n';

    arena.reset_logical_allocations();
    std::cout << "after_reset_live_requested_bytes=" << arena.live_requested() << '\n'
              << "after_reset_allocator_used_bytes=" << arena.used() << '\n'
              << "backing_buffer_still_owned_bytes=" << arena.capacity() << '\n'
              << "note=offset alignment is logical bookkeeping; this arena returns no over-aligned pointers"
              << '\n';
}
