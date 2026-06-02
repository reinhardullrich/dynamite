#include "triaxial_mge.hpp"

#include "elliptic_integrals.hpp"

#include <cmath>

namespace dynamite::orblib_cpp {
namespace {

constexpr double kPi = 3.141592653589793238462643383279502884197;
constexpr double kTwoPi = 6.283185307179586476925286766559005768394;
constexpr double kGravConstKm = 6.67428e-11 * 1.98892e30 / 1.0e9;
constexpr double kParsecKm = 1.4959787068e8 * (648.0e3 / kPi);

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

}  // namespace dynamite::orblib_cpp
