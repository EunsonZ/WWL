#include <array>
#include <bit>
#include <climits>
#include <cstddef>
#include <cstdint>
#include <iomanip>
#include <iostream>
#include <string_view>

static_assert(CHAR_BIT == 8, "This teaching example requires 8-bit bytes.");
static_assert(sizeof(std::uint32_t) == 4, "This teaching example requires a four-byte uint32_t.");

struct Record {
    std::uint8_t tag;
    std::uint32_t count;
    std::uint16_t flags;
};

std::array<std::byte, 4> encode_u32_little_endian(std::uint32_t value) {
    return {
        static_cast<std::byte>(value & 0xffU),
        static_cast<std::byte>((value >> 8U) & 0xffU),
        static_cast<std::byte>((value >> 16U) & 0xffU),
        static_cast<std::byte>((value >> 24U) & 0xffU),
    };
}

std::uint32_t decode_u32_little_endian(const std::array<std::byte, 4>& bytes) {
    return std::to_integer<std::uint32_t>(bytes[0]) |
           (std::to_integer<std::uint32_t>(bytes[1]) << 8U) |
           (std::to_integer<std::uint32_t>(bytes[2]) << 16U) |
           (std::to_integer<std::uint32_t>(bytes[3]) << 24U);
}

bool self_test() {
    const std::array<std::uint32_t, 5> cases{0U, 1U, 0x12345678U, 0xffffffffU, 0xa5a55a5aU};
    for (const auto value : cases) {
        if (decode_u32_little_endian(encode_u32_little_endian(value)) != value) {
            return false;
        }
    }
    return offsetof(Record, tag) == 0 && offsetof(Record, count) % alignof(std::uint32_t) == 0 &&
           offsetof(Record, flags) % alignof(std::uint16_t) == 0 && sizeof(Record) >= 7;
}

int main(int argc, char* argv[]) {
    if (argc == 2 && std::string_view(argv[1]) == "--self-test") {
        const bool passed = self_test();
        std::cout << (passed ? "self-test passed\n" : "self-test failed\n");
        return passed ? 0 : 1;
    }

    constexpr std::uint32_t value = 0x12345678U;
    const auto explicit_bytes = encode_u32_little_endian(value);
    const auto native_bytes = std::bit_cast<std::array<std::byte, 4>>(value);

    std::cout << "native_endian=";
    if constexpr (std::endian::native == std::endian::little) {
        std::cout << "little\n";
    } else if constexpr (std::endian::native == std::endian::big) {
        std::cout << "big\n";
    } else {
        std::cout << "mixed\n";
    }

    const auto print_bytes = [](std::string_view label, const auto& bytes) {
        std::cout << label << '=';
        for (const auto byte : bytes) {
            std::cout << ' ' << std::hex << std::setw(2) << std::setfill('0')
                      << std::to_integer<unsigned int>(byte);
        }
        std::cout << std::dec << '\n';
    };

    print_bytes("native_object_bytes", native_bytes);
    print_bytes("explicit_little_endian", explicit_bytes);
    std::cout << "Record sizeof=" << sizeof(Record) << " alignof=" << alignof(Record)
              << " offsets={tag:" << offsetof(Record, tag) << ",count:" << offsetof(Record, count)
              << ",flags:" << offsetof(Record, flags) << "}\n";
    std::cout << "round_trip=0x" << std::hex << decode_u32_little_endian(explicit_bytes) << std::dec
              << '\n';
}
