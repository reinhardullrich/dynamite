#pragma once

#include "interpolated_potential.hpp"
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

bool compute_unregularized_orbit_grid(
    int energy_count,
    int i2_count,
    const double* outer_boundaries,
    const double* middle_boundaries,
    const int* irregular,
    int* noreg_grid
) noexcept;

bool compute_tube_start_schedule(
    int energy_count,
    int i2_count,
    int i3_count,
    const double* inner_boundaries,
    const double* middle_boundaries,
    const double* outer_boundaries,
    const int* irregular,
    const int* noreg_grid,
    double* start_radii,
    int* noreg_flags
) noexcept;

bool build_tube_start_records(
    const TriaxialMgeSetup& mge,
    const DarkHaloSetup& halo,
    double black_hole_mass,
    double black_hole_softening_km,
    int energy_count,
    int i2_count,
    int i3_count,
    const double* inner_boundaries,
    const double* middle_boundaries,
    const double* outer_boundaries,
    const int* irregular,
    const int* noreg_grid,
    const double* theta_values,
    const double* energies,
    const double* circular_periods,
    const double* circular_radii,
    const double* circular_velocities,
    double* records,
    int* noreg_flags,
    bool include_retrograde,
    double* retrograde_records,
    int* retrograde_noreg_flags
) noexcept;

bool calculate_box_start_record(
    const TriaxialMgeSetup& mge,
    const DarkHaloSetup& halo,
    double black_hole_mass,
    double black_hole_softening_km,
    double request_radius,
    double energy,
    int i2_index,
    int i3_index,
    int i2_count,
    int i3_count,
    double circular_radius,
    double circular_period,
    double circular_velocity,
    double* record,
    int& iterations
) noexcept;

bool build_box_start_records(
    const TriaxialMgeSetup& mge,
    const DarkHaloSetup& halo,
    double black_hole_mass,
    double black_hole_softening_km,
    int energy_count,
    int i2_count,
    int i3_count,
    const double* energies,
    const double* circular_periods,
    const double* circular_radii,
    const double* circular_velocities,
    double* records,
    int* noreg_flags,
    int* iterations
) noexcept;

bool measure_tube_orbit_width(
    InterpolatedPotential& potential,
    double radius,
    double theta,
    double energy,
    double circular_period,
    int plane,
    double integrator_accuracy,
    int crossing_capacity,
    double* crossing_positions,
    double& width,
    int& crossing_count,
    int& solver_status,
    int& function_evaluations
) noexcept;

bool find_tube_radius(
    InterpolatedPotential& potential,
    double inner_radius,
    double middle_radius,
    double outer_radius,
    double energy,
    double circular_period,
    double theta,
    int plane,
    double integrator_accuracy,
    int crossing_capacity,
    double& radius,
    double& width,
    int& width_evaluations,
    int& solver_status,
    int& crossing_count,
    int& function_evaluations
) noexcept;

}  // namespace dynamite::orblib_cpp
