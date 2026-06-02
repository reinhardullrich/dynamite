#pragma once

namespace dynamite::orblib_cpp {

bool setup_qgrid_boundaries(
    int radius_bin_count,
    int theta_bin_count,
    int phi_bin_count,
    double rlogmin,
    double rlogmax,
    int sigma_count,
    const double* sigobs_km,
    double* radius_boundaries,
    double* theta_boundaries,
    double* phi_boundaries
) noexcept;

bool accumulate_qgrid_samples(
    int orbit_type,
    double omega,
    int radius_bin_count,
    int theta_bin_count,
    int phi_bin_count,
    const double* radius_boundaries,
    const double* theta_boundaries,
    const double* phi_boundaries,
    int sample_count,
    const double* x,
    const double* y,
    const double* z,
    const double* vx,
    const double* vy,
    const double* vz,
    double* qgrid
) noexcept;

bool normalize_qgrid(
    int radius_bin_count,
    int theta_bin_count,
    int phi_bin_count,
    double* qgrid
) noexcept;

}  // namespace dynamite::orblib_cpp
