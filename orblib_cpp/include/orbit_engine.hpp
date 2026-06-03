#pragma once

namespace dynamite::orblib_cpp {

struct OrblibDirectInput {
    int random_seed = 0;
    int ngauss = 0;
    const double* surf_pc = nullptr;
    const double* sigobs_arcsec = nullptr;
    const double* qobs = nullptr;
    const double* psi_obs_degrees = nullptr;
    double distance_mpc = 0.0;
    double theta_degrees = 0.0;
    double phi_degrees = 0.0;
    double psi_view_degrees = 0.0;
    double upsilon = 0.0;
    double black_hole_mass = 0.0;
    double black_hole_softening_arcsec = 0.0;
    int nener = 0;
    double rlogmin_arcsec = 0.0;
    double rlogmax_arcsec = 0.0;
    int ni2 = 0;
    int ni3 = 0;
    int orbit_dithering = 0;
    int n_radius = 0;
    int n_theta = 0;
    int n_phi = 0;
    int dark_halo_profile_type = 0;
    int dark_halo_parameter_count = 0;
    const double* dark_halo_parameters = nullptr;
    int begin_rows = 0;
    const double* begin_values = nullptr;
    const int* begin_noreg = nullptr;
    double orbital_periods = 0.0;
    int sampling = 0;
    int starting_orbit = 0;
    int number_orbits = 0;
    double accuracy = 0.0;
    int psf_count = 0;
    int max_psf_gauss = 0;
    const int* psf_kind = nullptr;
    const double* psf_weight = nullptr;
    const double* psf_sigma = nullptr;
    int aperture_count = 0;
    const double* ap_begin = nullptr;
    const double* ap_size = nullptr;
    const double* ap_rot = nullptr;
    const int* ap_binx = nullptr;
    const int* ap_biny = nullptr;
    const int* ap_psf = nullptr;
    const int* ap_hist_dim = nullptr;
    const double* hist_width = nullptr;
    const double* hist_center = nullptr;
    const int* hist_bins = nullptr;
    int max_bin_size = 0;
    const int* bin_type = nullptr;
    const int* bin_size = nullptr;
    const int* bin_order = nullptr;
    const char* out_qgrid_path = nullptr;
    const char* out_pops_path = nullptr;
    const char* out_losvd_path = nullptr;
    const char* out_orbclass_path = nullptr;
};

int run_orblib_direct_generation(const OrblibDirectInput& input) noexcept;

}  // namespace dynamite::orblib_cpp
