#pragma once

namespace dynamite::orblib_cpp {

bool project_orbit_samples(
    int orbit_type,
    int projection_number,
    double omega,
    double theta,
    double phi,
    int sample_count,
    const double* x,
    const double* y,
    const double* z,
    const double* vx,
    const double* vy,
    const double* vz,
    double* projected_x,
    double* projected_y,
    double* los_velocity
) noexcept;

}  // namespace dynamite::orblib_cpp
