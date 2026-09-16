#include <algorithm>
#include <chrono>
#include <cmath>
#include <cstddef>
#include <cstdlib>
#include <iostream>
#include <numeric>
#include <string>
#include <string_view>
#include <utility>
#include <vector>

std::string compiler_description() {
#if defined(__clang__)
    return "Clang " + std::to_string(__clang_major__) + "." + std::to_string(__clang_minor__) + "." +
           std::to_string(__clang_patchlevel__);
#elif defined(__GNUC__)
    return "GCC " + std::to_string(__GNUC__) + "." + std::to_string(__GNUC_MINOR__) + "." +
           std::to_string(__GNUC_PATCHLEVEL__);
#elif defined(_MSC_VER)
    return "MSVC " + std::to_string(_MSC_VER);
#else
    return "unknown";
#endif
}

constexpr std::string_view build_mode() {
#if defined(NDEBUG)
    return "NDEBUG/optimized-like";
#else
    return "debug-like";
#endif
}

double sum_row_major(const std::vector<double>& matrix, std::size_t rows, std::size_t columns) {
    double sum = 0.0;
    for (std::size_t row = 0; row < rows; ++row) {
        for (std::size_t column = 0; column < columns; ++column) {
            sum += matrix[row * columns + column];
        }
    }
    return sum;
}

double sum_column_major(const std::vector<double>& matrix, std::size_t rows, std::size_t columns) {
    double sum = 0.0;
    for (std::size_t column = 0; column < columns; ++column) {
        for (std::size_t row = 0; row < rows; ++row) {
            sum += matrix[row * columns + column];
        }
    }
    return sum;
}

template <class Function>
std::pair<long long, double> measure_microseconds(Function&& function) {
    const auto start = std::chrono::steady_clock::now();
    const double checksum = function();
    const auto elapsed = std::chrono::steady_clock::now() - start;
    return {std::chrono::duration_cast<std::chrono::microseconds>(elapsed).count(), checksum};
}

long long median(std::vector<long long> samples) {
    std::sort(samples.begin(), samples.end());
    return samples[samples.size() / 2];
}

bool self_test() {
    const std::vector<double> matrix{1.0, 2.0, 3.0, 4.0, 5.0, 6.0};
    return sum_row_major(matrix, 2, 3) == 21.0 && sum_column_major(matrix, 2, 3) == 21.0;
}

int main(int argc, char* argv[]) {
    if (argc == 2 && std::string_view(argv[1]) == "--self-test") {
        const bool passed = self_test();
        std::cout << (passed ? "self-test passed\n" : "self-test failed\n");
        return passed ? 0 : 1;
    }

    constexpr std::size_t rows = 2048;
    constexpr std::size_t columns = 2048;
    constexpr int rounds = 7;
    std::vector<double> matrix(rows * columns);
    for (std::size_t index = 0; index < matrix.size(); ++index) {
        matrix[index] = static_cast<double>(index % 251U) / 251.0;
    }

    std::vector<long long> row_times;
    std::vector<long long> column_times;
    double checksum_guard = 0.0;
    for (int round = 0; round < rounds; ++round) {
        if (round % 2 == 0) {
            const auto row = measure_microseconds([&] { return sum_row_major(matrix, rows, columns); });
            const auto column =
                measure_microseconds([&] { return sum_column_major(matrix, rows, columns); });
            row_times.push_back(row.first);
            column_times.push_back(column.first);
            checksum_guard += row.second + column.second;
        } else {
            const auto column =
                measure_microseconds([&] { return sum_column_major(matrix, rows, columns); });
            const auto row = measure_microseconds([&] { return sum_row_major(matrix, rows, columns); });
            column_times.push_back(column.first);
            row_times.push_back(row.first);
            checksum_guard += row.second + column.second;
        }
    }

    const double expected = sum_row_major(matrix, rows, columns);
    const double observed = checksum_guard / (2.0 * rounds);
    if (std::abs(expected - observed) > std::abs(expected) * 1e-12) {
        std::cerr << "checksum mismatch\n";
        return 1;
    }

    std::cout << "compiler=" << compiler_description() << ", build_mode=" << build_mode() << '\n'
              << "layout=row-major, rows=" << rows << ", columns=" << columns
              << ", rounds=" << rounds << '\n'
              << "row_major_us=";
    for (const auto value : row_times) {
        std::cout << value << ' ';
    }
    std::cout << "median=" << median(row_times) << '\n' << "column_major_us=";
    for (const auto value : column_times) {
        std::cout << value << ' ';
    }
    std::cout << "median=" << median(column_times) << '\n' << "checksum=" << observed << '\n';
}
