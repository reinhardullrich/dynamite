#include "orbit_projection.hpp"

#include <cmath>

namespace dynamite::orblib_cpp {
namespace {

constexpr int kProjectionCount = 8;
constexpr int kOrbitTypeCount = 5;

constexpr int kPositionSignsNonRotating[kProjectionCount][3] = {
    {1, 1, 1},
    {-1, 1, 1},
    {-1, -1, 1},
    {1, -1, 1},
    {1, 1, -1},
    {-1, 1, -1},
    {-1, -1, -1},
    {1, -1, -1},
};

constexpr int kPositionSignsRotating[kProjectionCount][3] = {
    {1, 1, 1},
    {1, 1, 1},
    {-1, -1, 1},
    {-1, -1, 1},
    {1, 1, -1},
    {1, 1, -1},
    {-1, -1, -1},
    {-1, -1, -1},
};

constexpr int kVelocitySignsNonRotating[kOrbitTypeCount][kProjectionCount][3] = {
    {
        {1, 1, 1},
        {-1, 1, 1},
        {1, 1, -1},
        {-1, 1, -1},
        {-1, -1, 1},
        {1, -1, 1},
        {-1, -1, -1},
        {1, -1, -1},
    },
    {
        {1, 1, 1},
        {1, -1, -1},
        {1, 1, -1},
        {1, -1, 1},
        {-1, -1, 1},
        {-1, 1, -1},
        {-1, -1, -1},
        {-1, 1, 1},
    },
    {
        {1, 1, 1},
        {1, -1, -1},
        {-1, -1, 1},
        {-1, 1, -1},
        {1, 1, -1},
        {1, -1, 1},
        {-1, -1, -1},
        {-1, 1, 1},
    },
    {
        {1, 1, 1},
        {-1, 1, 1},
        {-1, -1, 1},
        {1, -1, 1},
        {1, 1, -1},
        {-1, 1, -1},
        {-1, -1, -1},
        {1, -1, -1},
    },
    {
        {1, 1, 1},
        {-1, 1, 1},
        {-1, -1, 1},
        {1, -1, 1},
        {1, 1, -1},
        {-1, 1, -1},
        {-1, -1, -1},
        {1, -1, -1},
    },
};

constexpr int kVelocitySignsRotating[kOrbitTypeCount][kProjectionCount][3] = {
    {
        {1, 1, 1},
        {1, 1, 1},
        {-1, -1, 1},
        {-1, -1, 1},
        {1, 1, -1},
        {1, 1, -1},
        {-1, -1, -1},
        {-1, -1, -1},
    },
    {
        {1, 1, 1},
        {1, 1, 1},
        {1, 1, -1},
        {1, 1, -1},
        {-1, -1, 1},
        {-1, -1, 1},
        {-1, -1, -1},
        {-1, -1, -1},
    },
    {
        {1, 1, 1},
        {1, 1, 1},
        {-1, -1, 1},
        {-1, -1, 1},
        {1, 1, -1},
        {1, 1, -1},
        {-1, -1, -1},
        {-1, -1, -1},
    },
    {
        {1, 1, 1},
        {1, 1, 1},
        {-1, -1, 1},
        {-1, -1, 1},
        {1, 1, -1},
        {1, 1, -1},
        {-1, -1, -1},
        {-1, -1, -1},
    },
    {
        {1, 1, 1},
        {1, 1, 1},
        {-1, -1, 1},
        {-1, -1, 1},
        {1, 1, -1},
        {1, 1, -1},
        {-1, -1, -1},
        {-1, -1, -1},
    },
};

}  // namespace

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
) noexcept {
    if (orbit_type < 1 || orbit_type > kOrbitTypeCount || projection_number < 1 ||
        projection_number > kProjectionCount || sample_count < 0 || x == nullptr ||
        y == nullptr || z == nullptr || vx == nullptr || vy == nullptr || vz == nullptr ||
        projected_x == nullptr || projected_y == nullptr || los_velocity == nullptr) {
        return false;
    }

    const int projection_index = projection_number - 1;
    const int orbit_type_index = orbit_type - 1;
    const bool rotating_frame = omega != 0.0;
    const int* psgn = rotating_frame ? kPositionSignsRotating[projection_index]
                                     : kPositionSignsNonRotating[projection_index];
    const int* vsgn = rotating_frame ? kVelocitySignsRotating[orbit_type_index][projection_index]
                                     : kVelocitySignsNonRotating[orbit_type_index][projection_index];

    const double sin_theta = std::sin(theta);
    const double cos_theta = std::cos(theta);
    const double sin_phi = std::sin(phi);
    const double cos_phi = std::cos(phi);

    const double proj_x_x_scale = -sin_phi * psgn[0];
    const double proj_x_y_scale = cos_phi * psgn[1];
    const double proj_y_x_scale = -cos_theta * cos_phi * psgn[0];
    const double proj_y_y_scale = -cos_theta * sin_phi * psgn[1];
    const double proj_y_z_scale = sin_theta * psgn[2];
    const double los_vx_scale = sin_theta * cos_phi * vsgn[0];
    const double los_vy_scale = sin_theta * sin_phi * vsgn[1];
    const double los_vz_scale = cos_theta * vsgn[2];

    for (int i = 0; i < sample_count; ++i) {
        projected_x[i] = proj_x_x_scale * x[i] + proj_x_y_scale * y[i];
        projected_y[i] =
            proj_y_x_scale * x[i] + proj_y_y_scale * y[i] + proj_y_z_scale * z[i];
        los_velocity[i] = los_vx_scale * vx[i] + los_vy_scale * vy[i] + los_vz_scale * vz[i];
    }
    return true;
}

}  // namespace dynamite::orblib_cpp
