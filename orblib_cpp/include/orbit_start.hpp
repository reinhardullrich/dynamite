#pragma once

#include "potential.hpp"

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
) noexcept;

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
) noexcept;

}  // namespace dynamite::orblib_cpp
