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

bool collapse_losvd_binning(
    int source_pixel_count,
    int velocity_bin_count,
    int target_pixel_count,
    const int* bin_order,
    const double* source_histogram,
    double* target_histogram
) noexcept {
    if (source_pixel_count < 1 || velocity_bin_count < 1 || target_pixel_count < 1 ||
        target_pixel_count > source_pixel_count || bin_order == nullptr ||
        source_histogram == nullptr || target_histogram == nullptr) {
        return false;
    }

    for (int i = 0; i < source_pixel_count; ++i) {
        if (bin_order[i] < 0 || bin_order[i] > target_pixel_count) {
            return false;
        }
    }

    const std::size_t target_size =
        static_cast<std::size_t>(target_pixel_count) * static_cast<std::size_t>(velocity_bin_count);
    for (std::size_t i = 0; i < target_size; ++i) {
        target_histogram[i] = 0.0;
    }

    for (int pixel = 0; pixel < source_pixel_count; ++pixel) {
        const int target = bin_order[pixel];
        if (target == 0) {
            continue;
        }
        for (int velocity_bin = 0; velocity_bin < velocity_bin_count; ++velocity_bin) {
            const std::size_t source_index =
                static_cast<std::size_t>(pixel) * static_cast<std::size_t>(velocity_bin_count) +
                static_cast<std::size_t>(velocity_bin);
            const std::size_t target_index =
                static_cast<std::size_t>(target - 1) * static_cast<std::size_t>(velocity_bin_count) +
                static_cast<std::size_t>(velocity_bin);
            target_histogram[target_index] += source_histogram[source_index];
        }
    }
    return true;
}

bool normalize_losvd_histogram(
    int pixel_count,
    int velocity_bin_count,
    double stored_count,
    double* histogram
) noexcept {
    if (pixel_count < 1 || velocity_bin_count < 1 || histogram == nullptr ||
        !std::isfinite(stored_count)) {
        return false;
    }

    const double factor = stored_count > 0.0 ? 1.0 / stored_count : 0.0;
    const std::size_t size =
        static_cast<std::size_t>(pixel_count) * static_cast<std::size_t>(velocity_bin_count);
    for (std::size_t i = 0; i < size; ++i) {
        histogram[i] *= factor;
    }
    return true;
}

bool compute_sparse_losvd_ranges(
    int pixel_count,
    int velocity_bin_count,
    const double* histogram,
    int* begin_offsets,
    int* end_offsets
) noexcept {
    if (pixel_count < 1 || velocity_bin_count < 1 || histogram == nullptr ||
        begin_offsets == nullptr || end_offsets == nullptr) {
        return false;
    }

    const int center_bin = static_cast<int>(static_cast<double>(velocity_bin_count) / 2.0 + 1.0);
    for (int pixel = 0; pixel < pixel_count; ++pixel) {
        int begin = 2 * velocity_bin_count;
        int end = -2 * velocity_bin_count;
        for (int velocity_bin = 0; velocity_bin < velocity_bin_count; ++velocity_bin) {
            const std::size_t index =
                static_cast<std::size_t>(pixel) * static_cast<std::size_t>(velocity_bin_count) +
                static_cast<std::size_t>(velocity_bin);
            if (histogram[index] > 0.0) {
                const int fortran_bin = velocity_bin + 1;
                if (fortran_bin < begin) {
                    begin = fortran_bin;
                }
                if (fortran_bin > end) {
                    end = fortran_bin;
                }
            }
        }
        begin_offsets[pixel] = begin - center_bin;
        end_offsets[pixel] = end - center_bin;
    }
    return true;
}

}  // namespace dynamite::orblib_cpp
