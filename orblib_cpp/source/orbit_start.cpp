#include "orbit_start.hpp"

#include <algorithm>
#include <cstddef>
#include <cmath>

namespace dynamite::orblib_cpp {

namespace {

constexpr double kPi = 3.141592653589793238462643383279502884;

}  // namespace

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
) noexcept {
    iterations = 0;
    if (record == nullptr || request_radius <= 0.0 || energy == 0.0 ||
        i2_index < 0 || i3_index < 0 || i2_count <= 0 || i3_count <= 0 ||
        i2_index >= i2_count || i3_index >= i3_count ||
        !std::isfinite(request_radius) || !std::isfinite(energy) ||
        !std::isfinite(circular_radius) || !std::isfinite(circular_period) ||
        !std::isfinite(circular_velocity)) {
        return false;
    }

    const double theta =
        0.5 * kPi * (static_cast<double>(i2_index) + 0.5) / static_cast<double>(i2_count);
    const double phi =
        0.5 * kPi * (static_cast<double>(i3_index) + 0.5) / static_cast<double>(i3_count);
    double radius = 0.0;
    if (!find_equivalent_radius(
            mge,
            halo,
            black_hole_mass,
            black_hole_softening_km,
            request_radius,
            energy,
            theta,
            phi,
            radius,
            iterations
        )) {
        return false;
    }

    record[0] = radius * std::sin(theta) * std::cos(phi);
    record[1] = radius * std::sin(theta) * std::sin(phi);
    record[2] = radius * std::cos(theta);
    record[3] = 0.0;
    record[4] = 0.0;
    record[5] = 0.0;
    record[6] = circular_radius;
    record[7] = circular_period;
    record[8] = circular_velocity;
    return true;
}

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
) noexcept {
    if (energy_count <= 0 || i2_count <= 0 || i3_count <= 0 || energies == nullptr ||
        circular_periods == nullptr || circular_radii == nullptr ||
        circular_velocities == nullptr || records == nullptr || noreg_flags == nullptr ||
        iterations == nullptr) {
        return false;
    }

    for (int energy = 0; energy < energy_count; ++energy) {
        for (int i2 = 0; i2 < i2_count; ++i2) {
            for (int i3 = 0; i3 < i3_count; ++i3) {
                const int record_index = (energy * i2_count + i2) * i3_count + i3;
                int record_iterations = 0;
                if (!calculate_box_start_record(
                        mge,
                        halo,
                        black_hole_mass,
                        black_hole_softening_km,
                        circular_radii[energy],
                        energies[energy],
                        i2,
                        i3,
                        i2_count,
                        i3_count,
                        circular_radii[energy],
                        circular_periods[energy],
                        circular_velocities[energy],
                        records + static_cast<std::size_t>(record_index) * 9U,
                        record_iterations
                    )) {
                    return false;
                }
                noreg_flags[record_index] = 0;
                iterations[record_index] = record_iterations;
            }
        }
    }
    return true;
}

