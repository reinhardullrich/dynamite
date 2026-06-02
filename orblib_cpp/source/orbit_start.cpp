#include "orbit_start.hpp"

#include "dop853.hpp"

#include <algorithm>
#include <cstddef>
#include <cmath>
#include <limits>

namespace dynamite::orblib_cpp {

namespace {

constexpr double kPi = 3.141592653589793238462643383279502884;

struct TubeWidthRhsContext {
    InterpolatedPotential* potential = nullptr;
    bool failed = false;
};

struct TubeWidthObserverContext {
    int plane_index = 0;
    int crossing_capacity = 0;
    int crossing_count = 0;
    double crossing_tolerance_radius = 0.0;
    double previous_plane_value = 0.0;
    double min_projected_radius = std::numeric_limits<double>::infinity();
    double max_projected_radius = -std::numeric_limits<double>::infinity();
    double* crossing_positions = nullptr;
};

void tube_width_rhs(
    int n,
    double,
    const double* y,
    double* dydx,
    void* context
) noexcept {
    auto* rhs_context = static_cast<TubeWidthRhsContext*>(context);
    if (n != 6 || rhs_context == nullptr || rhs_context->potential == nullptr) {
        if (rhs_context != nullptr) {
            rhs_context->failed = true;
        }
        for (int i = 0; i < n; ++i) {
            dydx[i] = 0.0;
        }
        return;
    }

    dydx[0] = y[3];
    dydx[1] = y[4];
    dydx[2] = y[5];
    if (!rhs_context->potential->evaluate_acceleration(
            y[0],
            y[1],
            y[2],
            dydx[3],
            dydx[4],
            dydx[5]
        )) {
        rhs_context->failed = true;
        dydx[3] = 0.0;
        dydx[4] = 0.0;
        dydx[5] = 0.0;
    }
}

double projected_radius_for_plane(const double* position, int plane_index) noexcept {
    if (plane_index == 0) {
        return std::sqrt(position[1] * position[1] + position[2] * position[2]);
    }
    if (plane_index == 1) {
        return std::sqrt(position[0] * position[0] + position[2] * position[2]);
    }
    return std::sqrt(position[0] * position[0] + position[1] * position[1]);
}

int tube_width_observer(
    int nr,
    double x_old,
    double x,
    const double* y,
    int,
    const Dop853& solver,
    void* context
) noexcept {
    auto* observer = static_cast<TubeWidthObserverContext*>(context);
    if (observer == nullptr) {
        return -1;
    }
    if (nr == 1) {
        observer->crossing_count = 0;
        observer->previous_plane_value = y[observer->plane_index];
        return 1;
    }
    if (observer->crossing_count >= observer->crossing_capacity) {
        return -1;
    }

    const double current_plane_value = y[observer->plane_index];
    if (current_plane_value * observer->previous_plane_value < 0.0) {
        double x_max = current_plane_value > 0.0 ? x : x_old;
        double x_min = current_plane_value > 0.0 ? x_old : x;
        double x_mid = 0.5 * (x_min + x_max);
        int bisection_count = 0;
        for (;;) {
            x_mid = 0.5 * (x_min + x_max);
            const double y_mid = solver.dense_value(observer->plane_index, x_mid);
            bisection_count += 1;
            if (std::abs(y_mid) < observer->crossing_tolerance_radius * 1.0e-4 ||
                bisection_count > 40) {
                break;
            }
            if (y_mid < 0.0) {
                x_min = x_mid;
            } else {
                x_max = x_mid;
            }
        }
        if (bisection_count < 40) {
            double position[3] = {
                solver.dense_value(0, x_mid),
                solver.dense_value(1, x_mid),
                solver.dense_value(2, x_mid),
            };
            const int crossing_index = observer->crossing_count;
            if (observer->crossing_positions != nullptr) {
                const int offset = crossing_index * 3;
                observer->crossing_positions[offset] = position[0];
                observer->crossing_positions[offset + 1] = position[1];
                observer->crossing_positions[offset + 2] = position[2];
            }
            const double projected_radius = projected_radius_for_plane(position, observer->plane_index);
            observer->min_projected_radius =
                std::min(observer->min_projected_radius, projected_radius);
            observer->max_projected_radius =
                std::max(observer->max_projected_radius, projected_radius);
            observer->crossing_count += 1;
            if (observer->crossing_count >= observer->crossing_capacity) {
                observer->previous_plane_value = current_plane_value;
                return -1;
            }
        }
    }

    observer->previous_plane_value = current_plane_value;
    return 1;
}

bool calculate_interpolated_orbit_start_state(
    InterpolatedPotential& potential,
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

    double potential_value = 0.0;
    if (!potential.evaluate_potential(state[0], state[1], state[2], potential_value)) {
        return false;
    }
    double vy = 2.0 * (potential_value - energy);
    if (vy >= 1.0e-300) {
        vy = std::sqrt(vy);
    }
    if (vy < 0.0 || std::isnan(vy)) {
        vy = std::sqrt(2.0 * potential_value * 1.0e-12);
    }
    if (!std::isfinite(vy)) {
        return false;
    }
    state[4] = vy;
    return true;
}

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
) noexcept {
    width = 0.0;
    crossing_count = 0;
    solver_status = 0;
    function_evaluations = 0;
    if (radius <= 0.0 || circular_period <= 0.0 || integrator_accuracy <= 0.0 ||
        crossing_capacity <= 0 || plane < 1 || plane > 3 || !std::isfinite(radius) ||
        !std::isfinite(theta) || !std::isfinite(energy) || !std::isfinite(circular_period)) {
        return false;
    }

    double state[6] = {0.0, 0.0, 0.0, 0.0, 0.0, 0.0};
    if (!calculate_interpolated_orbit_start_state(potential, radius, theta, energy, state)) {
        return false;
    }

    TubeWidthRhsContext rhs_context;
    rhs_context.potential = &potential;

    TubeWidthObserverContext observer;
    observer.plane_index = plane - 1;
    observer.crossing_capacity = crossing_capacity;
    observer.crossing_tolerance_radius = radius;
    observer.crossing_positions = crossing_positions;

    Dop853Options options;
    options.rtol = integrator_accuracy;
    options.atol = 1.0e-8;
    options.max_steps = 100000000;
    options.stiffness_check_interval = -1;
    options.dense_components = 3;

    double time = 0.0;
    const double end_time = 500.0 * static_cast<double>(crossing_capacity) * circular_period;
    Dop853 solver;
    const Dop853Result result = solver.integrate(
        6,
        time,
        state,
        end_time,
        tube_width_rhs,
        &rhs_context,
        options,
        tube_width_observer,
        &observer
    );

    solver_status = result.status;
    function_evaluations = result.function_evaluations;
    crossing_count = observer.crossing_count;
    if (rhs_context.failed || crossing_count <= 0 || !std::isfinite(observer.min_projected_radius) ||
        !std::isfinite(observer.max_projected_radius)) {
        return false;
    }
    width = observer.max_projected_radius - observer.min_projected_radius;
    return result.status == 1 || result.status == 2;
}

}  // namespace dynamite::orblib_cpp
