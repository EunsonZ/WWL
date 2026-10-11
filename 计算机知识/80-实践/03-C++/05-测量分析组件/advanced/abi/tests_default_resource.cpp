#include <wwl/measurement_abi.h>
#include <iostream>
#include <memory>
#include <memory_resource>
#include <string>
#include <vector>
namespace {
int failures = 0;
#define CHECK(x) do { if (!(x)) { std::cerr << "FAIL " << __LINE__ << ": " << #x << '\n'; ++failures; } } while (0)
class DefaultResourceScope {
public:
    explicit DefaultResourceScope(std::pmr::memory_resource* resource)
        : old_(std::pmr::set_default_resource(resource)) {}
    ~DefaultResourceScope() { std::pmr::set_default_resource(old_); }
    DefaultResourceScope(const DefaultResourceScope&) = delete;
    DefaultResourceScope& operator=(const DefaultResourceScope&) = delete;
private:
    std::pmr::memory_resource* old_;
};
}
int main() {
    wwl_report_handle* handle = nullptr;
    auto* original = std::pmr::get_default_resource();
    {
        // Real heap lifetime: a handle must not capture this host-owned resource.
        auto temporary = std::make_unique<std::pmr::unsynchronized_pool_resource>();
        {
            DefaultResourceScope restore{temporary.get()};
            CHECK(std::pmr::get_default_resource() == temporary.get());
            CHECK(wwl_report_create_v1(1, &handle) == WWL_OK);
        }
        CHECK(std::pmr::get_default_resource() == original);
        temporary.reset(); // The handle is still live; its PMR must be independent.
    }
    if (!handle) return 1;
    const wwl_report_settings_v1 settings{1000,0,1000,2,1,3,{'p','m','r'}};
    CHECK(wwl_report_replace_v1(handle,1,sizeof settings,&settings,"2 4 6 8",7) == WWL_OK);
    std::size_t required = 0;
    CHECK(wwl_report_copy_text_v1(handle,nullptr,0,&required) == WWL_BUFFER_TOO_SMALL);
    if (required) {
        std::vector<char> text(required);
        CHECK(wwl_report_copy_text_v1(handle,text.data(),text.size(),&required) == WWL_OK);
        CHECK(std::string(text.data()).find("label=pmr count=4") != std::string::npos);
        CHECK(std::string(text.data()).find("windows=3") != std::string::npos);
    } else {
        ++failures;
    }
    CHECK(wwl_report_destroy_v1(&handle) == WWL_OK && !handle);
    CHECK(std::pmr::get_default_resource() == original);
    std::cout << "production SHARED default-resource lifetime " << (failures ? "FAIL" : "PASS") << '\n';
    return failures ? 1 : 0;
}
