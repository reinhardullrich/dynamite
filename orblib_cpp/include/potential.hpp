#pragma once

#include "triaxial_mge.hpp"

#include <array>

namespace dynamite::orblib_cpp {

struct DarkHaloSetup {
    int profile_type = 0;
    double rhoc = 0.0;
    double rc = 0.0;
    std::array<double, 4> params{};
};

bool setup_dark_halo(
    int profile_type,
    int n_params,
    const double* params,
    double total_stellar_mass,
    DarkHaloSetup& halo
) noexcept;

bool evaluate_dark_halo(
    const DarkHaloSetup& halo,
    double x,
    double y,
    double z,
    double& potential,
    double& accel_x,
    double& accel_y,
    double& accel_z
) noexcept;

bool evaluate_dark_halo_acceleration(
    const DarkHaloSetup& halo,
    double x,
    double y,
    double z,
    double& accel_x,
    double& accel_y,
    double& accel_z
) noexcept;

bool evaluate_potential_stack(
    const TriaxialMgeSetup& mge,
    const DarkHaloSetup& halo,
    double black_hole_mass,
    double black_hole_softening_km,
    double x,
    double y,
    double z,
    double& potential,
    double& accel_x,
    double& accel_y,
    double& accel_z
) noexcept;

bool evaluate_potential_stack_acceleration(
    const TriaxialMgeSetup& mge,
    const DarkHaloSetup& halo,
    double black_hole_mass,
    double black_hole_softening_km,
    double x,
    double y,
    double z,
    double& accel_x,
    double& accel_y,
    double& accel_z
) noexcept;

}  // namespace dynamite::orblib_cpp
