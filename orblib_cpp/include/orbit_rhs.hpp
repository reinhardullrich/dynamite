#pragma once

#include "interpolated_potential.hpp"

namespace dynamite::orblib_cpp {

bool evaluate_orbit_rhs(
    InterpolatedPotential& potential,
    double omega,
    const double state[6],
    double derivative[6]
) noexcept;

}  // namespace dynamite::orblib_cpp
