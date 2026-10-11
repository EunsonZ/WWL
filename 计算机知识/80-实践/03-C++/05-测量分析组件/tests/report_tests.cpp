#include "wwl/report.hpp"
#include <array>
#include <iostream>
#include <sstream>
#include <type_traits>

using namespace wwl;
class CountingResource final : public std::pmr::memory_resource {
public:
    std::size_t attempts=0, fail_at=0, live_blocks=0, live_bytes=0;
    void arm(std::size_t failure=0) { attempts=0; fail_at=failure; }
private:
    void* do_allocate(std::size_t bytes, std::size_t alignment) override {
        ++attempts;
        if (fail_at && attempts==fail_at) throw std::bad_alloc{};
        auto* pointer=std::pmr::new_delete_resource()->allocate(bytes,alignment);
        ++live_blocks;live_bytes+=bytes;return pointer;
    }
    void do_deallocate(void* pointer,std::size_t bytes,std::size_t alignment) override {
        --live_blocks;live_bytes-=bytes;
        std::pmr::new_delete_resource()->deallocate(pointer,bytes,alignment);
    }
    bool do_is_equal(const std::pmr::memory_resource& other) const noexcept override {
        return this==&other;
    }
};
template<class T> concept TemporaryText = requires(T&& value) { std::move(value).text(); };
static_assert(!TemporaryText<ReportSession>);
static_assert(!std::is_copy_constructible_v<ReportSession>);
static_assert(std::same_as<decltype(std::declval<ReportSettings&&>().label()),std::string>);

