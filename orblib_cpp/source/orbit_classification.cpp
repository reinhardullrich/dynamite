#include "orbit_classification.hpp"

#include <algorithm>
#include <cmath>

namespace dynamite::orblib_cpp {
namespace {

double square(double value) noexcept {
    return value * value;
}

}  // namespace

bool classify_orbit_samples(
    int sample_count,
    const double* x,
    const double* y,
    const double* z,
    const double* vx,
    const double* vy,
    const double* vz,
    OrbitClassificationResult& result
) noexcept {
    result = OrbitClassificationResult{};
    if (sample_count <= 0 || x == nullptr || y == nullptr || z == nullptr || vx == nullptr ||
        vy == nullptr || vz == nullptr) {
        return false;
    }

    double lx_min = 0.0;
    double lx_max = 0.0;
    double ly_min = 0.0;
    double ly_max = 0.0;
    double lz_min = 0.0;
    double lz_max = 0.0;
    double lx_sum = 0.0;
    double ly_sum = 0.0;
    double lz_sum = 0.0;
    double radius_sum = 0.0;
    double velocity_second_sum = 0.0;
    double vr_sum = 0.0;
    double vt_sum = 0.0;
    double vz_sum = 0.0;

    for (int i = 0; i < sample_count; ++i) {
        const double lx = y[i] * vz[i] - z[i] * vy[i];
        const double ly = z[i] * vx[i] - x[i] * vz[i];
        const double lz = x[i] * vy[i] - y[i] * vx[i];
        if (i == 0) {
            lx_min = lx_max = lx;
            ly_min = ly_max = ly;
            lz_min = lz_max = lz;
        } else {
            lx_min = std::min(lx_min, lx);
            lx_max = std::max(lx_max, lx);
            ly_min = std::min(ly_min, ly);
            ly_max = std::max(ly_max, ly);
            lz_min = std::min(lz_min, lz);
            lz_max = std::max(lz_max, lz);
        }
        lx_sum += lx;
        ly_sum += ly;
        lz_sum += lz;
        radius_sum += std::sqrt(x[i] * x[i] + y[i] * y[i] + z[i] * z[i]);
        velocity_second_sum +=
            vx[i] * vx[i] + vy[i] * vy[i] + vz[i] * vz[i] +
            2.0 * (vx[i] * vy[i] + vy[i] * vz[i] + vz[i] * vx[i]);

        const double cylindrical_radius = std::sqrt(x[i] * x[i] + y[i] * y[i]);
        if (cylindrical_radius <= 0.0) {
            return false;
        }
        vr_sum += (x[i] * vx[i] + y[i] * vy[i]) / cylindrical_radius;
        vt_sum += (x[i] * vy[i] + y[i] * vx[i]) / cylindrical_radius;
        vz_sum += vz[i];
    }

    const double lxc = lx_max * lx_min;
    const double lyc = ly_max * ly_min;
    const double lzc = lz_max * lz_min;
    constexpr double nul = 0.0;

    result.type = 5;
    if (lxc > nul && lyc < nul && lzc < nul) {
        result.type = 1;
    }
    if (lxc < nul && lyc > nul && lzc < nul) {
        result.type = 2;
    }
    if (lxc < nul && lyc < nul && lzc > nul) {
        result.type = 3;
    }
    if (lxc < nul && lyc < nul && lzc < nul) {
        result.type = 4;
    }

    const double n = static_cast<double>(sample_count);
    result.moments[0] = lx_sum / n;
    result.moments[1] = ly_sum / n;
    result.moments[2] = lz_sum / n;
    result.moments[3] = radius_sum / n;
    result.moments[4] = velocity_second_sum / n;

    const double mean_vr = vr_sum / n;
    const double mean_vt = vt_sum / n;
    const double mean_vz = vz_sum / n;
    double sd_vr_sum = 0.0;
    double sd_vt_sum = 0.0;
    double sd_vz_sum = 0.0;
    for (int i = 0; i < sample_count; ++i) {
        const double cylindrical_radius = std::sqrt(x[i] * x[i] + y[i] * y[i]);
        const double vr = (x[i] * vx[i] + y[i] * vy[i]) / cylindrical_radius;
        const double vt = (x[i] * vy[i] + y[i] * vx[i]) / cylindrical_radius;
        const double v_z = vz[i];
        sd_vr_sum += square(vr - mean_vr);
        sd_vt_sum += square(vt - mean_vt);
        sd_vz_sum += square(v_z - mean_vz);
    }
    result.moments2[0] = std::sqrt(sd_vr_sum / n);
    result.moments2[1] = std::sqrt(sd_vt_sum / n);
    result.moments2[2] = std::sqrt(sd_vz_sum / n);
    return true;
}

}  // namespace dynamite::orblib_cpp
