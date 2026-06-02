#include "orbit_qgrid.hpp"

#include <algorithm>
#include <cmath>
#include <cstddef>

namespace dynamite::orblib_cpp {
namespace {

constexpr int kChannelCount = 16;
constexpr int kProjectionCount = 8;
constexpr int kOrbitTypeCount = 5;
constexpr double kPi = 3.141592653589793238462643383279502884;

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

std::size_t qgrid_index(
    int channel,
    int phi_bin,
    int theta_bin,
    int radius_bin,
    int phi_bin_count,
    int theta_bin_count
) noexcept {
    return static_cast<std::size_t>(channel) +
           static_cast<std::size_t>(kChannelCount) *
               (static_cast<std::size_t>(phi_bin) +
                static_cast<std::size_t>(phi_bin_count) *
                    (static_cast<std::size_t>(theta_bin) +
                     static_cast<std::size_t>(theta_bin_count) *
                         static_cast<std::size_t>(radius_bin)));
}

int find_squared_boundary_bin(const double* boundaries, int bin_count, double value) noexcept {
    for (int bin = 0; bin < bin_count - 1; ++bin) {
        const double boundary = boundaries[bin + 1];
        if (value <= boundary * boundary) {
            return bin;
        }
    }
    return bin_count - 1;
}

int find_tan_squared_boundary_bin(const double* boundaries, int bin_count, double value) noexcept {
    for (int bin = 0; bin < bin_count - 1; ++bin) {
        const double tangent = std::tan(boundaries[bin + 1]);
        if (value <= tangent * tangent) {
            return bin;
        }
    }
    return bin_count - 1;
}

int find_tan_boundary_bin(const double* boundaries, int bin_count, double value) noexcept {
    for (int bin = 0; bin < bin_count - 1; ++bin) {
        if (value <= std::tan(boundaries[bin + 1])) {
            return bin;
        }
    }
    return bin_count - 1;
}

int qgrid_store_type_channel(int orbit_type) noexcept {
    if (orbit_type == 1) {
        return 13;
    }
    if (orbit_type == 3) {
        return 14;
    }
    return 15;
}

}  // namespace

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
) noexcept {
    if (radius_bin_count < 2 || theta_bin_count < 2 || phi_bin_count < 2 ||
        sigma_count < 1 || sigobs_km == nullptr || radius_boundaries == nullptr ||
        theta_boundaries == nullptr || phi_boundaries == nullptr ||
        !std::isfinite(rlogmin) || !std::isfinite(rlogmax)) {
        return false;
    }

    double max_sigma = sigobs_km[0];
    for (int i = 0; i < sigma_count; ++i) {
        if (!std::isfinite(sigobs_km[i])) {
            return false;
        }
        if (sigobs_km[i] > max_sigma) {
            max_sigma = sigobs_km[i];
        }
    }

    radius_boundaries[0] = 0.0;
    for (int i = 1; i < radius_bin_count; ++i) {
        const double fraction = static_cast<double>(i) / static_cast<double>(radius_bin_count);
        radius_boundaries[i] =
            std::pow(10.0, rlogmin + (rlogmax - rlogmin + std::log10(0.5)) * fraction);
    }
    radius_boundaries[radius_bin_count] =
        std::max(std::pow(10.0, rlogmax) * 100.0, max_sigma * 10.0);

    theta_boundaries[0] = 0.0;
    for (int i = 1; i < theta_bin_count; ++i) {
        theta_boundaries[i] =
            0.5 * kPi * static_cast<double>(i) / static_cast<double>(theta_bin_count);
    }
    theta_boundaries[theta_bin_count] = 0.5 * kPi;

    phi_boundaries[0] = 0.0;
    for (int i = 1; i < phi_bin_count; ++i) {
        phi_boundaries[i] =
            0.5 * kPi * static_cast<double>(i) / static_cast<double>(phi_bin_count);
    }
    phi_boundaries[phi_bin_count] = 0.5 * kPi;
    return true;
}

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
) noexcept {
    if (orbit_type < 1 || orbit_type > kOrbitTypeCount || radius_bin_count < 2 ||
        theta_bin_count < 2 || phi_bin_count < 2 || sample_count < 0 ||
        radius_boundaries == nullptr || theta_boundaries == nullptr ||
        phi_boundaries == nullptr || x == nullptr || y == nullptr || z == nullptr ||
        vx == nullptr || vy == nullptr || vz == nullptr || qgrid == nullptr) {
        return false;
    }

    const bool rotating_frame = omega != 0.0;
    const int orbit_type_index = orbit_type - 1;
    const int store_type_channel = qgrid_store_type_channel(orbit_type);
    for (int sample = 0; sample < sample_count; ++sample) {
        for (int projection = 0; projection < kProjectionCount; ++projection) {
            const int* psgn = rotating_frame ? kPositionSignsRotating[projection]
                                             : kPositionSignsNonRotating[projection];
            const int* vsgn = rotating_frame
                                  ? kVelocitySignsRotating[orbit_type_index][projection]
                                  : kVelocitySignsNonRotating[orbit_type_index][projection];

            const double folded_x = x[sample] * static_cast<double>(psgn[0]);
            const double folded_y = y[sample] * static_cast<double>(psgn[1]);
            const double folded_z = z[sample] * static_cast<double>(psgn[2]);
            if (folded_x > 0.0 && folded_y >= 0.0 && folded_z > 0.0) {
                const double folded_vx = vx[sample] * static_cast<double>(vsgn[0]);
                const double folded_vy = vy[sample] * static_cast<double>(vsgn[1]);
                const double folded_vz = vz[sample] * static_cast<double>(vsgn[2]);
                const double radius_squared =
                    folded_x * folded_x + folded_y * folded_y + folded_z * folded_z;
                const double tan_theta_squared =
                    (folded_x * folded_x + folded_y * folded_y) / (folded_z * folded_z);
                const double tan_phi = folded_y / folded_x;

                const int radius_bin =
                    find_squared_boundary_bin(radius_boundaries, radius_bin_count, radius_squared);
                const int theta_bin =
                    find_tan_squared_boundary_bin(theta_boundaries, theta_bin_count, tan_theta_squared);
                const int phi_bin = find_tan_boundary_bin(phi_boundaries, phi_bin_count, tan_phi);

                double values[13] = {
                    1.0,
                    folded_x,
                    folded_y,
                    folded_z,
                    folded_vx,
                    folded_vy,
                    folded_vz,
                    folded_vx * folded_vx,
                    folded_vy * folded_vy,
                    folded_vz * folded_vz,
                    folded_vx * folded_vy,
                    folded_vy * folded_vz,
                    folded_vz * folded_vx,
                };
                for (int channel = 0; channel < 13; ++channel) {
                    qgrid[qgrid_index(
                        channel,
                        phi_bin,
                        theta_bin,
                        radius_bin,
                        phi_bin_count,
                        theta_bin_count
                    )] += values[channel];
                }
                qgrid[qgrid_index(
                    store_type_channel,
                    phi_bin,
                    theta_bin,
                    radius_bin,
                    phi_bin_count,
                    theta_bin_count
                )] += 1.0;
            }
        }
    }
    return true;
}

