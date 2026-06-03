#pragma once

namespace dynamite::orblib_cpp {

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
) noexcept;

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
) noexcept;

bool write_losvd_histogram_file(
    const char* path,
    int orbit_count,
    int aperture_count,
    int velocity_bin_count,
    double velocity_bin_width,
    const int* begin_offsets,
    const int* end_offsets,
    const double* histograms
) noexcept;

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
) noexcept;

bool write_population_mass_file(
    const char* path,
    int orbit_count,
    int population_count,
    const int* aperture_counts,
    const double* masses
) noexcept;

bool write_orbit_class_file(
    const char* path,
    int orbit_count,
    int dither_count,
    const double* moments
) noexcept;

}  // namespace dynamite::orblib_cpp
