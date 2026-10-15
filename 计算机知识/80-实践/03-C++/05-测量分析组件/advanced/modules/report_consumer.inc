// Shared control flow only; numerical implementation stays in the original library.
int main(int argc, char** argv) {
    if (argc != 2) {
        std::cerr << "usage: consumer CODES_FILE\n";
        return 2;
    }
    try {
#ifdef WWL_MODULE_CONSUMER
        if (api::interface_revision() != 1) return 3;
#endif
        std::ifstream input(argv[1]);
        if (!input) throw std::runtime_error("cannot open codes file");
        api::ReportSession session;
        session.replace(input, api::ReportSettings{api::Calibration{},
            std::chrono::milliseconds{1000}, api::WindowSpec{2,1}, "adc"});
        // Use a fresh borrow while session is still alive. No view crosses its lifetime.
        std::cout << session.text();
        if (!std::cout) return 2;
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "error: " << error.what() << '\n';
        return 2;
    }
}
