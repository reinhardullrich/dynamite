#include "dop853.hpp"
#include "ran1.hpp"

#include <algorithm>
#include <cmath>
#include <limits>

namespace {

constexpr int kAbiVersion = 1;
constexpr int kStatusOk = 0;
constexpr int kStatusInvalidArgument = -1;
constexpr int kStatusNotImplemented = -100;
constexpr int kStatusException = -101;

void set_status(int* status, int value) noexcept {
    if (status != nullptr) {
        *status = value;
    }
}

void harmonic_rhs(
    int,
    double,
    const double* y,
    double* dydx,
    void*
) noexcept {
    dydx[0] = y[1];
    dydx[1] = -y[0];
}

struct HarmonicSampleContext {
    const double* sample_x = nullptr;
    int sample_count = 0;
    int next_sample = 0;
    double* sample_y0 = nullptr;
    double* sample_y1 = nullptr;
};

bool interval_contains(double x_old, double x, double target) noexcept {
    const double scale = std::max({1.0, std::abs(x_old), std::abs(x), std::abs(target)});
    const double eps = 64.0 * std::numeric_limits<double>::epsilon() * scale;
    if (x >= x_old) {
        return target >= x_old - eps && target <= x + eps;
    }
    return target <= x_old + eps && target >= x - eps;
}

int harmonic_sample_observer(
    int,
    double x_old,
    double x,
    const double* y,
    int,
    const dynamite::orblib_cpp::Dop853& solver,
    void* context
) noexcept {
    auto* samples = static_cast<HarmonicSampleContext*>(context);
    while (samples->next_sample < samples->sample_count &&
           interval_contains(x_old, x, samples->sample_x[samples->next_sample])) {
        const int index = samples->next_sample;
        const double target = samples->sample_x[index];
        if (target == x) {
            samples->sample_y0[index] = y[0];
            samples->sample_y1[index] = y[1];
        } else {
            samples->sample_y0[index] = solver.dense_value(0, target);
            samples->sample_y1[index] = solver.dense_value(1, target);
        }
        samples->next_sample += 1;
    }
    return 1;
}

}  // namespace

extern "C" int orblib_cpp_api_abi_version() noexcept {
    return kAbiVersion;
}

extern "C" void orblib_cpp_api_ran1_sequence(
    int seed,
    int count,
    double* values,
    int* status
) noexcept {
    if (count < 0 || (count > 0 && values == nullptr)) {
        set_status(status, kStatusInvalidArgument);
        return;
    }

    dynamite::orblib_cpp::Ran1 rng(seed);
    for (int i = 0; i < count; ++i) {
        values[i] = rng.next();
    }
    set_status(status, kStatusOk);
}

extern "C" void orblib_cpp_api_dop853_harmonic(
    double x_start,
    double y0_start,
    double y1_start,
    double x_end,
    double rtol,
    double atol,
    const double* sample_x,
    int sample_count,
    double* final_y0,
    double* final_y1,
    double* sample_y0,
    double* sample_y1,
    int* function_evaluations,
    int* computed_steps,
    int* accepted_steps,
    int* rejected_steps,
    int* status
) noexcept {
    if (final_y0 == nullptr || final_y1 == nullptr || function_evaluations == nullptr ||
        computed_steps == nullptr || accepted_steps == nullptr || rejected_steps == nullptr ||
        sample_count < 0 || rtol <= 0.0 || atol <= 0.0 ||
        (sample_count > 0 && (sample_x == nullptr || sample_y0 == nullptr || sample_y1 == nullptr))) {
        set_status(status, kStatusInvalidArgument);
        return;
    }

    const double direction = std::copysign(1.0, x_end - x_start);
    for (int i = 0; i < sample_count; ++i) {
        if (!interval_contains(x_start, x_end, sample_x[i])) {
            set_status(status, kStatusInvalidArgument);
            return;
        }
        if (i > 0 && (sample_x[i] - sample_x[i - 1]) * direction < 0.0) {
            set_status(status, kStatusInvalidArgument);
            return;
        }
    }

    try {
        dynamite::orblib_cpp::Dop853 solver;
        dynamite::orblib_cpp::Dop853Options options;
        options.rtol = rtol;
        options.atol = atol;
        options.dense_components = sample_count > 0 ? 2 : 0;
        options.stiffness_check_interval = -1;

        double x = x_start;
        double y[2] = {y0_start, y1_start};
        HarmonicSampleContext sample_context;
        sample_context.sample_x = sample_x;
        sample_context.sample_count = sample_count;
        sample_context.sample_y0 = sample_y0;
        sample_context.sample_y1 = sample_y1;

        const dynamite::orblib_cpp::Dop853Result result = solver.integrate(
            2,
            x,
            y,
            x_end,
            harmonic_rhs,
            nullptr,
            options,
            sample_count > 0 ? harmonic_sample_observer : nullptr,
            sample_count > 0 ? &sample_context : nullptr
        );

        *final_y0 = y[0];
        *final_y1 = y[1];
        *function_evaluations = result.function_evaluations;
        *computed_steps = result.computed_steps;
        *accepted_steps = result.accepted_steps;
        *rejected_steps = result.rejected_steps;
        if (result.status == 1 && sample_context.next_sample != sample_count) {
            set_status(status, kStatusInvalidArgument);
            return;
        }
        set_status(status, result.status);
    } catch (...) {
        set_status(status, kStatusException);
    }
}

extern "C" void orblib_cpp_api_run_orbitstart_memory(
    int,
    int,
    const double*,
    const double*,
    const double*,
    const double*,
    double,
    double,
    double,
    double,
    double,
    double,
    double,
    int,
    double,
    double,
    int,
    int,
    int,
    int,
    int,
    int,
    int,
    int,
    const double*,
    int,
    double*,
    int*,
    double*,
    int*,
    int* rows_written,
    int* box_rows_written,
    int* status
) noexcept {
    set_status(rows_written, 0);
    set_status(box_rows_written, 0);
    set_status(status, kStatusNotImplemented);
}

extern "C" void orblib_cpp_api_run_orblib_direct(
    int,
    int,
    const double*,
    const double*,
    const double*,
    const double*,
    double,
    double,
    double,
    double,
    double,
    double,
    double,
    int,
    double,
    double,
    int,
    int,
    int,
    int,
    int,
    int,
    int,
    int,
    const double*,
    int,
    const double*,
    const int*,
    double,
    int,
    int,
    int,
    double,
    int,
    int,
    const int*,
    const double*,
    const double*,
    int,
    const double*,
    const double*,
    const double*,
    const int*,
    const int*,
    const int*,
    const int*,
    const double*,
    const double*,
    const int*,
    int,
    const int*,
    const int*,
    const int*,
    const char*,
    const char*,
    const char*,
    const char*,
    int* status
) noexcept {
    set_status(status, kStatusNotImplemented);
}
