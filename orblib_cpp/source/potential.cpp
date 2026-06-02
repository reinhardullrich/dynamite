#include "potential.hpp"

#include <cmath>

namespace dynamite::orblib_cpp {
namespace {

constexpr double kPi = 3.141592653589793238462643383279502884197;
constexpr double kGravConstKm = 6.67428e-11 * 1.98892e30 / 1.0e9;
constexpr double kParsecKm = 1.4959787068e8 * (648.0e3 / kPi);
constexpr double kRhoCrit =
    (3.0 * (7.0e-5 / kParsecKm) * (7.0e-5 / kParsecKm)) /
    (8.0 * kPi * kGravConstKm);

double stable_log1p(double ratio) noexcept {
    if (ratio >= 1.0) {
        return std::log(1.0 + ratio);
    }
    return 2.0 * std::atanh(ratio / (2.0 + ratio));
}

double zh_gammln(double xx) noexcept {
    constexpr double cof[6] = {
        76.18009172947146,
        -86.50532032941677,
        24.01409824083091,
        -1.231739572450155,
        0.1208650973866179e-2,
        -0.5395239384953e-5,
    };
    constexpr double stp = 2.5066282746310005;
    double x = xx;
    double y = x;
    double tmp = x + 5.5;
    tmp = (x + 0.5) * std::log(tmp) - tmp;
    double ser = 1.000000000190015;
    for (double coefficient : cof) {
        y += 1.0;
        ser += coefficient / y;
    }
    return tmp + std::log(stp * ser / x);
}

double zh_beta(double z, double w) noexcept {
    return std::exp(zh_gammln(z) + zh_gammln(w) - zh_gammln(z + w));
}

double zh_betacf(double a, double b, double x) noexcept {
    constexpr int max_iterations = 500;
    constexpr double epsilon = 3.0e-7;
    constexpr double fpmin = 1.0e-30;

    const double qab = a + b;
    const double qap = a + 1.0;
    const double qam = a - 1.0;
    double c = 1.0;
    double d = 1.0 - qab * x / qap;
    if (std::abs(d) < fpmin) {
        d = fpmin;
    }
    d = 1.0 / d;
    double h = d;

    for (int m = 1; m <= max_iterations; ++m) {
        const int m2 = 2 * m;
        double aa = m * (b - m) * x / ((qam + m2) * (a + m2));
        d = 1.0 + aa * d;
        if (std::abs(d) < fpmin) {
            d = fpmin;
        }
        c = 1.0 + aa / c;
        if (std::abs(c) < fpmin) {
            c = fpmin;
        }
        d = 1.0 / d;
        h *= d * c;

        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2));
        d = 1.0 + aa * d;
        if (std::abs(d) < fpmin) {
            d = fpmin;
        }
        c = 1.0 + aa / c;
        if (std::abs(c) < fpmin) {
            c = fpmin;
        }
        d = 1.0 / d;
        const double del = d * c;
        h *= del;
        if (std::abs(del - 1.0) < epsilon) {
            break;
        }
    }

    return h;
}

double zh_betai(double a, double b, double x) noexcept {
    double bt = 0.0;
    if (x == 0.0) {
        bt = 0.0;
    } else if (x == 1.0) {
        return zh_beta(a, b);
    } else {
        bt = std::pow(x, a) * std::pow(1.0 - x, b);
    }

    if (x < (a + 1.0) / (a + b + 2.0) || b <= 0.0) {
        return bt * zh_betacf(a, b, x) / a;
    }
    return zh_beta(a, b) - bt * zh_betacf(b, a, 1.0 - x) / b;
}

double gnfw_zeta(double concentration, double gamma) noexcept {
    if (gamma < 1.0) {
        return std::pow((1.0 + concentration) / concentration, gamma - 2.0) *
                   (2.0 * gamma * concentration - 3.0 * concentration + gamma - 2.0) /
                   (gamma * gamma - 3.0 * gamma + 2.0) / concentration +
               std::exp(zh_gammln(2.0 - gamma) - zh_gammln(1.0 - gamma)) *
                   zh_betai(1.0 - gamma, 0.0, concentration / (concentration + 1.0)) /
                   (1.0 - gamma);
    }
    if (gamma == 1.0) {
        return std::log(1.0 + concentration) - concentration / (1.0 + concentration);
    }

    const double tmp_gamma =
        kPi / std::sin(kPi * (1.0 - gamma)) / std::exp(zh_gammln(gamma));
    return std::pow((1.0 + concentration) / concentration, gamma - 2.0) *
               (2.0 * gamma * concentration - 3.0 * concentration + gamma - 2.0) /
               (gamma * gamma - 3.0 * gamma + 2.0) / concentration +
           (std::exp(zh_gammln(2.0 - gamma)) / tmp_gamma) *
               zh_betai(1.0 - gamma, 0.0, concentration / (concentration + 1.0)) /
               (1.0 - gamma);
}

