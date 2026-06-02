#pragma once

namespace dynamite::orblib_cpp {

struct OrbitClassificationResult {
    int type = 5;
    double moments[5] = {};
    double moments2[3] = {};
};

bool classify_orbit_samples(
    int sample_count,
    const double* x,
    const double* y,
    const double* z,
    const double* vx,
    const double* vy,
    const double* vz,
    OrbitClassificationResult& result
) noexcept;

}  // namespace dynamite::orblib_cpp
