#include "orbit_integrator.hpp"

#include "orbit_rhs.hpp"

namespace dynamite::orblib_cpp {
namespace {

struct OrbitRhsContext {
    InterpolatedPotential* potential = nullptr;
    double omega = 0.0;
    bool failed = false;
};

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

}  // namespace dynamite::orblib_cpp