void evaluate_black_hole(
    double mass,
    double softening_km,
    double x,
    double y,
    double z,
    double& potential,
    double& accel_x,
    double& accel_y,
    double& accel_z
) noexcept {
    if (mass == 0.0) {
        potential = 0.0;
        accel_x = 0.0;
        accel_y = 0.0;
        accel_z = 0.0;
        return;
    }
    const double radius_squared = x * x + y * y + z * z;
    const double softened_radius_squared = radius_squared + softening_km * softening_km;
    potential = kGravConstKm * mass / std::sqrt(softened_radius_squared);
    const double scale = -kGravConstKm * mass /
                         (softened_radius_squared * std::sqrt(softened_radius_squared));
    accel_x = x * scale;
    accel_y = y * scale;
    accel_z = z * scale;
}

}  // namespace

bool setup_dark_halo(
    int profile_type,
    int n_params,
    const double* params,
    double total_stellar_mass,
    DarkHaloSetup& halo
) noexcept {
    halo = DarkHaloSetup{};
    halo.profile_type = profile_type;

    switch (profile_type) {
    case 0:
        return n_params == 0;
    case 1: {
        if (n_params != 2 || params == nullptr || params[0] <= 0.0 || total_stellar_mass <= 0.0) {
            return false;
        }
        const double concentration = params[0];
        const double dark_fraction = params[1];
        halo.rhoc = (200.0 / 3.0) * kRhoCrit * concentration * concentration * concentration /
                    (std::log(1.0 + concentration) - concentration / (1.0 + concentration));
        halo.rc = std::pow(
            (3.0 / (800.0 * kPi * kRhoCrit * concentration * concentration * concentration)) *
                dark_fraction * total_stellar_mass,
            1.0 / 3.0
        );
        halo.params[0] = concentration;
        halo.params[1] = dark_fraction;
        return halo.rc > 0.0;
    }
    case 2:
        if (n_params != 2 || params == nullptr || params[0] <= 0.0 || params[1] <= 0.0) {
            return false;
        }
        halo.rhoc = params[0];
        halo.rc = params[1];
        halo.params[0] = params[0];
        halo.params[1] = params[1];
        return true;
    case 3:
        if (n_params != 4 || params == nullptr || params[0] <= 0.0 || params[1] <= 0.0 ||
            params[2] > 1.0 || params[3] <= 0.0 || params[2] < params[3]) {
            return false;
        }
        halo.params[0] = params[0] * params[0];
        halo.params[1] = (params[1] * kParsecKm * 1.0e3) * (params[1] * kParsecKm * 1.0e3);
        halo.params[2] = params[2] * params[2];
        halo.params[3] = params[3] * params[3];
        return true;
    case 5: {
        if (n_params != 3 || params == nullptr || params[0] <= 0.0 || params[1] <= 0.0 ||
            !std::isfinite(params[2])) {
            return false;
        }
        const double concentration = params[0];
        const double virial_mass = params[1];
        const double gamma = params[2];
        const double zeta = gnfw_zeta(concentration, gamma);
        if (!std::isfinite(zeta) || zeta == 0.0) {
            return false;
        }
        halo.rhoc = (200.0 / 3.0) * kRhoCrit * concentration * concentration * concentration /
                    zeta;
        halo.rc = std::pow(
            3.0 * virial_mass /
                (800.0 * kPi * kRhoCrit * concentration * concentration * concentration),
            1.0 / 3.0
        );
        halo.params[0] = concentration;
        halo.params[1] = virial_mass;
        halo.params[2] = gamma;
        return std::isfinite(halo.rhoc) && std::isfinite(halo.rc) && halo.rc > 0.0;
    }
    default:
        return false;
    }
}

