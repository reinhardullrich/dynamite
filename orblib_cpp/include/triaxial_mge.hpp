#pragma once

#include <vector>

namespace dynamite::orblib_cpp {

struct TriaxialMgeSetup {
    double conversion_factor = 0.0;
    double total_mass = 0.0;
    std::vector<double> surf_km;
    std::vector<double> sigobs_km;
    std::vector<double> psi_obs_rad;
    std::vector<double> pintr;
    std::vector<double> qintr;
    std::vector<double> sigintr_km;
    std::vector<double> density;
    std::vector<double> v0;
    std::vector<double> triaxiality;
    std::vector<double> a1;
    std::vector<double> a2;
    std::vector<double> a3;
    std::vector<double> elliptic_f;
};

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
) noexcept;

}  // namespace dynamite::orblib_cpp