int main() {
    int failures=0;
    auto check=[&](bool condition,const char* label) {
        if (!condition) { ++failures;std::cerr << "FAILED: " << label << '\n'; }
    };
    auto rejects=[&](auto action,const char* label) {
        bool caught=false;try { action(); } catch(const std::exception&) { caught=true; }check(caught,label);
    };
    ReportSession session;
    check(!session.settings() && session.windows().empty() && session.text().empty(),"uninitialized snapshot");
    std::istringstream input("2 4 6 8");
    session.replace(input,ReportSettings{Calibration{},std::chrono::milliseconds{1000},WindowSpec{2,1},"adc"});
    auto windows=session.windows();
    check(windows.size()==3,"full overlapping windows");
    const std::array<double,3> means{3,5,7};
    for (std::size_t i=0;i<windows.size();++i) {
        check(windows[i].begin==i && windows[i].end==i+2,"half-open index convention");
        check(windows[i].first_sample_time==std::chrono::milliseconds{1000*static_cast<int>(i)} &&
              windows[i].last_sample_time==std::chrono::milliseconds{1000*static_cast<int>(i+1)},"sample timestamps");
        check(windows[i].statistics.mean.value==means[i] &&
              windows[i].statistics.population_variance.value==1,"window statistics");
    }
    check(windows[0].statistics.rms_squared.value==10 && windows[1].statistics.rms_squared.value==26 &&
          windows[2].statistics.rms_squared.value==50,"RMS is not variance");
    const std::string old_text(session.text());
    std::istringstream invalid("2 x 8");rejects([&]{session.replace(invalid);},"parse failure");
    check(session.text()==old_text,"parse failure preserves snapshot");
    std::istringstream broken("2 4");broken.setstate(std::ios::badbit);
    rejects([&]{session.replace(broken);},"read failure");check(session.text()==old_text,"read failure preserves snapshot");
    std::istringstream empty;
    session.replace(empty);check(session.windows().empty() && session.text().find("windows=0")!=std::string_view::npos,"empty report");
    std::istringstream short_input("2 4 6 8");session.replace(short_input,ReportSettings{Calibration{},std::chrono::milliseconds{250},WindowSpec{3,2}});
    check(session.windows().size()==1 && session.windows()[0].end==3 &&
          session.windows()[0].last_sample_time==std::chrono::milliseconds{500},"discard incomplete tail; last timestamp end-1");
    std::string maximum_input;
    for (std::size_t i=0;i<max_samples;++i) maximum_input.append("0 ");
    std::istringstream maximum_stream(maximum_input);
    session.replace(maximum_stream,ReportSettings{Calibration{},std::chrono::milliseconds{86400000},WindowSpec{1,65535}});
    check(session.windows().size()==2 && session.windows()[1].last_sample_time.count()==65535LL*86400000LL,
          "maximum legal sample timestamp fits integer chrono representation");
    std::istringstream singleton("1");session.replace(singleton,ReportSettings{Calibration{},std::chrono::milliseconds{1},WindowSpec{1,1}});
    check(session.windows()[0].first_sample_time==session.windows()[0].last_sample_time &&
          !session.windows()[0].statistics.sample_variance,"one-sample window");
    rejects([]{static_cast<void>(WindowSpec{0,1});},"zero width");
    rejects([]{static_cast<void>(WindowSpec{2,0});},"zero hop");
    rejects([]{static_cast<void>(WindowSpec{65537,1});},"window count limit");
    rejects([]{static_cast<void>(ReportSettings{Calibration{},std::chrono::milliseconds{0}});},"interval limit");
    rejects([]{static_cast<void>(ReportSettings{Calibration{},std::chrono::milliseconds{1},WindowSpec{},"bad label"});},"label grammar");
    rejects([]{static_cast<void>(ReportSession{nullptr});},"null resource");
    std::vector<RawCode> excessive(max_samples+1,RawCode{0});
    rejects([&]{static_cast<void>(describe_codes(excessive,Calibration{}));},"borrowed statistics count limit");
    const std::array<std::string_view,10> valid{
        "--input","codes.txt","--gain-uv","500","--offset-uv","1000","--interval-ms","250","--window","2"};
    auto options=parse_report_options(valid);
    check(options.settings.calibration().gain()==500 && options.settings.interval()==std::chrono::milliseconds{250},"typed application options");
    const std::array<std::string_view,4> duplicate{"--input","a","--input","b"};
    rejects([&]{static_cast<void>(parse_report_options(duplicate));},"duplicate option");
    const std::array<std::string_view,4> malformed{"--input","a","--interval-ms","1.2"};
    rejects([&]{static_cast<void>(parse_report_options(malformed));},"integer option grammar");
    const std::array<std::string_view,1> missing{"--input"};
    rejects([&]{static_cast<void>(parse_report_options(missing));},"missing option value");
    rejects([]{static_cast<void>(parse_report_options({}));},"required input");
    std::ostringstream bad_output;bad_output.setstate(std::ios::badbit);
    rejects([&]{emit_report(bad_output,"text");},"output failure");

    // Discover the number of allocation points from a real successful replacement.
    // Do not assume a string growth policy or a fixed standard-library allocation count.
    std::string next_input;
    for (int i=0;i<64;++i) next_input+=std::to_string(i)+" ";
    ReportSettings next_settings{Calibration{500,1000},std::chrono::milliseconds{10},WindowSpec{4,2},"next-run"};
    std::size_t allocation_points=0;
    {
        CountingResource resource;
        {
            ReportSession probe(&resource);std::istringstream stream(next_input);resource.arm();
            probe.replace(stream,next_settings);allocation_points=resource.attempts;
            check(resource.live_blocks>0 && resource.live_bytes>0,"successful result owns counted allocations");
        }
        check(resource.live_blocks==0 && resource.live_bytes==0,"successful destruction releases all counted storage");
    }
    check(allocation_points>2,"snapshot, window vector and report text really allocate");
    CountingResource resource;
    {
        ReportSession tested(&resource);std::istringstream old_input("2 4 6 8");
        tested.replace(old_input,ReportSettings{Calibration{},std::chrono::milliseconds{1000},WindowSpec{2,1},"old-run"});
        const std::string saved_text(tested.text());
        const auto old_pointer=tested.windows().data();
        const auto blocks=resource.live_blocks,bytes=resource.live_bytes;
        for (std::size_t point=1;point<=allocation_points;++point) {
            resource.arm(point);std::istringstream stream(next_input);bool failed=false;
            try {tested.replace(stream,next_settings);} catch(const std::bad_alloc&) {failed=true;}
            check(failed,"each selected PMR allocation point throws");
            check(tested.text()==saved_text && tested.windows().data()==old_pointer && tested.windows().size()==3,
                  "allocation failure preserves old result and its live views");
            const auto saved_settings=tested.settings();
            check(saved_settings && saved_settings->label()=="old-run" && saved_settings->calibration().gain()==1000 &&
                  saved_settings->interval()==std::chrono::milliseconds{1000},"allocation failure preserves configuration");
            check(resource.live_blocks==blocks && resource.live_bytes==bytes,"failed candidate releases all newly counted storage");
        }
        resource.arm();std::istringstream stream(next_input);tested.replace(stream,next_settings);
        check(tested.windows().size()==31 && tested.settings()->label()=="next-run","successful replacement commits new snapshot");
        // old_pointer is not dereferenced after successful replacement.
    }
    check(resource.live_blocks==0 && resource.live_bytes==0,"session destruction leaves zero live blocks and bytes");
    std::cout << "PMR allocation failure points=" << allocation_points << " live_blocks=" << resource.live_blocks
              << " live_bytes=" << resource.live_bytes << " failures=" << failures << '\n';
    return failures ? 1 : 0;
}