bool evaluate_dark_halo(
    const DarkHaloSetup& halo,
    double x,
    double y,
    double z,
    double& potential,
    double& accel_x,
    double& accel_y,
    double& accel_z
) noexcept {
    potential = 0.0;
    accel_x = 0.0;
    accel_y = 0.0;
    accel_z = 0.0;
    const double radius_squared = x * x + y * y + z * z;
    const double radius = std::sqrt(radius_squared);

    switch (halo.profile_type) {
    case 0:
        return true;
    case 1: {
        if (radius <= 0.0 || halo.rc <= 0.0) {
            return false;
        }
        const double ratio = radius / halo.rc;
        const double log_term = stable_log1p(ratio);
        const double enclosed_term = log_term - ratio / (1.0 + ratio);
        const double potential_scale =
            4.0 * kPi * kGravConstKm * halo.rhoc * halo.rc * halo.rc * halo.rc;
        potential = potential_scale / radius * log_term;
        const double accel_scale = -potential_scale / radius_squared * enclosed_term / radius;
        accel_x = x * accel_scale;
        accel_y = y * accel_scale;
        accel_z = z * accel_scale;
        return true;
    }
    case 2: {
        if (radius <= 0.0 || halo.rc <= 0.0) {
            return false;
        }
        potential = 4.0 * kPi * kGravConstKm * halo.rhoc * halo.rc * halo.rc /
                    (2.0 * (1.0 + radius / halo.rc));
        const double acceleration_r =
            -2.0 * kPi * kGravConstKm * halo.rhoc * halo.rc /
            ((1.0 + radius / halo.rc) * (1.0 + radius / halo.rc));
        accel_x = x / radius * acceleration_r;
        accel_y = y / radius * acceleration_r;
        accel_z = z / radius * acceleration_r;
        return true;
    }
    case 3: {
        const double vc_squared = halo.params[0];
        const double core_radius_squared = halo.params[1];
        const double p_squared = halo.params[2];
        const double q_squared = halo.params[3];
        if (core_radius_squared <= 0.0 || p_squared <= 0.0 || q_squared <= 0.0) {
            return false;
        }
        const double denominator =
            core_radius_squared + x * x + y * y / p_squared + z * z / q_squared;
        const double coordinate_term = x * x + y * y / p_squared + z * z / q_squared;
        if (coordinate_term / core_radius_squared <= 1.0e-14) {
            return false;
        }
        potential = -0.5 * vc_squared * std::log(denominator);
        accel_x = -vc_squared * x / denominator;
        accel_y = -vc_squared * (y / p_squared) / denominator;
        accel_z = -vc_squared * (z / q_squared) / denominator;
        return true;
    }
    case 5: {
        if (radius <= 0.0 || halo.rc <= 0.0) {
            return false;
        }
        const double gamma = halo.params[2];
        const double dnorm = radius / halo.rc;
        const double xi = dnorm / (1.0 + dnorm);
        const double ibeta_v2 = zh_betai(3.0 - gamma, 0.0, xi);
        const double ibeta_v3 = zh_betai(1.0, 2.0 - gamma, 1.0 - xi);
        potential = 4.0 * kPi * kGravConstKm * halo.rhoc *
                    (ibeta_v2 / dnorm + ibeta_v3) * halo.rc * halo.rc;

        const double acceleration_r = 4.0 * kPi * kGravConstKm * halo.rhoc * halo.rc / dnorm;
        const double one_plus_dnorm = 1.0 + dnorm;
        const double t1 = std::pow(xi, 2.0 - gamma) / (1.0 - xi) / halo.rc / dnorm /
                          (one_plus_dnorm * one_plus_dnorm);
        const double t2 = std::pow(xi, 1.0 - gamma) / halo.rc /
                          (one_plus_dnorm * one_plus_dnorm);
        const double t3 = ibeta_v2 * halo.rc / radius_squared;
        const double scale = acceleration_r * (t1 - t2 - t3);
        accel_x = x * scale;
        accel_y = y * scale;
        accel_z = z * scale;
        return std::isfinite(potential) && std::isfinite(accel_x) && std::isfinite(accel_y) &&
               std::isfinite(accel_z);
    }
    default:
        return false;
    }
}

