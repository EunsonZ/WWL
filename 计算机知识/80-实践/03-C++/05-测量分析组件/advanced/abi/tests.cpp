#include <wwl/measurement_abi.h>
#include <algorithm>
#include <array>
#include <cstddef>
#include <iostream>
#include <string>
#include <vector>
namespace wwl_abi_test {
void throw_next(int);
std::size_t live_handles(); std::size_t live_blocks(); std::size_t live_bytes();
void fail_pmr_at(wwl_report_handle*, std::size_t);
std::size_t pmr_calls(wwl_report_handle*);
}
int failures = 0;
#define CHECK(x) do { if (!(x)) { std::cerr << "FAIL " << __LINE__ << ": " << #x << '\n'; ++failures; } } while (0)
std::string read_text(wwl_report_handle* h) {
    std::size_t n=0;
    CHECK(wwl_report_copy_text_v1(h,nullptr,0,&n)==WWL_BUFFER_TOO_SMALL);
    if (!n) return {};
    std::vector<char> bytes(n);
    CHECK(wwl_report_copy_text_v1(h,bytes.data(),bytes.size(),&n)==WWL_OK);
    return bytes.data();
}
int main() {
    wwl_report_handle* h=nullptr;
    wwl_report_settings_v1 s{1000,0,1000,2,1,3,{'a','b','i'}};
    CHECK(wwl_report_create_v1(1,nullptr)==WWL_INVALID_ARGUMENT);
    CHECK(wwl_report_create_v1(2,nullptr)==WWL_VERSION_MISMATCH);
    CHECK(wwl_report_destroy_v1(nullptr)==WWL_INVALID_ARGUMENT);
    CHECK(wwl_report_create_v1(1,&h)==WWL_OK);
    CHECK(wwl_abi_test::live_handles()==1);
    auto* saved=h;
    CHECK(wwl_report_create_v1(1,&h)==WWL_INVALID_ARGUMENT && h==saved);
    std::size_t required=99;
    std::array<char,8> guard{}; guard.fill('!');
    CHECK(wwl_report_copy_text_v1(h,guard.data(),guard.size(),&required)==WWL_NOT_READY);
    CHECK(required==0 && std::all_of(guard.begin(),guard.end(),[](char c){return c=='!';}));
    CHECK(wwl_report_replace_v1(h,2,0,nullptr,nullptr,0)==WWL_VERSION_MISMATCH);
    CHECK(wwl_report_replace_v1(h,1,sizeof s-1,nullptr,nullptr,0)==WWL_SIZE_MISMATCH);
    CHECK(wwl_report_replace_v1(h,1,sizeof s+1,nullptr,nullptr,0)==WWL_SIZE_MISMATCH);
    CHECK(wwl_report_replace_v1(h,1,sizeof s,nullptr,nullptr,0)==WWL_INVALID_ARGUMENT);
    CHECK(wwl_report_replace_v1(nullptr,1,sizeof s,&s,nullptr,0)==WWL_INVALID_ARGUMENT);
    CHECK(wwl_report_replace_v1(h,1,sizeof s,&s,nullptr,1)==WWL_INVALID_ARGUMENT);
    std::string over(WWL_ABI_MAX_INPUT_BYTES_V1+1,' ');
    CHECK(wwl_report_replace_v1(h,1,sizeof s,&s,over.data(),over.size())==WWL_LIMIT_EXCEEDED);
    CHECK(wwl_report_replace_v1(h,1,sizeof s,&s,"2 4 6 8",7)==WWL_OK);
    const auto old=read_text(h);
    const auto blocks=wwl_abi_test::live_blocks(), bytes=wwl_abi_test::live_bytes();
    const auto allocations=wwl_abi_test::pmr_calls(h);
    CHECK(allocations>0 && blocks>0 && bytes>0);
    required=99;
    CHECK(wwl_report_copy_text_v1(h,nullptr,1,&required)==WWL_INVALID_ARGUMENT && required==99);
    CHECK(wwl_report_copy_text_v1(nullptr,nullptr,0,&required)==WWL_INVALID_ARGUMENT);
    CHECK(wwl_report_copy_text_v1(h,nullptr,0,nullptr)==WWL_INVALID_ARGUMENT);
    CHECK(wwl_report_copy_text_v1(h,guard.data(),0,&required)==WWL_BUFFER_TOO_SMALL);
    CHECK(required==old.size()+1 && guard[0]=='!');
    std::vector<char> output(required+3,'!');
    CHECK(wwl_report_copy_text_v1(h,output.data()+1,required-1,&required)==WWL_BUFFER_TOO_SMALL);
    CHECK(std::all_of(output.begin(),output.end(),[](char c){return c=='!';}));
    CHECK(wwl_report_copy_text_v1(h,output.data()+1,required+1,&required)==WWL_OK);
    CHECK(output.front()=='!' && output[required]=='\0' && output[required+1]=='!' && output.back()=='!');
    for (const auto& bad : {std::string("-1"),std::string("4096"),std::string("2 bad"),std::string("2\0 4",4)}) {
        CHECK(wwl_report_replace_v1(h,1,sizeof s,&s,bad.data(),bad.size())==WWL_INVALID_ARGUMENT);
        CHECK(read_text(h)==old);
    }
    for (int field=0;field<7;++field) {
        auto bad=s;
        switch(field) {
        case 0: bad.gain_uV_per_code=0; break;
        case 1: bad.offset_uV=1000001; break;
        case 2: bad.interval_ms=0; break;
        case 3: bad.width=4097; break;
        case 4: bad.hop=0; break;
        case 5: bad.label_bytes=41; break;
        case 6: bad.label[0]='!'; break;
        }
        CHECK(wwl_report_replace_v1(h,1,sizeof bad,&bad,"1 2",3)==WWL_INVALID_ARGUMENT);
        CHECK(read_text(h)==old);
    }
    // Real Snapshot/window/text allocation attempts in the reused ReportSession.
    for (std::size_t fail=1;fail<=allocations;++fail) {
        wwl_abi_test::fail_pmr_at(h,fail);
        CHECK(wwl_report_replace_v1(h,1,sizeof s,&s,"2 4 6 8",7)==WWL_OUT_OF_MEMORY);
        CHECK(read_text(h)==old);
        CHECK(wwl_abi_test::live_blocks()==blocks && wwl_abi_test::live_bytes()==bytes);
    }
    wwl_abi_test::fail_pmr_at(h,0);
    // Each export executes the same catch boundary; this uninstalled variant
    // injects before any side effect. It does not claim real OS allocation failure.
    const std::array<wwl_status,5> mapped{WWL_OUT_OF_MEMORY,WWL_INVALID_ARGUMENT,
        WWL_LIMIT_EXCEEDED,WWL_INTERNAL_ERROR,WWL_INTERNAL_ERROR};
    for (int kind=1;kind<=5;++kind) {
        wwl_report_handle* fresh=nullptr;
        wwl_abi_test::throw_next(kind);
        CHECK(wwl_report_create_v1(1,&fresh)==mapped[kind-1] && !fresh);
        wwl_abi_test::throw_next(kind);
        CHECK(wwl_report_replace_v1(h,1,sizeof s,&s,"1",1)==mapped[kind-1]);
        wwl_abi_test::throw_next(kind);
        CHECK(wwl_report_copy_text_v1(h,nullptr,0,&required)==mapped[kind-1]);
        wwl_report_layout_v1 layout{};
        wwl_abi_test::throw_next(kind);
        CHECK(wwl_report_get_layout_v1(1,sizeof layout,&layout)==mapped[kind-1]);
        wwl_abi_test::throw_next(kind);
        CHECK(wwl_report_destroy_v1(&h)==mapped[kind-1] && h==saved);
        CHECK(read_text(h)==old && wwl_abi_test::live_handles()==1);
    }
    wwl_report_layout_v1 layout{};
    CHECK(wwl_report_get_layout_v1(2,0,nullptr)==WWL_VERSION_MISMATCH);
    CHECK(wwl_report_get_layout_v1(1,0,nullptr)==WWL_SIZE_MISMATCH);
    CHECK(wwl_report_get_layout_v1(1,sizeof layout,nullptr)==WWL_INVALID_ARGUMENT);
    CHECK(wwl_report_get_layout_v1(1,sizeof layout,&layout)==WWL_OK);
    CHECK(layout.settings_size==sizeof s && layout.settings_alignment==alignof(decltype(s)));
    CHECK(wwl_report_replace_v1(h,1,sizeof s,&s,nullptr,0)==WWL_OK);
    CHECK(read_text(h).find("count=0")!=std::string::npos);
    auto changed=s;
    changed.gain_uV_per_code=500; changed.offset_uV=1000; changed.interval_ms=250;
    CHECK(wwl_report_replace_v1(h,1,sizeof changed,&changed,"1 3 5",5)==WWL_OK);
    const auto transferred=read_text(h);
    CHECK(transferred.find("first_ms=0 last_ms=250 sum_mV=4 mean_mV=2 population_variance_mV2=0.25 rms_squared_mV2=4.25")!=std::string::npos);
    CHECK(transferred.find("first_ms=250 last_ms=500 sum_mV=6 mean_mV=3 population_variance_mV2=0.25 rms_squared_mV2=9.25")!=std::string::npos);
    std::string maximum;
    for (int i=0;i<4096;++i) maximum += "1 ";
    CHECK(maximum.size()==WWL_ABI_MAX_INPUT_BYTES_V1);
    CHECK(wwl_report_replace_v1(h,1,sizeof s,&s,maximum.data(),maximum.size())==WWL_OK);
    CHECK(read_text(h).find("count=4096")!=std::string::npos);
    CHECK(read_text(h).find("windows=4095")!=std::string::npos);
    CHECK(wwl_report_destroy_v1(&h)==WWL_OK && !h);
    CHECK(wwl_report_destroy_v1(&h)==WWL_OK);
    CHECK(wwl_abi_test::live_handles()==0 && wwl_abi_test::live_blocks()==0 && wwl_abi_test::live_bytes()==0);
    std::cout << "PMR failure points=" << allocations << " live_handles=" << wwl_abi_test::live_handles()
              << " live_blocks=" << wwl_abi_test::live_blocks() << " live_bytes=" << wwl_abi_test::live_bytes() << '\n';
    std::cout << "C++=" << __cplusplus;
#ifdef _LIBCPP_VERSION
    std::cout << " libc++=" << _LIBCPP_VERSION;
#endif
    std::cout << '\n';
    std::cout << "exception maps=5 exports=5; ABI contracts " << (failures ? "FAIL" : "PASS") << '\n';
    return failures ? 1 : 0;
}
