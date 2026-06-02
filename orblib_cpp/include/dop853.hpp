#pragma once

#include <vector>

namespace dynamite::orblib_cpp {

using Dop853Rhs = void (*)(int n, double x, const double* y, double* dydx, void* context) noexcept;

class Dop853;

using Dop853Solout = int (*)(
    int nr,
    double x_old,
    double x,
    const double* y,
    int n,
    const Dop853& solver,
    void* context
) noexcept;

struct Dop853Options {
    double rtol = 1.0e-10;
    double atol = 1.0e-10;
    double uround = 2.3e-16;
    double safety = 0.9;
    double fac1 = 0.333;
    double fac2 = 6.0;
    double beta = 0.0;
    double max_step = 0.0;
    double initial_step = 0.0;
    int max_steps = 100000;
    int stiffness_check_interval = -1;
    int dense_components = 0;
};

struct Dop853Result {
    int status = 0;
    int function_evaluations = 0;
    int computed_steps = 0;
    int accepted_steps = 0;
    int rejected_steps = 0;
    double suggested_step = 0.0;
};

class Dop853 {
public:
    Dop853() = default;

    Dop853Result integrate(
        int n,
        double& x,
        double* y,
        double x_end,
        Dop853Rhs rhs,
        void* rhs_context,
        const Dop853Options& options,
        Dop853Solout solout = nullptr,
        void* solout_context = nullptr
    );

    double dense_value(int component, double x) const noexcept;

private:
    void ensure_workspace(int n, int dense_components);

    double initial_step(
        int n,
        double x,
        const double* y,
        double x_end,
        double posneg,
        double max_step,
        double atol,
        double rtol,
        Dop853Rhs rhs,
        void* rhs_context
    );

    int n_ = 0;
    int dense_components_ = 0;
    double x_old_ = 0.0;
    double dense_step_ = 1.0;
    std::vector<double> k1_;
    std::vector<double> k2_;
    std::vector<double> k3_;
    std::vector<double> k4_;
    std::vector<double> k5_;
    std::vector<double> k6_;
    std::vector<double> k7_;
    std::vector<double> k8_;
    std::vector<double> k9_;
    std::vector<double> k10_;
    std::vector<double> y1_;
    std::vector<double> cont_;
    std::vector<int> components_;
};

}  // namespace dynamite::orblib_cpp
