#pragma once

namespace dynamite::orblib_cpp {

bool apply_psf_to_projected_samples(
    int gaussian_count,
    const double* weights,
    const double* sigmas,
    double sigma_scale,
    int sample_count,
    const double* projected_x,
    const double* projected_y,
    int seed,
    double* convolved_x,
    double* convolved_y
) noexcept;

}  // namespace dynamite::orblib_cpp
