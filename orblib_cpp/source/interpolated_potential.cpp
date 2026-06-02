#include "interpolated_potential.hpp"

#include <algorithm>
#include <cmath>
#include <limits>

namespace dynamite::orblib_cpp {
namespace {

constexpr double kPiOver2 = 1.570796326794896619231321691639751442099;
constexpr double kLogTiny = -708.39641853226408;

}  // namespace

bool InterpolatedPotential::setup(
    const TriaxialMgeSetup& mge,
    const DarkHaloSetup& halo,
    double black_hole_mass,
    double black_hole_softening_km,
    const InterpolationGridConfig& config
) {
    if (mge.sigobs_km.empty() || mge.sigintr_km.empty() || black_hole_mass < 0.0 ||
        black_hole_softening_km < 0.0 || config.n_radius < 2 || config.n_theta < 2 ||
        config.n_phi < 2 || config.rlogmax <= config.rlogmin) {
        return false;
    }

    mge_ = mge;
    halo_ = halo;
    black_hole_mass_ = black_hole_mass;
    black_hole_softening_km_ = black_hole_softening_km;
    n_radius_ = config.n_radius;
    n_theta_ = config.n_theta;
    n_phi_ = config.n_phi;
    inner_fallback_count_ = 0;
    outer_fallback_count_ = 0;

    const double min_sigobs = *std::min_element(mge_.sigobs_km.begin(), mge_.sigobs_km.end());
    const double max_sigintr = *std::max_element(mge_.sigintr_km.begin(), mge_.sigintr_km.end());
    metadata_.rmin2 = (min_sigobs / 10.0) * (min_sigobs / 10.0);
    metadata_.rmax2 = (max_sigintr * 6.0) * (max_sigintr * 6.0);
    const double orbit_rmin = std::pow(10.0, config.rlogmin) * 0.01;
    const double orbit_rmax = std::pow(10.0, config.rlogmax) * 1.05;
    metadata_.rmin2 = std::min(orbit_rmin * orbit_rmin, metadata_.rmin2);
    metadata_.rmax2 = std::max(orbit_rmax * orbit_rmax, metadata_.rmax2 * 2.0);
    metadata_.rlog_min = std::log10(std::sqrt(metadata_.rmin2));
    const double rlog_max = std::log10(std::sqrt(metadata_.rmax2));
    metadata_.theta_step = kPiOver2 / static_cast<double>(n_theta_ - 1);
    metadata_.phi_step = kPiOver2 / static_cast<double>(n_phi_ - 1);
    metadata_.rlog_step = (rlog_max - metadata_.rlog_min) / static_cast<double>(n_radius_ - 1);

    grid_.assign(static_cast<std::size_t>(3 * n_phi_ * n_theta_ * n_radius_), kLogTiny);
    const double tiny = std::numeric_limits<double>::min();

    for (int radius_index = 0; radius_index < n_radius_; ++radius_index) {
        const double radius = std::pow(10.0, metadata_.rlog_min + radius_index * metadata_.rlog_step);
        for (int theta_index = 0; theta_index < n_theta_; ++theta_index) {
            double theta = theta_index * metadata_.theta_step;
            if (theta_index == 0) {
                theta = 0.5 * metadata_.theta_step;
            }
            if (theta_index == n_theta_ - 1) {
                theta = (static_cast<double>(n_theta_) - 1.1) * metadata_.theta_step;
            }
            const double sin_theta = std::sin(theta);
            const double z = radius * std::cos(theta);
            for (int phi_index = 0; phi_index < n_phi_; ++phi_index) {
                double phi = phi_index * metadata_.phi_step;
                if (phi_index == 0) {
                    phi = 0.5 * metadata_.phi_step;
                }
                if (phi_index == n_phi_ - 1) {
                    phi = (static_cast<double>(n_phi_) - 1.1) * metadata_.phi_step;
                }
                const double x = radius * sin_theta * std::cos(phi);
                const double y = radius * sin_theta * std::sin(phi);
                double accel_x = 0.0;
                double accel_y = 0.0;
                double accel_z = 0.0;
                if (!evaluate_direct_acceleration(x, y, z, accel_x, accel_y, accel_z)) {
                    return false;
                }
                if (-accel_x > tiny * x) {
                    grid_[grid_index(0, phi_index, theta_index, radius_index)] =
                        std::log(-accel_x / x);
                }
                if (-accel_y > tiny * y) {
                    grid_[grid_index(1, phi_index, theta_index, radius_index)] =
                        std::log(-accel_y / y);
                }
                if (-accel_z > tiny * z) {
                    grid_[grid_index(2, phi_index, theta_index, radius_index)] =
                        std::log(-accel_z / z);
                }
            }
        }
    }
    return true;
}

bool InterpolatedPotential::evaluate_potential(
    double x,
    double y,
    double z,
    double& potential
) const noexcept {
    double accel_x = 0.0;
    double accel_y = 0.0;
    double accel_z = 0.0;
    return evaluate_potential_stack(
        mge_,
        halo_,
        black_hole_mass_,
        black_hole_softening_km_,
        x,
        y,
        z,
        potential,
        accel_x,
        accel_y,
        accel_z
    );
}

bool InterpolatedPotential::evaluate_acceleration(
    double x,
    double y,
    double z,
    double& accel_x,
    double& accel_y,
    double& accel_z
) noexcept {
    const double radius_squared = x * x + y * y + z * z;
    if (radius_squared <= metadata_.rmin2 || radius_squared >= metadata_.rmax2) {
        if (radius_squared < metadata_.rmin2) {
            inner_fallback_count_ += 1;
        }
        if (radius_squared > metadata_.rmax2) {
            outer_fallback_count_ += 1;
        }
        return evaluate_direct_acceleration(x, y, z, accel_x, accel_y, accel_z);
    }

    const double theta = std::atan2(std::sqrt(x * x + y * y), std::abs(z));
    const double phi = std::atan2(std::abs(y), std::abs(x));
    const double rlog = 0.5 * std::log10(radius_squared);
    const double theta_scaled = theta / metadata_.theta_step;
    const double phi_scaled = phi / metadata_.phi_step;
    const double radius_scaled = (rlog - metadata_.rlog_min) / metadata_.rlog_step;
    const int theta_index = static_cast<int>(std::floor(theta_scaled));
    const int phi_index = static_cast<int>(std::floor(phi_scaled));
    const int radius_index = static_cast<int>(std::floor(radius_scaled));

    if (theta_index < 0 || phi_index < 0 || radius_index < 0 ||
        theta_index + 1 >= n_theta_ || phi_index + 1 >= n_phi_ ||
        radius_index + 1 >= n_radius_) {
        return evaluate_direct_acceleration(x, y, z, accel_x, accel_y, accel_z);
    }

    const double tf = theta_scaled - std::floor(theta_scaled);
    const double pf = phi_scaled - std::floor(phi_scaled);
    const double rf = radius_scaled - std::floor(radius_scaled);
    const double one_minus_tf = 1.0 - tf;
    const double one_minus_pf = 1.0 - pf;
    const double one_minus_rf = 1.0 - rf;

    double acc[3] = {0.0, 0.0, 0.0};
    for (int component = 0; component < 3; ++component) {
        acc[component] =
            one_minus_pf * one_minus_tf * one_minus_rf *
                grid_[grid_index(component, phi_index, theta_index, radius_index)] +
            one_minus_pf * one_minus_tf * rf *
                grid_[grid_index(component, phi_index, theta_index, radius_index + 1)] +
            one_minus_pf * tf * rf *
                grid_[grid_index(component, phi_index, theta_index + 1, radius_index + 1)] +
            one_minus_pf * tf * one_minus_rf *
                grid_[grid_index(component, phi_index, theta_index + 1, radius_index)] +
            pf * one_minus_tf * one_minus_rf *
                grid_[grid_index(component, phi_index + 1, theta_index, radius_index)] +
            pf * one_minus_tf * rf *
                grid_[grid_index(component, phi_index + 1, theta_index, radius_index + 1)] +
            pf * tf * rf *
                grid_[grid_index(component, phi_index + 1, theta_index + 1, radius_index + 1)] +
            pf * tf * one_minus_rf *
                grid_[grid_index(component, phi_index + 1, theta_index + 1, radius_index)];
    }

    accel_x = -x * std::exp(acc[0]);
    accel_y = -y * std::exp(acc[1]);
    accel_z = -z * std::exp(acc[2]);
    return true;
}

std::size_t InterpolatedPotential::grid_index(
    int component,
    int phi,
    int theta,
    int radius
) const noexcept {
    return static_cast<std::size_t>(
        (((radius * n_theta_ + theta) * n_phi_ + phi) * 3) + component
    );
}

bool InterpolatedPotential::evaluate_direct_acceleration(
    double x,
    double y,
    double z,
    double& accel_x,
    double& accel_y,
    double& accel_z
) const noexcept {
    return evaluate_potential_stack_acceleration(
        mge_,
        halo_,
        black_hole_mass_,
        black_hole_softening_km_,
        x,
        y,
        z,
        accel_x,
        accel_y,
        accel_z
    );
}

}  // namespace dynamite::orblib_cpp
