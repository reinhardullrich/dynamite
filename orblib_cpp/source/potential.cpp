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

}  // namespace dynamite::orblib_cpp