bool evaluate_dark_halo_acceleration(
    const DarkHaloSetup& halo,
    double x,
    double y,
    double z,
    double& accel_x,
    double& accel_y,
    double& accel_z
) noexcept {
    accel_x = 0.0;
    accel_y = 0.0;
    accel_z = 0.0;
    const double radius_squared = x * x + y * y + z * z;
    const double radius = std::sqrt(radius_squared);

    switch (halo.profile_type) {
    case 0:
        return true;
    case 1: {
        if (radius <= 0.0 || halo.rc <= 0.0) {
            return false;
        }
        const double ratio = radius / halo.rc;
        const double log_term = stable_log1p(ratio);
        const double enclosed_term = log_term - ratio / (1.0 + ratio);
        const double potential_scale =
            4.0 * kPi * kGravConstKm * halo.rhoc * halo.rc * halo.rc * halo.rc;
        const double accel_scale = -potential_scale / radius_squared * enclosed_term / radius;
        accel_x = x * accel_scale;
        accel_y = y * accel_scale;
        accel_z = z * accel_scale;
        return true;
    }
    case 2: {
        if (radius <= 0.0 || halo.rc <= 0.0) {
            return false;
        }
        const double acceleration_r =
            -2.0 * kPi * kGravConstKm * halo.rhoc * halo.rc /
            ((1.0 + radius / halo.rc) * (1.0 + radius / halo.rc));
        accel_x = x / radius * acceleration_r;
        accel_y = y / radius * acceleration_r;
        accel_z = z / radius * acceleration_r;
        return true;
    }
    case 3: {
        const double vc_squared = halo.params[0];
        const double core_radius_squared = halo.params[1];
        const double p_squared = halo.params[2];
        const double q_squared = halo.params[3];
        if (core_radius_squared <= 0.0 || p_squared <= 0.0 || q_squared <= 0.0) {
            return false;
        }
        const double denominator =
            core_radius_squared + x * x + y * y / p_squared + z * z / q_squared;
        accel_x = -vc_squared * x / denominator;
        accel_y = -vc_squared * (y / p_squared) / denominator;
        accel_z = -vc_squared * (z / q_squared) / denominator;
        return true;
    }
    case 5: {
        if (radius <= 0.0 || halo.rc <= 0.0) {
            return false;
        }
        const double gamma = halo.params[2];
        const double dnorm = radius / halo.rc;
        const double xi = dnorm / (1.0 + dnorm);
        const double ibeta_v2 = zh_betai(3.0 - gamma, 0.0, xi);
        const double acceleration_r = 4.0 * kPi * kGravConstKm * halo.rhoc * halo.rc / dnorm;
        const double one_plus_dnorm = 1.0 + dnorm;
        const double t1 = std::pow(xi, 2.0 - gamma) / (1.0 - xi) / halo.rc / dnorm /
                          (one_plus_dnorm * one_plus_dnorm);
        const double t2 = std::pow(xi, 1.0 - gamma) / halo.rc /
                          (one_plus_dnorm * one_plus_dnorm);
        const double t3 = ibeta_v2 * halo.rc / radius_squared;
        const double scale = acceleration_r * (t1 - t2 - t3);
        accel_x = x * scale;
        accel_y = y * scale;
        accel_z = z * scale;
        return std::isfinite(accel_x) && std::isfinite(accel_y) && std::isfinite(accel_z);
    }
    default:
        return false;
    }
}

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
) noexcept {
    if (!evaluate_triaxial_mge(mge, x, y, z, potential, accel_x, accel_y, accel_z)) {
        return false;
    }

    double term_potential = 0.0;
    double term_ax = 0.0;
    double term_ay = 0.0;
    double term_az = 0.0;
    evaluate_black_hole(
        black_hole_mass,
        black_hole_softening_km,
        x,
        y,
        z,
        term_potential,
        term_ax,
        term_ay,
        term_az
    );
    potential += term_potential;
    accel_x += term_ax;
    accel_y += term_ay;
    accel_z += term_az;

    if (!evaluate_dark_halo(halo, x, y, z, term_potential, term_ax, term_ay, term_az)) {
        return false;
    }
    potential += term_potential;
    accel_x += term_ax;
    accel_y += term_ay;
    accel_z += term_az;
    return true;
}

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
) noexcept {
    double potential = 0.0;
    if (!evaluate_triaxial_mge(mge, x, y, z, potential, accel_x, accel_y, accel_z)) {
        return false;
    }

    double term_potential = 0.0;
    double term_ax = 0.0;
    double term_ay = 0.0;
    double term_az = 0.0;
    evaluate_black_hole(
        black_hole_mass,
        black_hole_softening_km,
        x,
        y,
        z,
        term_potential,
        term_ax,
        term_ay,
        term_az
    );
    accel_x += term_ax;
    accel_y += term_ay;
    accel_z += term_az;

    if (!evaluate_dark_halo_acceleration(halo, x, y, z, term_ax, term_ay, term_az)) {
        return false;
    }
    accel_x += term_ax;
    accel_y += term_ay;
    accel_z += term_az;
    return true;
}

}  // namespace dynamite::orblib_cpp
