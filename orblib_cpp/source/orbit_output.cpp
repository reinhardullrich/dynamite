#include "orbit_output.hpp"

#include <algorithm>
#include <cmath>
#include <cstddef>
#include <cstdint>
#include <fstream>
#include <iomanip>
#include <limits>
#include <string>
#include <vector>

namespace dynamite::orblib_cpp {
namespace {

constexpr int kQgridChannelCount = 16;

bool checked_mul_int(int lhs, int rhs, int& result) noexcept {
    if (lhs < 0 || rhs < 0) {
        return false;
    }
    if (lhs != 0 && rhs > std::numeric_limits<int>::max() / lhs) {
        return false;
    }
    result = lhs * rhs;
    return true;
}

class FortranRecordWriter {
public:
    explicit FortranRecordWriter(const char* path)
        : stream_(std::string(path), std::ios::binary | std::ios::out | std::ios::trunc) {}

    bool ok() const noexcept {
        return stream_.good();
    }

    template <typename T>
    bool write_array(const T* values, std::size_t count) noexcept {
        if (count > 0 && values == nullptr) {
            return false;
        }
        const std::size_t bytes = count * sizeof(T);
        if (count != 0 && bytes / count != sizeof(T)) {
            return false;
        }
        if (bytes > static_cast<std::size_t>(std::numeric_limits<std::int32_t>::max())) {
            return false;
        }

        const auto record_size = static_cast<std::int32_t>(bytes);
        stream_.write(reinterpret_cast<const char*>(&record_size), sizeof(record_size));
        if (bytes > 0) {
            stream_.write(reinterpret_cast<const char*>(values), static_cast<std::streamsize>(bytes));
        }
        stream_.write(reinterpret_cast<const char*>(&record_size), sizeof(record_size));
        return stream_.good();
    }

