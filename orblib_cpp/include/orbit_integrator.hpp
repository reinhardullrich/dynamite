#pragma once

#include "dop853.hpp"
#include "interpolated_potential.hpp"

namespace dynamite::orblib_cpp {

struct OrbitIntegrationResult {
    Dop853Result solver;
    bool rhs_failed = false;
    double final_time = 0.0;
};

OrbitIntegrationResult integrate_orbit_final_state(
    InterpolatedPotential& potential,
    double omega,
    double t_start,
    const double initial_state[6],
    double t_end,
    double rtol,
    double atol,
    int max_steps,
    double final_state[6]
) noexcept;

}  // namespace dynamite::orblib_cpp
