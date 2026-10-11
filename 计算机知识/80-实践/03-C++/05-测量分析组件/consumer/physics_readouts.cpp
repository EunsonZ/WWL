#include <wwl/measurement.hpp>
#include <array>
#include <cmath>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <sstream>
#include <string>
#include <vector>

int main(int argc, char** argv) {
    try {
        if (argc != 2) throw std::invalid_argument("expected one readout file");
        std::ifstream input(argv[1]);
        if (!input) throw std::runtime_error("cannot open readouts");
        const std::array<std::string,3> names{"thermal","quantum","diode"};
        const std::array<double,3> intervals{1.,2e-7,0.};
        // Fractions independently derived from the finite reference codes.
        const std::array<double,3> sums{7043.,3500.,3342.};
        std::cout << std::setprecision(17);
        for (std::size_t channel=0; channel<names.size(); ++channel) {
            std::string line, name, extra;
            if (!std::getline(input,line)) throw std::invalid_argument("missing channel");
            std::istringstream row(line);
            double interval=0.; int count=0;
            if (!(row>>name>>interval>>count) || name!=names[channel] || count!=6 ||
                !std::isfinite(interval) || interval!=intervals[channel])
                throw std::invalid_argument("channel, count or coordinate contract");
            std::vector<wwl::RawCode> codes;
            for (int i=0; i<count; ++i) {
                int code=0;
                if (!(row>>code)) throw std::invalid_argument("invalid code token");
                codes.emplace_back(code);
            }
            if (row>>extra) throw std::invalid_argument("extra field");
            std::optional<wwl::Statistics> stats;
            if (interval>0.) {
                // Real relative seconds only for the two time-indexed projections.
                const wwl::Batch batch(std::move(codes),wwl::Calibration{1000,0},
                                       wwl::Seconds{interval});
                stats=wwl::describe(batch);
            } else {
                // A source-voltage scan has no time axis: do not create Seconds{0}.
                stats=wwl::describe_codes(codes,wwl::Calibration{1000,0});
            }
            if (!stats || stats->count!=6 || stats->sum.value!=sums[channel])
                throw std::runtime_error("reference sum/count mismatch");
            if (std::abs(stats->rms_squared.value-(stats->mean.value*stats->mean.value+
                stats->population_variance.value))>1e-8)
                throw std::runtime_error("finite-record square identity");
            std::cout<<name<<" count="<<stats->count<<" sum_mV="<<stats->sum.value
                     <<" mean_mV="<<stats->mean.value
                     <<" variance_mV2="<<stats->population_variance.value
                     <<" rms2_mV2="<<stats->rms_squared.value<<"\n";
        }
        std::string tail;
        if (std::getline(input,tail) || input.bad())
            throw std::invalid_argument("extra channel or read failure");
        // The ADC page's 375000 microvolts/code is outside the public API domain.
        bool rejected=false;
        try { (void)wwl::Calibration{375000,0}; }
        catch (const std::invalid_argument&) { rejected=true; }
        if (!rejected) throw std::runtime_error("calibration domain widened");
        std::cout<<"physical_consumer=PASS voltage_projections,coordinate_contract,calibration_rejection\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr<<"physical_consumer_error="<<error.what()<<"\n";
        return 2;
    }
}