    bool write_losvd_setup_header(
        std::int32_t aperture_count,
        std::int32_t half_bin_count,
        double velocity_bin_width
    ) noexcept {
        constexpr std::int32_t record_size =
            static_cast<std::int32_t>(2 * sizeof(std::int32_t) + sizeof(double));
        stream_.write(reinterpret_cast<const char*>(&record_size), sizeof(record_size));
        stream_.write(reinterpret_cast<const char*>(&aperture_count), sizeof(aperture_count));
        stream_.write(reinterpret_cast<const char*>(&half_bin_count), sizeof(half_bin_count));
        stream_.write(reinterpret_cast<const char*>(&velocity_bin_width), sizeof(velocity_bin_width));
        stream_.write(reinterpret_cast<const char*>(&record_size), sizeof(record_size));
        return stream_.good();
    }

private:
    std::ofstream stream_;
};

std::size_t qgrid_values_per_orbit(int radius_bin_count, int theta_bin_count, int phi_bin_count) noexcept {
    return static_cast<std::size_t>(kQgridChannelCount) *
           static_cast<std::size_t>(phi_bin_count) *
           static_cast<std::size_t>(theta_bin_count) *
           static_cast<std::size_t>(radius_bin_count);
}

}  // namespace

bool write_qgrid_file(
    const char* path,
    int orbit_count,
    int energy_count,
    int i2_count,
    int i3_count,
    int dithering,
    int not_regularizable_count,
    int radius_bin_count,
    int theta_bin_count,
    int phi_bin_count,
    const double* radius_boundaries,
    const double* theta_boundaries,
    const double* phi_boundaries,
    const int* orbit_types,
    const double* qgrids
) noexcept {
    std::vector<int> counts(static_cast<std::size_t>(std::max(orbit_count, 0)), not_regularizable_count);
    return write_qgrid_file_with_not_regularizable_counts(
        path,
        orbit_count,
        energy_count,
        i2_count,
        i3_count,
        dithering,
        counts.data(),
        radius_bin_count,
        theta_bin_count,
        phi_bin_count,
        radius_boundaries,
        theta_boundaries,
        phi_boundaries,
        orbit_types,
        qgrids
    );
}

bool write_qgrid_file_with_not_regularizable_counts(
    const char* path,
    int orbit_count,
    int energy_count,
    int i2_count,
    int i3_count,
    int dithering,
    const int* not_regularizable_counts,
    int radius_bin_count,
    int theta_bin_count,
    int phi_bin_count,
    const double* radius_boundaries,
    const double* theta_boundaries,
    const double* phi_boundaries,
    const int* orbit_types,
    const double* qgrids
) noexcept {
    if (path == nullptr || orbit_count <= 0 || energy_count <= 0 || i2_count <= 0 ||
        i3_count <= 0 || dithering <= 0 || not_regularizable_counts == nullptr ||
        radius_bin_count <= 0 || theta_bin_count <= 0 || phi_bin_count <= 0 ||
        radius_boundaries == nullptr || theta_boundaries == nullptr ||
        phi_boundaries == nullptr || orbit_types == nullptr || qgrids == nullptr) {
        return false;
    }
    for (int orbit_index = 0; orbit_index < orbit_count; ++orbit_index) {
        if (not_regularizable_counts[orbit_index] < 0) {
            return false;
        }
    }

    int expected_orbits = 0;
    int expected_orbits_tmp = 0;
    if (!checked_mul_int(energy_count, i2_count, expected_orbits_tmp) ||
        !checked_mul_int(expected_orbits_tmp, i3_count, expected_orbits) ||
        expected_orbits != orbit_count) {
        return false;
    }

    int dither_count = 0;
    int dither_count_tmp = 0;
    if (!checked_mul_int(dithering, dithering, dither_count_tmp) ||
        !checked_mul_int(dither_count_tmp, dithering, dither_count)) {
        return false;
    }

    FortranRecordWriter writer(path);
    if (!writer.ok()) {
        return false;
    }

    const std::int32_t library_header[5] = {
        static_cast<std::int32_t>(orbit_count),
        static_cast<std::int32_t>(energy_count),
        static_cast<std::int32_t>(i2_count),
        static_cast<std::int32_t>(i3_count),
        static_cast<std::int32_t>(dithering),
    };
    const std::int32_t grid_header[4] = {
        kQgridChannelCount,
        static_cast<std::int32_t>(phi_bin_count),
        static_cast<std::int32_t>(theta_bin_count),
        static_cast<std::int32_t>(radius_bin_count),
    };
    if (!writer.write_array(library_header, 5) ||
        !writer.write_array(grid_header, 4) ||
        !writer.write_array(radius_boundaries, static_cast<std::size_t>(radius_bin_count + 1)) ||
        !writer.write_array(theta_boundaries, static_cast<std::size_t>(theta_bin_count + 1)) ||
        !writer.write_array(phi_boundaries, static_cast<std::size_t>(phi_bin_count + 1))) {
        return false;
    }

    const std::size_t qgrid_stride =
        qgrid_values_per_orbit(radius_bin_count, theta_bin_count, phi_bin_count);
    for (int orbit_index = 0; orbit_index < orbit_count; ++orbit_index) {
        const int orbit_number = orbit_index + 1;
        const int i3 = (orbit_index % i3_count) + 1;
        const int i2 = ((orbit_index / i3_count) % i2_count) + 1;
        const int energy = (orbit_index / (i3_count * i2_count)) + 1;
        const std::int32_t orbit_header[5] = {
            static_cast<std::int32_t>(orbit_number),
            static_cast<std::int32_t>(energy),
            static_cast<std::int32_t>(i2),
            static_cast<std::int32_t>(i3),
            static_cast<std::int32_t>(not_regularizable_counts[orbit_index]),
        };
        const std::size_t orbit_type_offset =
            static_cast<std::size_t>(orbit_index) * static_cast<std::size_t>(dither_count);
        const std::size_t qgrid_offset = static_cast<std::size_t>(orbit_index) * qgrid_stride;
        if (!writer.write_array(orbit_header, 5) ||
            !writer.write_array(orbit_types + orbit_type_offset, static_cast<std::size_t>(dither_count)) ||
            !writer.write_array(qgrids + qgrid_offset, qgrid_stride)) {
            return false;
        }
    }
    return true;
}

bool write_losvd_histogram_file(
    const char* path,
    int orbit_count,
    int aperture_count,
    int velocity_bin_count,
    double velocity_bin_width,
    const int* begin_offsets,
    const int* end_offsets,
    const double* histograms
) noexcept {
    if (path == nullptr || orbit_count <= 0 || aperture_count <= 0 ||
        velocity_bin_count <= 0 || velocity_bin_width <= 0.0 ||
        begin_offsets == nullptr || end_offsets == nullptr || histograms == nullptr ||
        !std::isfinite(velocity_bin_width)) {
        return false;
    }

    int row_count = 0;
    if (!checked_mul_int(orbit_count, aperture_count, row_count)) {
        return false;
    }

    FortranRecordWriter writer(path);
    if (!writer.ok()) {
        return false;
    }

    const std::int32_t half_bin_count =
        static_cast<std::int32_t>(static_cast<double>(velocity_bin_count) / 2.0);
    if (!writer.write_losvd_setup_header(
            static_cast<std::int32_t>(aperture_count),
            half_bin_count,
            velocity_bin_width
        )) {
        return false;
    }

    for (int row = 0; row < row_count; ++row) {
        const int begin = begin_offsets[row];
        const int end = end_offsets[row];
        const std::int32_t sparse_range[2] = {
            static_cast<std::int32_t>(begin),
            static_cast<std::int32_t>(end),
        };
        if (!writer.write_array(sparse_range, 2)) {
            return false;
        }
        if (begin <= end) {
            const int begin_bin = begin + static_cast<int>(half_bin_count);
            const int end_bin = end + static_cast<int>(half_bin_count);
            if (begin_bin < 0 || end_bin < begin_bin || end_bin >= velocity_bin_count) {
                return false;
            }
            const std::size_t row_offset =
                static_cast<std::size_t>(row) * static_cast<std::size_t>(velocity_bin_count);
            const std::size_t count = static_cast<std::size_t>(end_bin - begin_bin + 1);
            if (!writer.write_array(histograms + row_offset + static_cast<std::size_t>(begin_bin), count)) {
                return false;
            }
        }
    }
    return true;
}

bool write_losvd_histogram_file_mixed(
    const char* path,
    int orbit_count,
    int row_count_per_orbit,
    int max_velocity_bin_count,
    const int* row_velocity_bin_counts,
    double header_velocity_bin_width,
    const int* begin_offsets,
    const int* end_offsets,
    const double* histograms
) noexcept {
    if (path == nullptr || orbit_count <= 0 || row_count_per_orbit <= 0 ||
        max_velocity_bin_count <= 0 || row_velocity_bin_counts == nullptr ||
        header_velocity_bin_width <= 0.0 || begin_offsets == nullptr ||
        end_offsets == nullptr || histograms == nullptr ||
        !std::isfinite(header_velocity_bin_width)) {
        return false;
    }
    for (int row = 0; row < row_count_per_orbit; ++row) {
        if (row_velocity_bin_counts[row] <= 0 ||
            row_velocity_bin_counts[row] > max_velocity_bin_count) {
            return false;
        }
    }

    int total_rows = 0;
    if (!checked_mul_int(orbit_count, row_count_per_orbit, total_rows)) {
        return false;
    }

    FortranRecordWriter writer(path);
    if (!writer.ok()) {
        return false;
    }

    const std::int32_t half_bin_count =
        static_cast<std::int32_t>(static_cast<double>(row_velocity_bin_counts[0]) / 2.0);
    if (!writer.write_losvd_setup_header(
            static_cast<std::int32_t>(row_count_per_orbit),
            half_bin_count,
            header_velocity_bin_width
        )) {
        return false;
    }

    for (int row = 0; row < total_rows; ++row) {
        const int row_in_orbit = row % row_count_per_orbit;
        const int velocity_bin_count = row_velocity_bin_counts[row_in_orbit];
        const int begin = begin_offsets[row];
        const int end = end_offsets[row];
        const std::int32_t sparse_range[2] = {
            static_cast<std::int32_t>(begin),
            static_cast<std::int32_t>(end),
        };
        if (!writer.write_array(sparse_range, 2)) {
            return false;
        }
        if (begin <= end) {
            const int begin_bin = begin + velocity_bin_count / 2;
            const int end_bin = end + velocity_bin_count / 2;
            if (begin_bin < 0 || end_bin < begin_bin || end_bin >= velocity_bin_count) {
                return false;
            }
            const std::size_t row_offset =
                static_cast<std::size_t>(row) * static_cast<std::size_t>(max_velocity_bin_count);
            const std::size_t count = static_cast<std::size_t>(end_bin - begin_bin + 1);
            if (!writer.write_array(histograms + row_offset + static_cast<std::size_t>(begin_bin), count)) {
                return false;
            }
        }
    }
    return true;
}

bool write_population_mass_file(
    const char* path,
    int orbit_count,
    int population_count,
    const int* aperture_counts,
    const double* masses
) noexcept {
    if (path == nullptr || orbit_count <= 0 || population_count <= 0 ||
        aperture_counts == nullptr || masses == nullptr) {
        return false;
    }

    int total_apertures = 0;
    for (int population = 0; population < population_count; ++population) {
        if (aperture_counts[population] <= 0) {
            return false;
        }
        if (total_apertures > std::numeric_limits<int>::max() - aperture_counts[population]) {
            return false;
        }
        total_apertures += aperture_counts[population];
    }

    FortranRecordWriter writer(path);
    if (!writer.ok()) {
        return false;
    }

    for (int orbit = 0; orbit < orbit_count; ++orbit) {
        const std::size_t orbit_offset =
            static_cast<std::size_t>(orbit) * static_cast<std::size_t>(total_apertures);
        int population_offset = 0;
        for (int population = 0; population < population_count; ++population) {
            const int aperture_count = aperture_counts[population];
            if (!writer.write_array(
                    masses + orbit_offset + static_cast<std::size_t>(population_offset),
                    static_cast<std::size_t>(aperture_count)
                )) {
                return false;
            }
            population_offset += aperture_count;
        }
    }
    return true;
}

bool write_orbit_class_file(
    const char* path,
    int orbit_count,
    int dither_count,
    const double* moments
) noexcept {
    if (path == nullptr || orbit_count <= 0 || dither_count <= 0 || moments == nullptr) {
        return false;
    }

    int total_columns = 0;
    if (!checked_mul_int(orbit_count, dither_count, total_columns)) {
        return false;
    }

    std::ofstream stream(std::string(path), std::ios::out | std::ios::trunc);
    if (!stream.good()) {
        return false;
    }

    stream << std::scientific << std::uppercase << std::setprecision(5);
    constexpr int values_per_line = 25;
    int line_values = 0;
    const std::size_t value_count = static_cast<std::size_t>(total_columns) * 5U;
    for (std::size_t index = 0; index < value_count; ++index) {
        stream << std::setw(13) << moments[index];
        ++line_values;
        if (line_values == values_per_line) {
            stream << '\n';
            line_values = 0;
        }
    }
    if (line_values != 0) {
        stream << '\n';
    }
    return stream.good();
}

}  // namespace dynamite::orblib_cpp