bool normalize_qgrid(
    int radius_bin_count,
    int theta_bin_count,
    int phi_bin_count,
    double* qgrid
) noexcept {
    if (radius_bin_count < 1 || theta_bin_count < 1 || phi_bin_count < 1 || qgrid == nullptr) {
        return false;
    }

    double total_count = 0.0;
    for (int radius_bin = 0; radius_bin < radius_bin_count; ++radius_bin) {
        for (int theta_bin = 0; theta_bin < theta_bin_count; ++theta_bin) {
            for (int phi_bin = 0; phi_bin < phi_bin_count; ++phi_bin) {
                total_count += qgrid[qgrid_index(
                    0,
                    phi_bin,
                    theta_bin,
                    radius_bin,
                    phi_bin_count,
                    theta_bin_count
                )];
            }
        }
    }

    for (int radius_bin = 0; radius_bin < radius_bin_count; ++radius_bin) {
        for (int theta_bin = 0; theta_bin < theta_bin_count; ++theta_bin) {
            for (int phi_bin = 0; phi_bin < phi_bin_count; ++phi_bin) {
                const std::size_t count_index = qgrid_index(
                    0,
                    phi_bin,
                    theta_bin,
                    radius_bin,
                    phi_bin_count,
                    theta_bin_count
                );
                const double count = qgrid[count_index];
                if (count != 0.0) {
                    for (int channel = 1; channel < 13; ++channel) {
                        qgrid[qgrid_index(
                            channel,
                            phi_bin,
                            theta_bin,
                            radius_bin,
                            phi_bin_count,
                            theta_bin_count
                        )] /= count;
                    }
                    if (total_count != 0.0) {
                        qgrid[count_index] /= total_count;
                        for (int channel = 13; channel < 16; ++channel) {
                            qgrid[qgrid_index(
                                channel,
                                phi_bin,
                                theta_bin,
                                radius_bin,
                                phi_bin_count,
                                theta_bin_count
                            )] /= total_count;
                        }
                    }
                }
            }
        }
    }
    return true;
}

}  // namespace dynamite::orblib_cpp
