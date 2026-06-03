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

OrbitIntegrationResult integrate_orbit_samples(
    InterpolatedPotential& potential,
    double omega,
    double t_start,
    const double initial_state[6],
    double t_end,
    double rtol,
    double atol,
    int max_steps,
    const double* sample_times,
    int sample_count,
    double final_state[6],
    double* sample_states,
    int& samples_written,
    double initial_step = 0.0
) noexcept;

}  // namespace dynamite::orblib_cpp
