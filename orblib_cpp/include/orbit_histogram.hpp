#pragma once

namespace dynamite::orblib_cpp {

bool map_losvd_velocity_bins(
    double histogram_width,
    double histogram_center,
    int velocity_bin_count,
    int sample_count,
    const double* los_velocity,
    int* velocity_bins
) noexcept;

bool accumulate_losvd_histogram(
    int aperture_pixel_count,
    int velocity_bin_count,
    int sample_count,
    const int* aperture_pixels,
    const int* velocity_bins,
    int total_sample_count,
    double* histogram,
    double* stored_count
) noexcept;

}  // namespace dynamite::orblib_cpp
