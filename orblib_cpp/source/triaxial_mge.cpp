#include "triaxial_mge.hpp"

#include "elliptic_integrals.hpp"

#include <algorithm>
#include <cmath>

namespace dynamite::orblib_cpp {
namespace {

constexpr double kPi = 3.141592653589793238462643383279502884197;
constexpr double kTwoPi = 6.283185307179586476925286766559005768394;
constexpr double kGravConstKm = 6.67428e-11 * 1.98892e30 / 1.0e9;
constexpr double kParsecKm = 1.4959787068e8 * (648.0e3 / kPi);
constexpr double kInnerApprox = 0.0001;
constexpr double kOuterApprox = 300.0;

double degrees_to_radians(double value) noexcept {
    return value * (kPi / 180.0);
}

void resize_setup(TriaxialMgeSetup& setup, int ngauss) {
    const auto size = static_cast<std::size_t>(ngauss);
    setup.surf_km.assign(size, 0.0);
    setup.sigobs_km.assign(size, 0.0);
    setup.psi_obs_rad.assign(size, 0.0);
    setup.pintr.assign(size, 0.0);
    setup.qintr.assign(size, 0.0);
    setup.sigintr_km.assign(size, 0.0);
    setup.density.assign(size, 0.0);
    setup.v0.assign(size, 0.0);
    setup.triaxiality.assign(size, 0.0);
    setup.a1.assign(size, 0.0);
    setup.a2.assign(size, 0.0);
    setup.a3.assign(size, 0.0);
    setup.elliptic_f.assign(size, 0.0);
}

template <typename F>
double simpson(double a, double b, double fa, double fm, double fb) noexcept {
    return (b - a) * (fa + 4.0 * fm + fb) / 6.0;
}

template <typename F>
double adaptive_simpson(
    const F& function,
    double a,
    double b,
    double fa,
    double fm,
    double fb,
    double whole,
    double tolerance,
    int depth
) noexcept {
    const double center = 0.5 * (a + b);
    const double left_mid = 0.5 * (a + center);
    const double right_mid = 0.5 * (center + b);
    const double f_left_mid = function(left_mid);
    const double f_right_mid = function(right_mid);
    const double left = simpson<F>(a, center, fa, f_left_mid, fm);
    const double right = simpson<F>(center, b, fm, f_right_mid, fb);
    const double delta = left + right - whole;
    if (depth <= 0 || std::abs(delta) <= 15.0 * tolerance) {
        return left + right + delta / 15.0;
    }
    return adaptive_simpson(
               function,
               a,
               center,
               fa,
               f_left_mid,
               fm,
               left,
               0.5 * tolerance,
               depth - 1
           ) +
           adaptive_simpson(
               function,
               center,
               b,
               fm,
               f_right_mid,
               fb,
               right,
               0.5 * tolerance,
               depth - 1
           );
}

template <typename F>
double integrate_unit_interval(const F& function) noexcept {
    const double a = 0.0;
    const double b = 1.0;
    const double mid = 0.5;
    const double fa = function(a);
    const double fm = function(mid);
    const double fb = function(b);
    const double whole = simpson<F>(a, b, fa, fm, fb);
    const double tolerance = std::max(1.0e-30, std::abs(whole) * 1.0e-12);
    return adaptive_simpson(function, a, b, fa, fm, fb, whole, tolerance, 40);
}

void gaussian_inner_potential_acceleration(
    const TriaxialMgeSetup& setup,
    std::size_t index,
    double x,
    double y,
    double z,
    double& potential,
    double& accel_x,
    double& accel_y,
    double& accel_z
) noexcept {
    const double p = setup.pintr[index];
    const double q = setup.qintr[index];
    const double sigma = setup.sigintr_km[index];
    const double sigma2 = sigma * sigma;
    const double sigma4 = sigma2 * sigma2;
    const double p2 = p * p;
    const double q2 = q * q;
    const double x2 = x * x;
    const double y2 = y * y;
    const double z2 = z * z;
    const double a1 = setup.a1[index];
    const double a2 = setup.a2[index];
    const double a3 = setup.a3[index];

    const double a12 = -(a1 - a2) / (1.0 - p2);
    const double a23 = -(a2 - a3) / (p2 - q2);
    const double a31 = -(a3 - a1) / (q2 - 1.0);
    const double a11 = (1.0 / 3.0) * (2.0 - a12 - a31);
    const double a22 = (1.0 / 3.0) * (2.0 / p2 - a23 - a12);
    const double a33 = (1.0 / 3.0) * (2.0 / q2 - a31 - a23);
    const double scale = setup.v0[index] / std::sqrt(1.0 - q2);

    const double o1 = -0.5 / sigma2 * (a1 * x2 + a2 * y2 + a3 * z2);
    const double o2 = 0.125 / sigma4 *
                      (a11 * x2 * x2 + a22 * y2 * y2 + a33 * z2 * z2 +
                       2.0 * a12 * x2 * y2 + 2.0 * a23 * y2 * z2 + 2.0 * a31 * z2 * x2);
    potential = scale * (setup.elliptic_f[index] + o1 + o2);

    accel_x = -scale * x / sigma2 *
              (a1 - 0.5 / sigma2 * (a11 * x2 + a12 * y2 + a31 * z2));
    accel_y = -scale * y / sigma2 *
              (a2 - 0.5 / sigma2 * (a12 * x2 + a22 * y2 + a23 * z2));
    accel_z = -scale * z / sigma2 *
              (a3 - 0.5 / sigma2 * (a31 * x2 + a23 * y2 + a33 * z2));
}

void gaussian_mid_potential_acceleration(
    const TriaxialMgeSetup& setup,
    std::size_t index,
    double x,
    double y,
    double z,
    double& potential,
    double& accel_x,
    double& accel_y,
    double& accel_z
) noexcept {
    const double p = setup.pintr[index];
    const double q = setup.qintr[index];
    const double sigma = setup.sigintr_km[index];
    const double sigma2 = sigma * sigma;
    const double p_factor = 1.0 - p * p;
    const double q_factor = 1.0 - q * q;
    const double x2 = x * x;
    const double y2 = y * y;
    const double z2 = z * z;
    const auto common = [&](double t, double& d, double& e, double& exponent) noexcept {
        const double t2 = t * t;
        d = 1.0 - p_factor * t2;
        e = 1.0 - q_factor * t2;
        exponent = std::exp(-t2 / (2.0 * sigma2) * (x2 + y2 / d + z2 / e));
    };

    const double potential_integral = integrate_unit_interval([&](double t) noexcept {
        double d = 0.0;
        double e = 0.0;
        double exponent = 0.0;
        common(t, d, e, exponent);
        return exponent / std::sqrt(d * e);
    });
    const double ax_integral = integrate_unit_interval([&](double t) noexcept {
        double d = 0.0;
        double e = 0.0;
        double exponent = 0.0;
        const double t2 = t * t;
        common(t, d, e, exponent);
        return -x / sigma2 * t2 * exponent / std::sqrt(d * e);
    });
    const double ay_integral = integrate_unit_interval([&](double t) noexcept {
        double d = 0.0;
        double e = 0.0;
        double exponent = 0.0;
        const double t2 = t * t;
        common(t, d, e, exponent);
        return -y / sigma2 * t2 / d * exponent / std::sqrt(d * e);
    });
    const double az_integral = integrate_unit_interval([&](double t) noexcept {
        double d = 0.0;
        double e = 0.0;
        double exponent = 0.0;
        const double t2 = t * t;
        common(t, d, e, exponent);
        return -z / sigma2 * t2 / e * exponent / std::sqrt(d * e);
    });

    potential = setup.v0[index] * potential_integral;
    accel_x = setup.v0[index] * ax_integral;
    accel_y = setup.v0[index] * ay_integral;
    accel_z = setup.v0[index] * az_integral;
}

void gaussian_outer_potential_acceleration(
    const TriaxialMgeSetup& setup,
    std::size_t index,
    double x,
    double y,
    double z,
    double radius_squared,
    double& potential,
    double& accel_x,
    double& accel_y,
    double& accel_z
) noexcept {
    const double radius = std::sqrt(radius_squared);
    const double scale = std::sqrt(kPi / 2.0) * setup.sigintr_km[index] * setup.v0[index];
    potential = scale / radius;
    const double accel_scale = -scale / (radius_squared * radius);
    accel_x = x * accel_scale;
    accel_y = y * accel_scale;
    accel_z = z * accel_scale;
}

}  // namespace

bool setup_triaxial_mge_from_observed(
    int ngauss,
    const double* surf_pc,
    const double* sigobs_arcsec,
    const double* qobs,
    const double* psi_obs_degrees,
    double distance_mpc,
    double theta_degrees,
    double phi_degrees,
    double psi_view_degrees,
    double upsilon,
    TriaxialMgeSetup& setup
) noexcept {
    if (ngauss <= 0 || surf_pc == nullptr || sigobs_arcsec == nullptr || qobs == nullptr ||
        psi_obs_degrees == nullptr || distance_mpc <= 0.0) {
        return false;
    }

    resize_setup(setup, ngauss);

    const double theta = degrees_to_radians(theta_degrees);
    const double phi = degrees_to_radians(phi_degrees);
    const double psi_view = degrees_to_radians(psi_view_degrees);
    const double sin_theta = std::sin(theta);
    const double cos_theta = std::cos(theta);
    const double cos_phi = std::cos(phi);
    const double tan_phi = std::tan(phi);
    if (sin_theta == 0.0 || cos_theta == 0.0 || tan_phi == 0.0 || cos_phi == 0.0) {
        return false;
    }
    const double sec_theta = 1.0 / cos_theta;
    const double cot_phi = 1.0 / tan_phi;

    setup.conversion_factor = distance_mpc * 1.0e6 * std::tan(kPi / 648.0e3) * kParsecKm;
    setup.total_mass = 0.0;

    for (int i = 0; i < ngauss; ++i) {
        const auto idx = static_cast<std::size_t>(i);
        if (qobs[i] <= 0.0 || sigobs_arcsec[i] <= 0.0) {
            return false;
        }
        setup.surf_km[idx] = surf_pc[i] / (kParsecKm * kParsecKm) * upsilon;
        setup.sigobs_km[idx] = sigobs_arcsec[i] * setup.conversion_factor;
        setup.psi_obs_rad[idx] = degrees_to_radians(psi_obs_degrees[i]) + psi_view;
        setup.total_mass += setup.surf_km[idx] * qobs[i] * setup.sigobs_km[idx] * setup.sigobs_km[idx];
    }
    setup.total_mass *= kTwoPi;

    for (int i = 0; i < ngauss; ++i) {
        const auto idx = static_cast<std::size_t>(i);
        const double psi = setup.psi_obs_rad[idx];
        const double delp = 1.0 - qobs[i] * qobs[i];
        const double nom1minq2 =
            delp * (2.0 * std::cos(2.0 * psi) +
                    std::sin(2.0 * psi) * (sec_theta * cot_phi - cos_theta * tan_phi));
        const double nomp2minq2 =
            delp * (2.0 * std::cos(2.0 * psi) +
                    std::sin(2.0 * psi) * (cos_theta * cot_phi - sec_theta * tan_phi));
        const double denom =
            2.0 * sin_theta * sin_theta *
            (delp * std::cos(psi) * (std::cos(psi) + sec_theta * cot_phi * std::sin(psi)) - 1.0);
        if (denom == 0.0) {
            return false;
        }

        const double qintr_squared = 1.0 - nom1minq2 / denom;
        const double pintr_squared = qintr_squared + nomp2minq2 / denom;
        if (qintr_squared < 0.0 || pintr_squared < 0.0) {
            return false;
        }

        const double qintr = std::sqrt(qintr_squared);
        const double pintr = std::sqrt(pintr_squared);
        if (qintr > pintr || pintr > 1.0) {
            return false;
        }

        const double triaxiality = (1.0 - pintr * pintr) / (1.0 - qintr * qintr);
        if (triaxiality < 0.0 || triaxiality > 1.0) {
            return false;
        }

        const double sigma_intrinsic =
            setup.sigobs_km[idx] *
            std::sqrt(qobs[i] /
                      std::sqrt((pintr * cos_theta) * (pintr * cos_theta) +
                                (qintr * sin_theta) * (qintr * sin_theta) *
                                    ((pintr * cos_phi) * (pintr * cos_phi) +
                                     std::sin(phi) * std::sin(phi))));

        const double density =
            setup.surf_km[idx] * qobs[i] * setup.sigobs_km[idx] * setup.sigobs_km[idx] /
            (std::sqrt(kTwoPi) * pintr * qintr * sigma_intrinsic * sigma_intrinsic * sigma_intrinsic);
        const double v0 =
            4.0 * kPi * kGravConstKm * sigma_intrinsic * sigma_intrinsic * pintr * qintr * density;

        const double modulus = std::sqrt((1.0 - pintr * pintr) / (1.0 - qintr * qintr));
        const double amplitude = std::acos(qintr);
        double value_f = 0.0;
        double value_e = 0.0;
        if (!elliptic_f(amplitude, modulus, value_f) || !elliptic_e(amplitude, modulus, value_e)) {
            return false;
        }
        const double a1 = (value_f - value_e) / (1.0 - pintr * pintr);
        const double a2 =
            ((1.0 - qintr * qintr) * value_e - (pintr * pintr - qintr * qintr) * value_f -
             (qintr / pintr) * (1.0 - pintr * pintr) * std::sqrt(1.0 - qintr * qintr)) /
            ((1.0 - pintr * pintr) * (pintr * pintr - qintr * qintr));
        const double a3 =
            ((pintr / qintr) * std::sqrt(1.0 - qintr * qintr) - value_e) /
            (pintr * pintr - qintr * qintr);

        setup.pintr[idx] = pintr;
        setup.qintr[idx] = qintr;
        setup.sigintr_km[idx] = sigma_intrinsic;
        setup.density[idx] = density;
        setup.v0[idx] = v0;
        setup.triaxiality[idx] = triaxiality;
        setup.a1[idx] = a1;
        setup.a2[idx] = a2;
        setup.a3[idx] = a3;
        setup.elliptic_f[idx] = value_f;
    }

    return true;
}

bool evaluate_triaxial_mge(
    const TriaxialMgeSetup& setup,
    double x,
    double y,
    double z,
    double& potential,
    double& accel_x,
    double& accel_y,
    double& accel_z
) noexcept {
    const std::size_t ngauss = setup.sigintr_km.size();
    if (ngauss == 0 || setup.pintr.size() != ngauss || setup.qintr.size() != ngauss ||
        setup.v0.size() != ngauss || setup.a1.size() != ngauss || setup.a2.size() != ngauss ||
        setup.a3.size() != ngauss || setup.elliptic_f.size() != ngauss) {
        return false;
    }

    potential = 0.0;
    accel_x = 0.0;
    accel_y = 0.0;
    accel_z = 0.0;
    const double radius_squared = x * x + y * y + z * z;

    for (std::size_t i = 0; i < ngauss; ++i) {
        const double sigma = setup.sigintr_km[i];
        double one_potential = 0.0;
        double one_ax = 0.0;
        double one_ay = 0.0;
        double one_az = 0.0;
        const double inner_limit = kInnerApprox * sigma;
        const double outer_limit = kOuterApprox * sigma;
        if (radius_squared < inner_limit * inner_limit) {
            gaussian_inner_potential_acceleration(
                setup,
                i,
                x,
                y,
                z,
                one_potential,
                one_ax,
                one_ay,
                one_az
            );
        } else if (radius_squared < outer_limit * outer_limit) {
            gaussian_mid_potential_acceleration(
                setup,
                i,
                x,
                y,
                z,
                one_potential,
                one_ax,
                one_ay,
                one_az
            );
        } else {
            gaussian_outer_potential_acceleration(
                setup,
                i,
                x,
                y,
                z,
                radius_squared,
                one_potential,
                one_ax,
                one_ay,
                one_az
            );
        }

        potential += one_potential;
        accel_x += one_ax;
        accel_y += one_ay;
        accel_z += one_az;
    }

    return true;
}

}  // namespace dynamite::orblib_cpp
