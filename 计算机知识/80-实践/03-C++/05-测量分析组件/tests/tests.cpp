#include "wwl/measurement.hpp"
#include "layout_math.hpp"
#include <array>
#include <cfenv>
#include <cmath>
#include <iostream>
#include <limits>
#include <sstream>
#include <stdexcept>
#include <string_view>
#include <utility>

using namespace wwl;
template<class Range> concept Summable = requires(Range& r) { sum_codes(r); };
template<class T> concept RvalueView = requires(T&& object) { std::move(object).codes(); };
static_assert(Summable<std::vector<RawCode>>);
static_assert(!Summable<std::vector<int>>);
static_assert(!RvalueView<Batch>);
static_assert(std::same_as<decltype(std::declval<const Batch&>().calibration()), Calibration>);
static_assert(std::same_as<decltype(std::declval<Batch&&>().calibration()), Calibration>);
static_assert(std::is_nothrow_move_constructible_v<Batch>);

int main() {
    int failures = 0;
    auto check = [&](bool condition, std::string_view label) {
        if (!condition) { ++failures; std::cerr << "FAILED: " << label << '\n'; }
    };
    auto rejects = [&]<class Function>(Function action, std::string_view label) {
        bool caught = false;
        try { action(); } catch (const std::exception&) { caught = true; }
        check(caught,label);
    };
    std::istringstream input("2 4 6 8");
    auto batch = read_batch(input);
    std::istringstream calibration_input("2 4");
    // The returned Calibration temporary is an independent value. This reference
    // extends its own lifetime, rather than borrowing the destroyed Batch member.
    const auto& saved_calibration = read_batch(calibration_input, Calibration{500,1000}).calibration();
    check(saved_calibration.gain() == 500 && saved_calibration.offset() == 1000,
          "temporary Batch returns independent calibration value");
    auto stats = describe(batch);
    check(stats && stats->count == 4 && stats->sum.value == 20 && stats->mean.value == 5,
          "count/sum/mean with units");
    check(stats && stats->population_variance.value == 5 && stats->rms_squared.value == 30,
          "population variance and RMS squared");
    check(stats && stats->sample_variance && stats->sample_variance->value == 20.0/3.0,
          "different sample denominator");
    auto copied = batch;
    check(copied.codes().data() != batch.codes().data() && copied.codes()[0].value() == 2,
          "copy owns a separate allocation");
    auto moved = std::move(copied);
    check(moved.codes().size() == 4, "move destination receives values");
    // Source is deliberately only destroyed or assigned; no assumption that it is empty.
    copied = Batch{{}};
    check(!describe(copied), "empty result outside TensorBuffer");
    std::istringstream singleton("4095");
    auto one = read_batch(singleton);
    check(!describe(one)->sample_variance && describe(one)->population_variance.value == 0,
          "n=1 has no sample variance");
    std::istringstream bounds("0 4095");
    auto boundary_batch = read_batch(bounds);
    check(boundary_batch.codes().size() == 2, "inclusive code bounds");
    for (const auto* text : {"-1", "4096", "2oops", "1.0", "2147483648"})
        rejects([&] { std::istringstream bad(text); static_cast<void>(read_batch(bad)); }, "parse domain rejection");
    rejects([] { static_cast<void>(Calibration{0}); }, "gain domain");
    rejects([] { static_cast<void>(Calibration{1,1000001}); }, "offset domain");
    rejects([] { static_cast<void>(Batch{{},Calibration{},Seconds{0}}); }, "time domain");
    rejects([] { static_cast<void>(Batch{{},Calibration{},Seconds{std::numeric_limits<double>::infinity()}}); }, "time finite");
    rejects([&] { std::vector<RawCode> large(max_samples+1,RawCode{1}); static_cast<void>(Batch{std::move(large)}); }, "count domain");
    std::istringstream bad_replace("2 4oops");
    rejects([&] { replace_from_stream(batch,bad_replace); }, "failed replacement");
    check(batch.codes().size() == 4 && describe(batch)->sum.value == 20 && batch.calibration().gain() == 1000,
          "failure preserves batch and configuration");
    // A genuine stream failure, rather than a malformed token, exercises the I/O branch.
    std::istringstream broken("2 4"); broken.setstate(std::ios::badbit);
    rejects([&] { replace_from_stream(batch,broken); }, "bad stream rejection");
    check(describe(batch)->sum.value == 20, "I/O failure preserves batch");
    std::istringstream replacement("3 5"); replace_from_stream(batch,replacement);
    check(describe(batch)->sum.value == 8, "successful transaction commits");
    struct Record { RawCode code; int id; };
    const std::array<Record,2> records{{{RawCode{3},42},{RawCode{5},43}}};
    check(sum_codes(records,[](const Record& r) { return r.code; }) == 8, "projected generic input");
    const std::array<Batch,2> channels{batch,one};
    rejects([&] { static_cast<void>(channel_means(channels)); }, "mismatched tensor rows");
    const std::array<Batch,2> equal{batch,batch};
    auto means = channel_means(equal);
    check(means.size() == 2 && means[0].value == 4 && means[1].value == 4, "TensorBuffer consumer");
    const std::array<Batch,1> empty{Batch{{}}};
    rejects([&] { static_cast<void>(channel_means(empty)); }, "empty shape rejected before tensor");
    rejects([&] { static_cast<void>(compare_reductions(batch,0)); }, "zero worker rejected");
    // Small integer results alone do not justify bitwise equality for fractional calibration.
    std::vector<RawCode> codes;
    for (int i=0;i<4096;++i) codes.emplace_back(i);
    Batch fractional{std::move(codes),Calibration{7,-900000}};
    for (std::size_t workers : {1U,2U,3U,7U}) {
        auto result = compare_reductions(fractional,workers);
        check(std::abs(result.serial.value-result.reference.value) <= result.absolute_error_bound.value,
              "serial derived error bound");
        check(std::abs(result.parallel.value-result.reference.value) <= result.absolute_error_bound.value,
              "parallel derived error bound");
    }
    check(compare_reductions(one,7).parallel.value == 4095, "workers clamped to count");
    check(compare_reductions(empty.front(),2).parallel.value == 0, "empty sum identity");
    const bool model = std::numeric_limits<float>::is_iec559 && std::numeric_limits<float>::digits == 24 &&
                       std::numeric_limits<double>::is_iec559 && std::numeric_limits<double>::digits == 53 &&
                       std::fegetround() == FE_TONEAREST;
    check(model, "binary32/binary64 nearest model applicability");
    if (model) {
        const std::array<float,4> values{std::ldexp(1.0F,54),1.0F,-std::ldexp(1.0F,54),1.0F};
        check(sum_soa(values) == 1, "controlled serial left fold is 1");
        check(parallel_sum_soa(values,2) == 0, "controlled two block reduction is 0");
        std::cout << "controlled model: serial=1 parallel=0 exact_real=2\n";
    }
    std::cout << "float_digits=" << std::numeric_limits<float>::digits
              << " double_digits=" << std::numeric_limits<double>::digits
              << " rounding=" << std::fegetround() << " failures=" << failures << '\n';
    return failures ? 1 : 0;
}
