#include "orbit_start.hpp"

#include <cmath>

namespace dynamite::orblib_cpp {

bool calculate_orbit_start_state(
    const TriaxialMgeSetup& mge,
    const DarkHaloSetup& halo,
    double black_hole_mass,
    double black_hole_softening_km,
    double radius,
    double theta,
    double energy,
    double* state
) noexcept {
    if (state == nullptr || radius < 0.0 || !std::isfinite(radius) ||
        !std::isfinite(theta) || !std::isfinite(energy)) {
        return false;
    }

    state[0] = radius * std::sin(theta);
    state[1] = 0.0;
    state[2] = radius * std::cos(theta);
    state[3] = 0.0;
    state[4] = 0.0;
    state[5] = 0.0;

    double potential = 0.0;
    double accel_x = 0.0;
    double accel_y = 0.0;
    double accel_z = 0.0;
    if (!evaluate_potential_stack(
            mge,
            halo,
            black_hole_mass,
            black_hole_softening_km,
            state[0],
            state[1],
            state[2],
            potential,
            accel_x,
            accel_y,
            accel_z
        )) {
        return false;
    }

    double vy = 2.0 * (potential - energy);
    if (vy >= 1.0e-300) {
        vy = std::sqrt(vy);
    }
    if (vy < 0.0 || std::isnan(vy)) {
        vy = std::sqrt(2.0 * potential * 1.0e-12);
    }
    if (!std::isfinite(vy)) {
        return false;
    }
    state[4] = vy;
    return true;
}

bool find_equivalent_radius(
    const TriaxialMgeSetup& mge,
    const DarkHaloSetup& halo,
    double black_hole_mass,
    double black_hole_softening_km,
    double request_radius,
    double energy,
    double theta,
    double phi,
    double& radius,
    int& iterations
) noexcept {
    radius = 0.0;
    iterations = 0;
    if (request_radius <= 0.0 || energy == 0.0 || !std::isfinite(request_radius) ||
        !std::isfinite(energy) || !std::isfinite(theta) || !std::isfinite(phi)) {
        return false;
    }

    const double sin_theta = std::sin(theta);
    const double cos_theta = std::cos(theta);
    const double sin_phi = std::sin(phi);
    const double cos_phi = std::cos(phi);
    double min_radius = 0.01 * request_radius;
    double max_radius = 1.1 * request_radius;

    constexpr int max_iterations = 60000;
    for (int i = 0; i <= max_iterations; ++i) {
        radius = 0.5 * (min_radius + max_radius);
        double potential = 0.0;
        double accel_x = 0.0;
        double accel_y = 0.0;
        double accel_z = 0.0;
        if (!evaluate_potential_stack(
                mge,
                halo,
                black_hole_mass,
                black_hole_softening_km,
                radius * sin_theta * cos_phi,
                radius * sin_theta * sin_phi,
                radius * cos_theta,
                potential,
                accel_x,
                accel_y,
                accel_z
            )) {
            return false;
        }

        if (std::abs((energy - potential) / energy) < 1.0e-7) {
            iterations = i;
            return true;
        }
        if (potential > energy) {
            min_radius = radius;
        } else {
            max_radius = radius;
        }
    }
    iterations = max_iterations;
    return false;
}

}  // namespace dynamite::orblib_cpp
