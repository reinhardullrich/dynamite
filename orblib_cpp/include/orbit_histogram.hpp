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

bool collapse_losvd_binning(
    int source_pixel_count,
    int velocity_bin_count,
    int target_pixel_count,
    const int* bin_order,
    const double* source_histogram,
    double* target_histogram
) noexcept;

bool normalize_losvd_histogram(
    int pixel_count,
    int velocity_bin_count,
    double stored_count,
    double* histogram
) noexcept;

bool compute_sparse_losvd_ranges(
    int pixel_count,
    int velocity_bin_count,
    const double* histogram,
    int* begin_offsets,
    int* end_offsets
) noexcept;

}  // namespace dynamite::orblib_cpp
