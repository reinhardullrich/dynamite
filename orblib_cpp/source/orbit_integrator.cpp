#include "orbit_integrator.hpp"

#include "orbit_rhs.hpp"

#include <algorithm>
#include <cmath>
#include <limits>

namespace dynamite::orblib_cpp {
namespace {

struct OrbitRhsContext {
    InterpolatedPotential* potential = nullptr;
    double omega = 0.0;
    bool failed = false;
};

struct OrbitSampleContext {
    const double* sample_times = nullptr;
    int sample_count = 0;
    int next_sample = 0;
    double* sample_states = nullptr;
};

bool interval_contains(double x_old, double x, double target) noexcept {
    const double scale = std::max({1.0, std::abs(x_old), std::abs(x), std::abs(target)});
    const double eps = 64.0 * std::numeric_limits<double>::epsilon() * scale;
    if (x >= x_old) {
        return target >= x_old - eps && target <= x + eps;
    }
    return target <= x_old + eps && target >= x - eps;
}

void orbit_rhs_adapter(
    int n,
    double,
    const double* y,
    double* dydx,
    void* context
) noexcept {
    auto* rhs_context = static_cast<OrbitRhsContext*>(context);
    if (n != 6 || rhs_context == nullptr || rhs_context->potential == nullptr ||
        !evaluate_orbit_rhs(*rhs_context->potential, rhs_context->omega, y, dydx)) {
        if (rhs_context != nullptr) {
            rhs_context->failed = true;
        }
        for (int i = 0; i < n; ++i) {
            dydx[i] = 0.0;
        }
    }
}

int orbit_sample_observer(
    int,
    double x_old,
    double x,
    const double* y,
    int,
    const Dop853& solver,
    void* context
) noexcept {
    auto* samples = static_cast<OrbitSampleContext*>(context);
    while (samples->next_sample < samples->sample_count &&
           interval_contains(x_old, x, samples->sample_times[samples->next_sample])) {
        const int sample_index = samples->next_sample;
        const double target = samples->sample_times[sample_index];
        const int offset = sample_index * 6;
        if (target == x) {
            for (int component = 0; component < 6; ++component) {
                samples->sample_states[offset + component] = y[component];
            }
        } else {
            for (int component = 0; component < 6; ++component) {
                samples->sample_states[offset + component] =
                    solver.dense_value(component, target);
            }
        }
        samples->next_sample += 1;
    }
    return 1;
}

}  // namespace

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
) noexcept {
    OrbitIntegrationResult result;
    result.final_time = t_start;
    for (int i = 0; i < 6; ++i) {
        final_state[i] = initial_state[i];
    }

    Dop853Options options;
    options.rtol = rtol;
    options.atol = atol;
    options.max_steps = max_steps;
    options.stiffness_check_interval = -1;

    OrbitRhsContext rhs_context;
    rhs_context.potential = &potential;
    rhs_context.omega = omega;

    Dop853 solver;
    double time = t_start;
    result.solver = solver.integrate(
        6,
        time,
        final_state,
        t_end,
        orbit_rhs_adapter,
        &rhs_context,
        options
    );
    result.final_time = time;
    result.rhs_failed = rhs_context.failed;
    return result;
}

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
    double initial_step
) noexcept {
    OrbitIntegrationResult result;
    result.final_time = t_start;
    samples_written = 0;
    for (int i = 0; i < 6; ++i) {
        final_state[i] = initial_state[i];
    }

    if (sample_count < 0 || (sample_count > 0 && (sample_times == nullptr || sample_states == nullptr))) {
        result.solver.status = -1;
        return result;
    }

    const double direction = std::copysign(1.0, t_end - t_start);
    for (int i = 0; i < sample_count; ++i) {
        if (!interval_contains(t_start, t_end, sample_times[i])) {
            result.solver.status = -1;
            return result;
        }
        if (i > 0 && (sample_times[i] - sample_times[i - 1]) * direction < 0.0) {
            result.solver.status = -1;
            return result;
        }
    }

    Dop853Options options;
    options.rtol = rtol;
    options.atol = atol;
    options.max_steps = max_steps;
    options.stiffness_check_interval = -1;
    options.dense_components = sample_count > 0 ? 6 : 0;
    options.initial_step = initial_step;

    OrbitRhsContext rhs_context;
    rhs_context.potential = &potential;
    rhs_context.omega = omega;

    OrbitSampleContext sample_context;
    sample_context.sample_times = sample_times;
    sample_context.sample_count = sample_count;
    sample_context.sample_states = sample_states;

    Dop853 solver;
    double time = t_start;
    result.solver = solver.integrate(
        6,
        time,
        final_state,
        t_end,
        orbit_rhs_adapter,
        &rhs_context,
        options,
        sample_count > 0 ? orbit_sample_observer : nullptr,
        sample_count > 0 ? &sample_context : nullptr
    );
    result.final_time = time;
    result.rhs_failed = rhs_context.failed;
    samples_written = sample_context.next_sample;
    if (result.solver.status == 1 && samples_written != sample_count) {
        result.solver.status = -1;
    }
    return result;
}

}  // namespace dynamite::orblib_cpp
