#include <wwl/measurement_abi.h>
#include <wwl/report.hpp>
#include <cstring>
#include <memory_resource>
#include <new>
#include <sstream>
#include <stdexcept>
#include <string>
#include <type_traits>

#ifdef WWL_ABI_TESTING
namespace wwl_abi_test {
int next_exception = 0;
std::size_t handles = 0, blocks = 0, bytes = 0;
void throw_next(int kind) { next_exception = kind; }
std::size_t live_handles() { return handles; }
std::size_t live_blocks() { return blocks; }
std::size_t live_bytes() { return bytes; }
class Resource final : public std::pmr::memory_resource {
public:
    std::size_t allocation_calls = 0, fail_at = 0;
private:
    void* do_allocate(std::size_t n, std::size_t alignment) override {
        if (++allocation_calls == fail_at) throw std::bad_alloc{};
        auto* p = std::pmr::new_delete_resource()->allocate(n, alignment);
        ++blocks; bytes += n; return p;
    }
    void do_deallocate(void* p, std::size_t n, std::size_t alignment) override {
        std::pmr::new_delete_resource()->deallocate(p, n, alignment);
        --blocks; bytes -= n;
    }
    bool do_is_equal(const std::pmr::memory_resource& other) const noexcept override {
        return this == &other;
    }
};
}
#endif
struct wwl_report_handle {
#ifdef WWL_ABI_TESTING
    wwl_abi_test::Resource resource; // Declared first: outlives session destruction.
    wwl::ReportSession session{&resource};
    wwl_report_handle() { ++wwl_abi_test::handles; }
    ~wwl_report_handle() { --wwl_abi_test::handles; }
#else
    wwl::ReportSession session{std::pmr::new_delete_resource()};
#endif
    bool ready = false;
};
#ifdef WWL_ABI_TESTING
namespace wwl_abi_test {
void fail_pmr_at(wwl_report_handle* h, std::size_t n) {
    h->resource.allocation_calls = 0; h->resource.fail_at = n;
}
std::size_t pmr_calls(wwl_report_handle* h) { return h->resource.allocation_calls; }
}
#endif
static_assert(std::is_standard_layout_v<wwl_report_settings_v1>);
static_assert(std::is_trivially_copyable_v<wwl_report_settings_v1>);
namespace {
template<class F> wwl_status boundary(F&& body) noexcept {
    try {
#ifdef WWL_ABI_TESTING
        const int failure = wwl_abi_test::next_exception;
        wwl_abi_test::next_exception = 0;
        switch (failure) {
        case 1: throw std::bad_alloc{};
        case 2: throw std::invalid_argument("injected");
        case 3: throw std::length_error("injected");
        case 4: throw std::runtime_error("injected");
        case 5: throw 42;
        default: break;
        }
#endif
        return body();
    } catch (const std::bad_alloc&) { return WWL_OUT_OF_MEMORY;
    } catch (const std::invalid_argument&) { return WWL_INVALID_ARGUMENT;
    } catch (const std::length_error&) { return WWL_LIMIT_EXCEEDED;
    } catch (...) { return WWL_INTERNAL_ERROR; }
}
}
extern "C" WWL_ABI_API wwl_status wwl_report_create_v1(uint32_t version, wwl_report_handle** out) {
    return boundary([&]() -> wwl_status {
        if (version != WWL_ABI_VERSION_V1) return WWL_VERSION_MISMATCH;
        if (!out || *out) return WWL_INVALID_ARGUMENT;
        *out = new wwl_report_handle; return WWL_OK;
    });
}
extern "C" WWL_ABI_API wwl_status wwl_report_destroy_v1(wwl_report_handle** handle) {
    return boundary([&]() -> wwl_status {
        if (!handle) return WWL_INVALID_ARGUMENT;
        delete *handle; *handle = nullptr; return WWL_OK;
    });
}
extern "C" WWL_ABI_API wwl_status wwl_report_replace_v1(
    wwl_report_handle* handle, uint32_t version, size_t settings_size,
    const wwl_report_settings_v1* settings, const char* codes, size_t codes_bytes) {
    return boundary([&]() -> wwl_status {
        if (version != WWL_ABI_VERSION_V1) return WWL_VERSION_MISMATCH;
        if (settings_size != sizeof(wwl_report_settings_v1)) return WWL_SIZE_MISMATCH;
        if (!handle || !settings || (!codes && codes_bytes)) return WWL_INVALID_ARGUMENT;
        if (codes_bytes > WWL_ABI_MAX_INPUT_BYTES_V1) return WWL_LIMIT_EXCEEDED;
        // No structure field is read until the envelope has been checked.
        const auto& s = *settings;
        if (s.label_bytes < 1 || s.label_bytes > sizeof(s.label) ||
            s.width < 1 || s.width > 4096 || s.hop < 1 || s.hop > 4096)
            return WWL_INVALID_ARGUMENT;
        const wwl::ReportSettings config{
            wwl::Calibration{s.gain_uV_per_code, s.offset_uV},
            std::chrono::milliseconds{s.interval_ms}, wwl::WindowSpec{s.width, s.hop},
            std::string_view{s.label, s.label_bytes}};
        // Own the input while parsing; constructing it can fail before commit.
        std::istringstream input{codes_bytes ? std::string(codes, codes_bytes) : std::string{}};
        handle->session.replace(input, config);
        handle->ready = true; // Non-throwing; there is no fallible work after commit.
        return WWL_OK;
    });
}
extern "C" WWL_ABI_API wwl_status wwl_report_copy_text_v1(
    const wwl_report_handle* handle, char* output, size_t capacity, size_t* required) {
    return boundary([&]() -> wwl_status {
        if (!handle || !required || (!output && capacity)) return WWL_INVALID_ARGUMENT;
        if (!handle->ready) { *required = 0; return WWL_NOT_READY; }
        const auto text = handle->session.text();
        *required = text.size() + 1;
        if (capacity < *required) return WWL_BUFFER_TOO_SMALL;
        std::memcpy(output, text.data(), text.size());
        output[text.size()] = '\0';
        return WWL_OK;
    });
}
extern "C" WWL_ABI_API wwl_status wwl_report_get_layout_v1(
    uint32_t version, size_t layout_size, wwl_report_layout_v1* output) {
    return boundary([&]() -> wwl_status {
        if (version != WWL_ABI_VERSION_V1) return WWL_VERSION_MISMATCH;
        if (layout_size != sizeof(wwl_report_layout_v1)) return WWL_SIZE_MISMATCH;
        if (!output) return WWL_INVALID_ARGUMENT;
        *output = {sizeof(wwl_report_settings_v1), alignof(wwl_report_settings_v1),
            offsetof(wwl_report_settings_v1, gain_uV_per_code),
            offsetof(wwl_report_settings_v1, offset_uV),
            offsetof(wwl_report_settings_v1, interval_ms),
            offsetof(wwl_report_settings_v1, width), offsetof(wwl_report_settings_v1, hop),
            offsetof(wwl_report_settings_v1, label_bytes), offsetof(wwl_report_settings_v1, label)};
        return WWL_OK;
    });
}
