#include "orbit_aperture.hpp"

#include <cmath>

namespace dynamite::orblib_cpp {
namespace {

constexpr double kPi = 3.141592653589793238462643383279502884;

bool finite_box_inputs(
    double begin_x,
    double begin_y,
    double size_x,
    double size_y,
    double rotation_degrees,
    double psi_radians,
    double coordinate_scale
) noexcept {
    return std::isfinite(begin_x) && std::isfinite(begin_y) && std::isfinite(size_x) &&
           std::isfinite(size_y) && std::isfinite(rotation_degrees) &&
           std::isfinite(psi_radians) && std::isfinite(coordinate_scale);
}

}  // namespace

bool find_boxed_aperture_pixels(
    double begin_x,
    double begin_y,
    double size_x,
    double size_y,
    double rotation_degrees,
    int bins_x,
    int bins_y,
    double psi_radians,
    double coordinate_scale,
    int sample_count,
    const double* projected_x,
    const double* projected_y,
    int* pixels
) noexcept {
    if (bins_x <= 0 || bins_y <= 0 || size_x <= 0.0 || size_y <= 0.0 ||
        coordinate_scale <= 0.0 || sample_count < 0 || projected_x == nullptr ||
        projected_y == nullptr || pixels == nullptr ||
        !finite_box_inputs(
            begin_x,
            begin_y,
            size_x,
            size_y,
            rotation_degrees,
            psi_radians,
            coordinate_scale
        )) {
        return false;
    }

    const double scaled_begin_x = begin_x * coordinate_scale;
    const double scaled_begin_y = begin_y * coordinate_scale;
    const double scaled_size_x = size_x * coordinate_scale;
    const double scaled_size_y = size_y * coordinate_scale;
    if (!(scaled_size_x > 0.0) || !(scaled_size_y > 0.0) ||
        !std::isfinite(scaled_begin_x) || !std::isfinite(scaled_begin_y) ||
        !std::isfinite(scaled_size_x) || !std::isfinite(scaled_size_y)) {
        return false;
    }

    const double rotation_radians = rotation_degrees * (kPi / 180.0);
    const double angle = -rotation_radians + 0.5 * kPi - psi_radians;
    const double r1 = std::cos(angle);
    const double r2 = std::sin(angle);
    const double idx = static_cast<double>(bins_x) / scaled_size_x;
    const double idy = static_cast<double>(bins_y) / scaled_size_y;

    for (int i = 0; i < sample_count; ++i) {
        const double t = projected_x[i];
        const double q = projected_y[i];
        const double x = t * r1 - q * r2 - scaled_begin_x;
        int pixel = 0;
        if (x > 0.0 && x < scaled_size_x) {
            const double y = t * r2 + q * r1 - scaled_begin_y;
            if (y > 0.0 && y < scaled_size_y) {
                pixel = static_cast<int>(x * idx) + static_cast<int>(y * idy) * bins_x + 1;
            }
        }
        pixels[i] = pixel;
    }
    return true;
}

}  // namespace dynamite::orblib_cpp
