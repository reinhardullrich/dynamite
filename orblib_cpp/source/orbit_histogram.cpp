#include "orbit_histogram.hpp"

#include <cmath>
#include <cstddef>

namespace dynamite::orblib_cpp {

bool map_losvd_velocity_bins(
    double histogram_width,
    double histogram_center,
    int velocity_bin_count,
    int sample_count,
    const double* los_velocity,
    int* velocity_bins
) noexcept {
    if (histogram_width <= 0.0 || velocity_bin_count < 1 || sample_count < 0 ||
        los_velocity == nullptr || velocity_bins == nullptr ||
        !std::isfinite(histogram_width) || !std::isfinite(histogram_center)) {
        return false;
    }

    const double begin = histogram_center - 0.5 * histogram_width;
    const double end = histogram_center + 0.5 * histogram_width;
    const double bin_width = histogram_width / static_cast<double>(velocity_bin_count);
    if (!(bin_width > 0.0) || !std::isfinite(begin) || !std::isfinite(end) ||
        !std::isfinite(bin_width)) {
        return false;
    }

    for (int i = 0; i < sample_count; ++i) {
        const double velocity = los_velocity[i];
        int bin = 1;
        if (velocity > begin) {
            if (velocity < end) {
                bin = static_cast<int>((velocity - begin) / bin_width) + 1;
            } else {
                bin = velocity_bin_count;
            }
        }
        velocity_bins[i] = bin;
    }
    return true;
}

bool accumulate_losvd_histogram(
    int aperture_pixel_count,
    int velocity_bin_count,
    int sample_count,
    const int* aperture_pixels,
    const int* velocity_bins,
    int total_sample_count,
    double* histogram,
    double* stored_count
) noexcept {
    if (aperture_pixel_count < 1 || velocity_bin_count < 1 || sample_count < 0 ||
        total_sample_count < 0 || aperture_pixels == nullptr || velocity_bins == nullptr ||
        histogram == nullptr || stored_count == nullptr) {
        return false;
    }

    for (int i = 0; i < sample_count; ++i) {
        const int pixel = aperture_pixels[i];
        const int velocity_bin = velocity_bins[i];
        if (pixel < 0 || pixel > aperture_pixel_count ||
            velocity_bin < 1 || velocity_bin > velocity_bin_count) {
            return false;
        }
    }

    *stored_count += static_cast<double>(total_sample_count);
    for (int i = 0; i < sample_count; ++i) {
        const int pixel = aperture_pixels[i];
        if (pixel != 0) {
            const int velocity_bin = velocity_bins[i];
            const std::size_t index =
                static_cast<std::size_t>(pixel - 1) * static_cast<std::size_t>(velocity_bin_count) +
                static_cast<std::size_t>(velocity_bin - 1);
            histogram[index] += 1.0;
        }
    }
    return true;
}

}  // namespace dynamite::orblib_cpp
