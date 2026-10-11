#include "wwl/report.hpp"
#include <fstream>
#include <iostream>
#include <vector>
int main(int argc, char** argv) {
    try {
        std::vector<std::string_view> arguments;
        for (int i=1;i<argc;++i) arguments.emplace_back(argv[i]);
        const auto options = wwl::parse_report_options(arguments);
        std::ifstream input(options.input);
        if (!input) throw std::runtime_error("cannot open measurement input");
        wwl::ReportSession session;
        session.replace(input,options.settings);
        if (options.output) wwl::write_report_file(*options.output,session.text());
        else wwl::emit_report(std::cout,session.text());
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "measurement_report: " << error.what() << '\n';
        return 2;
    }
}
