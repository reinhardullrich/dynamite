#pragma once

namespace dynamite::orblib_cpp {

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
) noexcept;

}  // namespace dynamite::orblib_cpp