bool compute_unregularized_orbit_grid(
    int energy_count,
    int i2_count,
    const double* outer_boundaries,
    const double* middle_boundaries,
    const int* irregular,
    int* noreg_grid
) noexcept {
    if (energy_count <= 0 || i2_count <= 0 || outer_boundaries == nullptr ||
        middle_boundaries == nullptr || irregular == nullptr || noreg_grid == nullptr) {
        return false;
    }

    for (int energy = 0; energy < energy_count; ++energy) {
        int noreg = 0;
        for (int i2 = i2_count - 1; i2 >= 0; --i2) {
            const int index = energy * i2_count + i2;
            const double outer = outer_boundaries[index];
            const double middle = middle_boundaries[index];
            if (outer == 0.0 || !std::isfinite(outer) || !std::isfinite(middle)) {
                return false;
            }
            if (std::abs(middle - outer) / outer > 1.0e-5 && irregular[energy] == 0) {
                noreg = 1;
            }
            noreg_grid[index] = noreg;
        }
    }
    return true;
}

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
) noexcept {
    if (energy_count <= 0 || i2_count <= 0 || i3_count <= 0 || inner_boundaries == nullptr ||
        middle_boundaries == nullptr || outer_boundaries == nullptr || irregular == nullptr ||
        noreg_grid == nullptr || start_radii == nullptr || noreg_flags == nullptr) {
        return false;
    }

    const double denominator = static_cast<double>(i3_count) - 0.8;
    if (denominator == 0.0) {
        return false;
    }
    const int max_irregular = *std::max_element(irregular, irregular + energy_count);

    for (int energy = 0; energy < energy_count; ++energy) {
        for (int i2 = 0; i2 < i2_count; ++i2) {
            const int boundary_index = energy * i2_count + i2;
            double inner = inner_boundaries[boundary_index];
            double middle = middle_boundaries[boundary_index];
            const double outer = outer_boundaries[boundary_index];
            if (!std::isfinite(inner) || !std::isfinite(middle) || !std::isfinite(outer)) {
                return false;
            }
            if (irregular[energy] == 1) {
                inner = 0.0;
                middle = outer;
            }
            for (int i3 = 0; i3 < i3_count; ++i3) {
                const double fraction = (static_cast<double>(i3 + 1) - 0.9) / denominator;
                const int schedule_index = (energy * i2_count + i2) * i3_count + i3;
                start_radii[schedule_index] = inner + (middle - inner) * fraction;

                int noreg = 0;
                if (i3 == i3_count - 1 && noreg_grid[boundary_index] == 1) {
                    noreg = 1;
                }
                if (max_irregular == energy + 1) {
                    noreg = 1;
                }
                noreg_flags[schedule_index] = noreg;
            }
        }
    }
    return true;
}

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
) noexcept {
    if (energy_count <= 0 || i2_count <= 0 || i3_count <= 0 || inner_boundaries == nullptr ||
        middle_boundaries == nullptr || outer_boundaries == nullptr || irregular == nullptr ||
        noreg_grid == nullptr || theta_values == nullptr || energies == nullptr ||
        circular_periods == nullptr || circular_radii == nullptr ||
        circular_velocities == nullptr || records == nullptr || noreg_flags == nullptr ||
        (include_retrograde && (retrograde_records == nullptr || retrograde_noreg_flags == nullptr))) {
        return false;
    }

    const double denominator = static_cast<double>(i3_count) - 0.8;
    if (denominator == 0.0) {
        return false;
    }
    const int max_irregular = *std::max_element(irregular, irregular + energy_count);

    for (int energy = 0; energy < energy_count; ++energy) {
        if (!std::isfinite(energies[energy]) || !std::isfinite(circular_periods[energy]) ||
            !std::isfinite(circular_radii[energy]) || !std::isfinite(circular_velocities[energy])) {
            return false;
        }
        for (int i2 = 0; i2 < i2_count; ++i2) {
            if (!std::isfinite(theta_values[i2])) {
                return false;
            }
            const int boundary_index = energy * i2_count + i2;
            double inner = inner_boundaries[boundary_index];
            double middle = middle_boundaries[boundary_index];
            const double outer = outer_boundaries[boundary_index];
            if (!std::isfinite(inner) || !std::isfinite(middle) || !std::isfinite(outer)) {
                return false;
            }
            if (irregular[energy] == 1) {
                inner = 0.0;
                middle = outer;
            }
            for (int i3 = 0; i3 < i3_count; ++i3) {
                const double fraction = (static_cast<double>(i3 + 1) - 0.9) / denominator;
                const double start_radius = inner + (middle - inner) * fraction;
                const int record_index = (energy * i2_count + i2) * i3_count + i3;
                double* record = records + static_cast<std::size_t>(record_index) * 9U;

                if (!calculate_orbit_start_state(
                        mge,
                        halo,
                        black_hole_mass,
                        black_hole_softening_km,
                        start_radius,
                        theta_values[i2],
                        energies[energy],
                        record
                    )) {
                    return false;
                }
                record[6] = circular_radii[energy];
                record[7] = circular_periods[energy];
                record[8] = circular_velocities[energy];

                int noreg = 0;
                if (i3 == i3_count - 1 && noreg_grid[boundary_index] == 1) {
                    noreg = 1;
                }
                if (max_irregular == energy + 1) {
                    noreg = 1;
                }
                noreg_flags[record_index] = noreg;

                if (include_retrograde) {
                    double* retrograde_record =
                        retrograde_records + static_cast<std::size_t>(record_index) * 9U;
                    for (int component = 0; component < 9; ++component) {
                        retrograde_record[component] = record[component];
                    }
                    retrograde_record[4] = -retrograde_record[4];
                    retrograde_noreg_flags[record_index] = noreg;
                }
            }
        }
    }
    return true;
}

}  // namespace dynamite::orblib_cpp
