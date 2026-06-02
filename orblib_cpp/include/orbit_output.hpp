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

}  // namespace dynamite::orblib_cpp
