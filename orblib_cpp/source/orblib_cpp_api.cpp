#include "dop853.hpp"
#include "elliptic_integrals.hpp"
#include "interpolated_potential.hpp"
#include "orbit_aperture.hpp"
#include "orbit_classification.hpp"
#include "orbit_histogram.hpp"
#include "orbit_integrator.hpp"
#include "orbit_output.hpp"
#include "orbit_projection.hpp"
#include "orbit_psf.hpp"
#include "orbit_qgrid.hpp"
#include "orbit_rhs.hpp"
#include "orbit_start.hpp"
#include "potential.hpp"
#include "ran1.hpp"
#include "triaxial_mge.hpp"

#include <algorithm>
#include <cstddef>
#include <cmath>
#include <limits>
#include <vector>

namespace {

constexpr int kAbiVersion = 1;
constexpr int kStatusOk = 0;
constexpr int kStatusInvalidArgument = -1;
constexpr int kStatusIoError = -2;
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

extern "C" void orblib_cpp_api_elliptic_legendre(
    double phi,
    double modulus,
    double* value_f,
    double* value_e,
    int* status
) noexcept {
    if (value_f == nullptr || value_e == nullptr) {
        set_status(status, kStatusInvalidArgument);
        return;
    }

    double result_f = 0.0;
    double result_e = 0.0;
    if (!dynamite::orblib_cpp::elliptic_f(phi, modulus, result_f) ||
        !dynamite::orblib_cpp::elliptic_e(phi, modulus, result_e)) {
        set_status(status, kStatusInvalidArgument);
        return;
    }

    *value_f = result_f;
    *value_e = result_e;
    set_status(status, kStatusOk);
}

extern "C" void orblib_cpp_api_triaxial_mge_setup(
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
    double* pintr,
    double* qintr,
    double* sigintr_km,
    double* density,
    double* v0,
    double* triaxiality,
    double* total_mass,
    int* status
) noexcept {
    if (ngauss <= 0 || surf_pc == nullptr || sigobs_arcsec == nullptr || qobs == nullptr ||
        psi_obs_degrees == nullptr || pintr == nullptr || qintr == nullptr || sigintr_km == nullptr ||
        density == nullptr || v0 == nullptr || triaxiality == nullptr || total_mass == nullptr) {
        set_status(status, kStatusInvalidArgument);
        return;
    }

    try {
        dynamite::orblib_cpp::TriaxialMgeSetup setup;
        if (!dynamite::orblib_cpp::setup_triaxial_mge_from_observed(
                ngauss,
                surf_pc,
                sigobs_arcsec,
                qobs,
                psi_obs_degrees,
                distance_mpc,
                theta_degrees,
                phi_degrees,
                psi_view_degrees,
                upsilon,
                setup
            )) {
            set_status(status, kStatusInvalidArgument);
            return;
        }

        for (int i = 0; i < ngauss; ++i) {
            const auto idx = static_cast<std::size_t>(i);
            pintr[i] = setup.pintr[idx];
            qintr[i] = setup.qintr[idx];
            sigintr_km[i] = setup.sigintr_km[idx];
            density[i] = setup.density[idx];
            v0[i] = setup.v0[idx];
            triaxiality[i] = setup.triaxiality[idx];
        }
        *total_mass = setup.total_mass;
        set_status(status, kStatusOk);
    } catch (...) {
        set_status(status, kStatusException);
    }
}

extern "C" void orblib_cpp_api_triaxial_mge_evaluate(
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
    int point_count,
    const double* point_x,
    const double* point_y,
    const double* point_z,
    double* potential,
    double* accel_x,
    double* accel_y,
    double* accel_z,
    int* status
) noexcept {
    if (ngauss <= 0 || surf_pc == nullptr || sigobs_arcsec == nullptr || qobs == nullptr ||
        psi_obs_degrees == nullptr || point_count < 0 ||
        (point_count > 0 &&
         (point_x == nullptr || point_y == nullptr || point_z == nullptr || potential == nullptr ||
          accel_x == nullptr || accel_y == nullptr || accel_z == nullptr))) {
        set_status(status, kStatusInvalidArgument);
        return;
    }

    try {
        dynamite::orblib_cpp::TriaxialMgeSetup setup;
        if (!dynamite::orblib_cpp::setup_triaxial_mge_from_observed(
                ngauss,
                surf_pc,
                sigobs_arcsec,
                qobs,
                psi_obs_degrees,
                distance_mpc,
                theta_degrees,
                phi_degrees,
                psi_view_degrees,
                upsilon,
                setup
            )) {
            set_status(status, kStatusInvalidArgument);
            return;
        }

        for (int i = 0; i < point_count; ++i) {
            if (!dynamite::orblib_cpp::evaluate_triaxial_mge(
                    setup,
                    point_x[i],
                    point_y[i],
                    point_z[i],
                    potential[i],
                    accel_x[i],
                    accel_y[i],
                    accel_z[i]
                )) {
                set_status(status, kStatusInvalidArgument);
                return;
            }
        }
        set_status(status, kStatusOk);
    } catch (...) {
        set_status(status, kStatusException);
    }
}

extern "C" void orblib_cpp_api_potential_stack_evaluate(
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
    double black_hole_mass,
    double black_hole_softening_arcsec,
    int dark_halo_profile_type,
    int dark_halo_parameter_count,
    const double* dark_halo_parameters,
    int point_count,
    const double* point_x,
    const double* point_y,
    const double* point_z,
    double* potential,
    double* accel_x,
    double* accel_y,
    double* accel_z,
    int* status
) noexcept {
    if (ngauss <= 0 || surf_pc == nullptr || sigobs_arcsec == nullptr || qobs == nullptr ||
        psi_obs_degrees == nullptr || black_hole_mass < 0.0 ||
        black_hole_softening_arcsec < 0.0 || dark_halo_parameter_count < 0 ||
        (dark_halo_parameter_count > 0 && dark_halo_parameters == nullptr) ||
        point_count < 0 ||
        (point_count > 0 &&
         (point_x == nullptr || point_y == nullptr || point_z == nullptr || potential == nullptr ||
          accel_x == nullptr || accel_y == nullptr || accel_z == nullptr))) {
        set_status(status, kStatusInvalidArgument);
        return;
    }

    try {
        dynamite::orblib_cpp::TriaxialMgeSetup mge;
        if (!dynamite::orblib_cpp::setup_triaxial_mge_from_observed(
                ngauss,
                surf_pc,
                sigobs_arcsec,
                qobs,
                psi_obs_degrees,
                distance_mpc,
                theta_degrees,
                phi_degrees,
                psi_view_degrees,
                upsilon,
                mge
            )) {
            set_status(status, kStatusInvalidArgument);
            return;
        }

        dynamite::orblib_cpp::DarkHaloSetup halo;
        if (!dynamite::orblib_cpp::setup_dark_halo(
                dark_halo_profile_type,
                dark_halo_parameter_count,
                dark_halo_parameters,
                mge.total_mass,
                halo
            )) {
            set_status(status, kStatusInvalidArgument);
            return;
        }

        const double black_hole_softening_km = black_hole_softening_arcsec * mge.conversion_factor;
        for (int i = 0; i < point_count; ++i) {
            if (!dynamite::orblib_cpp::evaluate_potential_stack(
                    mge,
                    halo,
                    black_hole_mass,
                    black_hole_softening_km,
                    point_x[i],
                    point_y[i],
                    point_z[i],
                    potential[i],
                    accel_x[i],
                    accel_y[i],
                    accel_z[i]
                )) {
                set_status(status, kStatusInvalidArgument);
                return;
            }
        }
        set_status(status, kStatusOk);
    } catch (...) {
        set_status(status, kStatusException);
    }
}

extern "C" void orblib_cpp_api_interpolated_potential_evaluate(
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
    double black_hole_mass,
    double black_hole_softening_arcsec,
    int dark_halo_profile_type,
    int dark_halo_parameter_count,
    const double* dark_halo_parameters,
    int n_radius,
    int n_theta,
    int n_phi,
    double rlogmin,
    double rlogmax,
    int point_count,
    const double* point_x,
    const double* point_y,
    const double* point_z,
    double* potential,
    double* accel_x,
    double* accel_y,
    double* accel_z,
    double* theta_step,
    double* phi_step,
    double* rlog_step,
    double* rlog_min,
    double* rmin2,
    double* rmax2,
    int* inner_fallback_count,
    int* outer_fallback_count,
    int* status
) noexcept {
    if (ngauss <= 0 || surf_pc == nullptr || sigobs_arcsec == nullptr || qobs == nullptr ||
        psi_obs_degrees == nullptr || black_hole_mass < 0.0 ||
        black_hole_softening_arcsec < 0.0 || dark_halo_parameter_count < 0 ||
        (dark_halo_parameter_count > 0 && dark_halo_parameters == nullptr) ||
        n_radius < 2 || n_theta < 2 || n_phi < 2 || rlogmax <= rlogmin ||
        point_count < 0 || theta_step == nullptr || phi_step == nullptr ||
        rlog_step == nullptr || rlog_min == nullptr || rmin2 == nullptr ||
        rmax2 == nullptr || inner_fallback_count == nullptr ||
        outer_fallback_count == nullptr ||
        (point_count > 0 &&
         (point_x == nullptr || point_y == nullptr || point_z == nullptr || potential == nullptr ||
          accel_x == nullptr || accel_y == nullptr || accel_z == nullptr))) {
        set_status(status, kStatusInvalidArgument);
        return;
    }

    try {
        dynamite::orblib_cpp::TriaxialMgeSetup mge;
        if (!dynamite::orblib_cpp::setup_triaxial_mge_from_observed(
                ngauss,
                surf_pc,
                sigobs_arcsec,
                qobs,
                psi_obs_degrees,
                distance_mpc,
                theta_degrees,
                phi_degrees,
                psi_view_degrees,
                upsilon,
                mge
            )) {
            set_status(status, kStatusInvalidArgument);
            return;
        }

        dynamite::orblib_cpp::DarkHaloSetup halo;
        if (!dynamite::orblib_cpp::setup_dark_halo(
                dark_halo_profile_type,
                dark_halo_parameter_count,
                dark_halo_parameters,
                mge.total_mass,
                halo
            )) {
            set_status(status, kStatusInvalidArgument);
            return;
        }

        dynamite::orblib_cpp::InterpolationGridConfig config;
        config.n_radius = n_radius;
        config.n_theta = n_theta;
        config.n_phi = n_phi;
        config.rlogmin = rlogmin;
        config.rlogmax = rlogmax;

        dynamite::orblib_cpp::InterpolatedPotential interpolated;
        if (!interpolated.setup(
                mge,
                halo,
                black_hole_mass,
                black_hole_softening_arcsec * mge.conversion_factor,
                config
            )) {
            set_status(status, kStatusInvalidArgument);
            return;
        }

        for (int i = 0; i < point_count; ++i) {
            if (!interpolated.evaluate_potential(point_x[i], point_y[i], point_z[i], potential[i]) ||
                !interpolated.evaluate_acceleration(
                    point_x[i],
                    point_y[i],
                    point_z[i],
                    accel_x[i],
                    accel_y[i],
                    accel_z[i]
                )) {
                set_status(status, kStatusInvalidArgument);
                return;
            }
        }

        const auto& metadata = interpolated.metadata();
        *theta_step = metadata.theta_step;
        *phi_step = metadata.phi_step;
        *rlog_step = metadata.rlog_step;
        *rlog_min = metadata.rlog_min;
        *rmin2 = metadata.rmin2;
        *rmax2 = metadata.rmax2;
        *inner_fallback_count = interpolated.inner_fallback_count();
        *outer_fallback_count = interpolated.outer_fallback_count();
        set_status(status, kStatusOk);
    } catch (...) {
        set_status(status, kStatusException);
    }
}

extern "C" void orblib_cpp_api_orbit_rhs_evaluate(
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
    double black_hole_mass,
    double black_hole_softening_arcsec,
    int dark_halo_profile_type,
    int dark_halo_parameter_count,
    const double* dark_halo_parameters,
    int n_radius,
    int n_theta,
    int n_phi,
    double rlogmin,
    double rlogmax,
    double omega,
    int state_count,
    const double* state_x,
    const double* state_y,
    const double* state_z,
    const double* state_vx,
    const double* state_vy,
    const double* state_vz,
    double* derivative_x,
    double* derivative_y,
    double* derivative_z,
    double* derivative_vx,
    double* derivative_vy,
    double* derivative_vz,
    int* inner_fallback_count,
    int* outer_fallback_count,
    int* status
) noexcept {
    if (ngauss <= 0 || surf_pc == nullptr || sigobs_arcsec == nullptr || qobs == nullptr ||
        psi_obs_degrees == nullptr || black_hole_mass < 0.0 ||
        black_hole_softening_arcsec < 0.0 || dark_halo_parameter_count < 0 ||
        (dark_halo_parameter_count > 0 && dark_halo_parameters == nullptr) ||
        n_radius < 2 || n_theta < 2 || n_phi < 2 || rlogmax <= rlogmin ||
        inner_fallback_count == nullptr || outer_fallback_count == nullptr ||
        state_count < 0 ||
        (state_count > 0 &&
         (state_x == nullptr || state_y == nullptr || state_z == nullptr ||
          state_vx == nullptr || state_vy == nullptr || state_vz == nullptr ||
          derivative_x == nullptr || derivative_y == nullptr || derivative_z == nullptr ||
          derivative_vx == nullptr || derivative_vy == nullptr || derivative_vz == nullptr))) {
        set_status(status, kStatusInvalidArgument);
        return;
    }

    try {
        dynamite::orblib_cpp::TriaxialMgeSetup mge;
        if (!dynamite::orblib_cpp::setup_triaxial_mge_from_observed(
                ngauss,
                surf_pc,
                sigobs_arcsec,
                qobs,
                psi_obs_degrees,
                distance_mpc,
                theta_degrees,
                phi_degrees,
                psi_view_degrees,
                upsilon,
                mge
            )) {
            set_status(status, kStatusInvalidArgument);
            return;
        }

        dynamite::orblib_cpp::DarkHaloSetup halo;
        if (!dynamite::orblib_cpp::setup_dark_halo(
                dark_halo_profile_type,
                dark_halo_parameter_count,
                dark_halo_parameters,
                mge.total_mass,
                halo
            )) {
            set_status(status, kStatusInvalidArgument);
            return;
        }

        dynamite::orblib_cpp::InterpolationGridConfig config;
        config.n_radius = n_radius;
        config.n_theta = n_theta;
        config.n_phi = n_phi;
        config.rlogmin = rlogmin;
        config.rlogmax = rlogmax;

        dynamite::orblib_cpp::InterpolatedPotential interpolated;
        if (!interpolated.setup(
                mge,
                halo,
                black_hole_mass,
                black_hole_softening_arcsec * mge.conversion_factor,
                config
            )) {
            set_status(status, kStatusInvalidArgument);
            return;
        }

        for (int i = 0; i < state_count; ++i) {
            const double state[6] = {
                state_x[i],
                state_y[i],
                state_z[i],
                state_vx[i],
                state_vy[i],
                state_vz[i],
            };
            double derivative[6] = {0.0, 0.0, 0.0, 0.0, 0.0, 0.0};
            if (!dynamite::orblib_cpp::evaluate_orbit_rhs(
                    interpolated,
                    omega,
                    state,
                    derivative
                )) {
                set_status(status, kStatusInvalidArgument);
                return;
            }
            derivative_x[i] = derivative[0];
            derivative_y[i] = derivative[1];
            derivative_z[i] = derivative[2];
            derivative_vx[i] = derivative[3];
            derivative_vy[i] = derivative[4];
            derivative_vz[i] = derivative[5];
        }

        *inner_fallback_count = interpolated.inner_fallback_count();
        *outer_fallback_count = interpolated.outer_fallback_count();
        set_status(status, kStatusOk);
    } catch (...) {
        set_status(status, kStatusException);
    }
}

extern "C" void orblib_cpp_api_classify_orbit_samples(
    int sample_count,
    const double* sample_state_x,
    const double* sample_state_y,
    const double* sample_state_z,
    const double* sample_state_vx,
    const double* sample_state_vy,
    const double* sample_state_vz,
    int* orbit_type,
    double* moments,
    double* moments2,
    int* status
) noexcept {
    if (sample_count <= 0 || sample_state_x == nullptr || sample_state_y == nullptr ||
        sample_state_z == nullptr || sample_state_vx == nullptr || sample_state_vy == nullptr ||
        sample_state_vz == nullptr || orbit_type == nullptr || moments == nullptr ||
        moments2 == nullptr) {
        set_status(status, kStatusInvalidArgument);
        return;
    }

    try {
        dynamite::orblib_cpp::OrbitClassificationResult result;
        if (!dynamite::orblib_cpp::classify_orbit_samples(
                sample_count,
                sample_state_x,
                sample_state_y,
                sample_state_z,
                sample_state_vx,
                sample_state_vy,
                sample_state_vz,
                result
            )) {
            set_status(status, kStatusInvalidArgument);
            return;
        }

        *orbit_type = result.type;
        for (int i = 0; i < 5; ++i) {
            moments[i] = result.moments[i];
        }
        for (int i = 0; i < 3; ++i) {
            moments2[i] = result.moments2[i];
        }
        set_status(status, kStatusOk);
    } catch (...) {
        set_status(status, kStatusException);
    }
}

extern "C" void orblib_cpp_api_project_orbit_samples(
    int orbit_type,
    int projection_number,
    double omega,
    double theta_radians,
    double phi_radians,
    int sample_count,
    const double* sample_state_x,
    const double* sample_state_y,
    const double* sample_state_z,
    const double* sample_state_vx,
    const double* sample_state_vy,
    const double* sample_state_vz,
    double* projected_x,
    double* projected_y,
    double* los_velocity,
    int* status
) noexcept {
    if (sample_count < 0 || sample_state_x == nullptr || sample_state_y == nullptr ||
        sample_state_z == nullptr || sample_state_vx == nullptr || sample_state_vy == nullptr ||
        sample_state_vz == nullptr || projected_x == nullptr || projected_y == nullptr ||
        los_velocity == nullptr) {
        set_status(status, kStatusInvalidArgument);
        return;
    }

    try {
        if (!dynamite::orblib_cpp::project_orbit_samples(
                orbit_type,
                projection_number,
                omega,
                theta_radians,
                phi_radians,
                sample_count,
                sample_state_x,
                sample_state_y,
                sample_state_z,
                sample_state_vx,
                sample_state_vy,
                sample_state_vz,
                projected_x,
                projected_y,
                los_velocity
            )) {
            set_status(status, kStatusInvalidArgument);
            return;
        }
        set_status(status, kStatusOk);
    } catch (...) {
        set_status(status, kStatusException);
    }
}

extern "C" void orblib_cpp_api_apply_psf(
    int gaussian_count,
    const double* weights,
    const double* sigmas,
    double sigma_scale,
    int sample_count,
    const double* projected_x,
    const double* projected_y,
    int seed,
    double* convolved_x,
    double* convolved_y,
    int* status
) noexcept {
    if (gaussian_count < 1 || weights == nullptr || sigmas == nullptr || sample_count < 0 ||
        projected_x == nullptr || projected_y == nullptr || convolved_x == nullptr ||
        convolved_y == nullptr) {
        set_status(status, kStatusInvalidArgument);
        return;
    }

    try {
        if (!dynamite::orblib_cpp::apply_psf_to_projected_samples(
                gaussian_count,
                weights,
                sigmas,
                sigma_scale,
                sample_count,
                projected_x,
                projected_y,
                seed,
                convolved_x,
                convolved_y
            )) {
            set_status(status, kStatusInvalidArgument);
            return;
        }
        set_status(status, kStatusOk);
    } catch (...) {
        set_status(status, kStatusException);
    }
}

extern "C" void orblib_cpp_api_find_boxed_aperture_pixels(
    double begin_x,
    double begin_y,
    double size_x,
    double size_y,
    double rotation_degrees,
    int bins_x,
    int bins_y,
    double psi_radians,
    double coordinate_scale,
    int sample_count,
    const double* projected_x,
    const double* projected_y,
    int* pixels,
    int* status
) noexcept {
    if (sample_count < 0 || projected_x == nullptr || projected_y == nullptr ||
        pixels == nullptr) {
        set_status(status, kStatusInvalidArgument);
        return;
    }

    try {
        if (!dynamite::orblib_cpp::find_boxed_aperture_pixels(
                begin_x,
                begin_y,
                size_x,
                size_y,
                rotation_degrees,
                bins_x,
                bins_y,
                psi_radians,
                coordinate_scale,
                sample_count,
                projected_x,
                projected_y,
                pixels
            )) {
            set_status(status, kStatusInvalidArgument);
            return;
        }
        set_status(status, kStatusOk);
    } catch (...) {
        set_status(status, kStatusException);
    }
}

extern "C" void orblib_cpp_api_losvd_velocity_bins(
    double histogram_width,
    double histogram_center,
    int velocity_bin_count,
    int sample_count,
    const double* los_velocity,
    int* velocity_bins,
    int* status
) noexcept {
    if (sample_count < 0 || los_velocity == nullptr || velocity_bins == nullptr) {
        set_status(status, kStatusInvalidArgument);
        return;
    }

    try {
        if (!dynamite::orblib_cpp::map_losvd_velocity_bins(
                histogram_width,
                histogram_center,
                velocity_bin_count,
                sample_count,
                los_velocity,
                velocity_bins
            )) {
            set_status(status, kStatusInvalidArgument);
            return;
        }
        set_status(status, kStatusOk);
    } catch (...) {
        set_status(status, kStatusException);
    }
}

extern "C" void orblib_cpp_api_accumulate_losvd_histogram(
    int aperture_pixel_count,
    int velocity_bin_count,
    int sample_count,
    const int* aperture_pixels,
    const int* velocity_bins,
    int total_sample_count,
    double* histogram,
    double* stored_count,
    int* status
) noexcept {
    if (sample_count < 0 || aperture_pixels == nullptr || velocity_bins == nullptr ||
        histogram == nullptr || stored_count == nullptr) {
        set_status(status, kStatusInvalidArgument);
        return;
    }

    try {
        if (!dynamite::orblib_cpp::accumulate_losvd_histogram(
                aperture_pixel_count,
                velocity_bin_count,
                sample_count,
                aperture_pixels,
                velocity_bins,
                total_sample_count,
                histogram,
                stored_count
            )) {
            set_status(status, kStatusInvalidArgument);
            return;
        }
        set_status(status, kStatusOk);
    } catch (...) {
        set_status(status, kStatusException);
    }
}

extern "C" void orblib_cpp_api_collapse_losvd_binning(
    int source_pixel_count,
    int velocity_bin_count,
    int target_pixel_count,
    const int* bin_order,
    const double* source_histogram,
    double* target_histogram,
    int* status
) noexcept {
    if (bin_order == nullptr || source_histogram == nullptr || target_histogram == nullptr) {
        set_status(status, kStatusInvalidArgument);
        return;
    }

    try {
        if (!dynamite::orblib_cpp::collapse_losvd_binning(
                source_pixel_count,
                velocity_bin_count,
                target_pixel_count,
                bin_order,
                source_histogram,
                target_histogram
            )) {
            set_status(status, kStatusInvalidArgument);
            return;
        }
        set_status(status, kStatusOk);
    } catch (...) {
        set_status(status, kStatusException);
    }
}

extern "C" void orblib_cpp_api_normalize_losvd_histogram(
    int pixel_count,
    int velocity_bin_count,
    double stored_count,
    double* histogram,
    int* status
) noexcept {
    if (histogram == nullptr) {
        set_status(status, kStatusInvalidArgument);
        return;
    }

    try {
        if (!dynamite::orblib_cpp::normalize_losvd_histogram(
                pixel_count,
                velocity_bin_count,
                stored_count,
                histogram
            )) {
            set_status(status, kStatusInvalidArgument);
            return;
        }
        set_status(status, kStatusOk);
    } catch (...) {
        set_status(status, kStatusException);
    }
}

extern "C" void orblib_cpp_api_sparse_losvd_ranges(
    int pixel_count,
    int velocity_bin_count,
    const double* histogram,
    int* begin_offsets,
    int* end_offsets,
    int* status
) noexcept {
    if (histogram == nullptr || begin_offsets == nullptr || end_offsets == nullptr) {
        set_status(status, kStatusInvalidArgument);
        return;
    }

    try {
        if (!dynamite::orblib_cpp::compute_sparse_losvd_ranges(
                pixel_count,
                velocity_bin_count,
                histogram,
                begin_offsets,
                end_offsets
            )) {
            set_status(status, kStatusInvalidArgument);
            return;
        }
        set_status(status, kStatusOk);
    } catch (...) {
        set_status(status, kStatusException);
    }
}

extern "C" void orblib_cpp_api_qgrid_boundaries(
    int radius_bin_count,
    int theta_bin_count,
    int phi_bin_count,
    double rlogmin,
    double rlogmax,
    int sigma_count,
    const double* sigobs_km,
    double* radius_boundaries,
    double* theta_boundaries,
    double* phi_boundaries,
    int* status
) noexcept {
    if (sigobs_km == nullptr || radius_boundaries == nullptr || theta_boundaries == nullptr ||
        phi_boundaries == nullptr) {
        set_status(status, kStatusInvalidArgument);
        return;
    }

    try {
        if (!dynamite::orblib_cpp::setup_qgrid_boundaries(
                radius_bin_count,
                theta_bin_count,
                phi_bin_count,
                rlogmin,
                rlogmax,
                sigma_count,
                sigobs_km,
                radius_boundaries,
                theta_boundaries,
                phi_boundaries
            )) {
            set_status(status, kStatusInvalidArgument);
            return;
        }
        set_status(status, kStatusOk);
    } catch (...) {
        set_status(status, kStatusException);
    }
}

extern "C" void orblib_cpp_api_accumulate_qgrid(
    int orbit_type,
    double omega,
    int radius_bin_count,
    int theta_bin_count,
    int phi_bin_count,
    const double* radius_boundaries,
    const double* theta_boundaries,
    const double* phi_boundaries,
    int sample_count,
    const double* x,
    const double* y,
    const double* z,
    const double* vx,
    const double* vy,
    const double* vz,
    double* qgrid,
    int* status
) noexcept {
    if (radius_boundaries == nullptr || theta_boundaries == nullptr ||
        phi_boundaries == nullptr || x == nullptr || y == nullptr || z == nullptr ||
        vx == nullptr || vy == nullptr || vz == nullptr || qgrid == nullptr) {
        set_status(status, kStatusInvalidArgument);
        return;
    }

    try {
        if (!dynamite::orblib_cpp::accumulate_qgrid_samples(
                orbit_type,
                omega,
                radius_bin_count,
                theta_bin_count,
                phi_bin_count,
                radius_boundaries,
                theta_boundaries,
                phi_boundaries,
                sample_count,
                x,
                y,
                z,
                vx,
                vy,
                vz,
                qgrid
            )) {
            set_status(status, kStatusInvalidArgument);
            return;
        }
        set_status(status, kStatusOk);
    } catch (...) {
        set_status(status, kStatusException);
    }
}

extern "C" void orblib_cpp_api_normalize_qgrid(
    int radius_bin_count,
    int theta_bin_count,
    int phi_bin_count,
    double* qgrid,
    int* status
) noexcept {
    if (qgrid == nullptr) {
        set_status(status, kStatusInvalidArgument);
        return;
    }

    try {
        if (!dynamite::orblib_cpp::normalize_qgrid(
                radius_bin_count,
                theta_bin_count,
                phi_bin_count,
                qgrid
            )) {
            set_status(status, kStatusInvalidArgument);
            return;
        }
        set_status(status, kStatusOk);
    } catch (...) {
        set_status(status, kStatusException);
    }
}

extern "C" void orblib_cpp_api_integrate_orbit_final_state(
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
    double black_hole_mass,
    double black_hole_softening_arcsec,
    int dark_halo_profile_type,
    int dark_halo_parameter_count,
    const double* dark_halo_parameters,
    int n_radius,
    int n_theta,
    int n_phi,
    double rlogmin,
    double rlogmax,
    double omega,
    double t_start,
    double t_end,
    double rtol,
    double atol,
    int max_steps,
    const double* initial_state,
    double* final_state,
    double* final_time,
    int* function_evaluations,
    int* computed_steps,
    int* accepted_steps,
    int* rejected_steps,
    int* inner_fallback_count,
    int* outer_fallback_count,
    int* status
) noexcept {
    if (ngauss <= 0 || surf_pc == nullptr || sigobs_arcsec == nullptr || qobs == nullptr ||
        psi_obs_degrees == nullptr || black_hole_mass < 0.0 ||
        black_hole_softening_arcsec < 0.0 || dark_halo_parameter_count < 0 ||
        (dark_halo_parameter_count > 0 && dark_halo_parameters == nullptr) ||
        n_radius < 2 || n_theta < 2 || n_phi < 2 || rlogmax <= rlogmin ||
        t_end == t_start || rtol <= 0.0 || atol <= 0.0 || max_steps <= 0 ||
        initial_state == nullptr || final_state == nullptr || final_time == nullptr ||
        function_evaluations == nullptr || computed_steps == nullptr ||
        accepted_steps == nullptr || rejected_steps == nullptr ||
        inner_fallback_count == nullptr || outer_fallback_count == nullptr) {
        set_status(status, kStatusInvalidArgument);
        return;
    }

    try {
        dynamite::orblib_cpp::TriaxialMgeSetup mge;
        if (!dynamite::orblib_cpp::setup_triaxial_mge_from_observed(
                ngauss,
                surf_pc,
                sigobs_arcsec,
                qobs,
                psi_obs_degrees,
                distance_mpc,
                theta_degrees,
                phi_degrees,
                psi_view_degrees,
                upsilon,
                mge
            )) {
            set_status(status, kStatusInvalidArgument);
            return;
        }

        dynamite::orblib_cpp::DarkHaloSetup halo;
        if (!dynamite::orblib_cpp::setup_dark_halo(
                dark_halo_profile_type,
                dark_halo_parameter_count,
                dark_halo_parameters,
                mge.total_mass,
                halo
            )) {
            set_status(status, kStatusInvalidArgument);
            return;
        }

        dynamite::orblib_cpp::InterpolationGridConfig config;
        config.n_radius = n_radius;
        config.n_theta = n_theta;
        config.n_phi = n_phi;
        config.rlogmin = rlogmin;
        config.rlogmax = rlogmax;

        dynamite::orblib_cpp::InterpolatedPotential interpolated;
        if (!interpolated.setup(
                mge,
                halo,
                black_hole_mass,
                black_hole_softening_arcsec * mge.conversion_factor,
                config
            )) {
            set_status(status, kStatusInvalidArgument);
            return;
        }

        const dynamite::orblib_cpp::OrbitIntegrationResult result =
            dynamite::orblib_cpp::integrate_orbit_final_state(
                interpolated,
                omega,
                t_start,
                initial_state,
                t_end,
                rtol,
                atol,
                max_steps,
                final_state
            );

        *final_time = result.final_time;
        *function_evaluations = result.solver.function_evaluations;
        *computed_steps = result.solver.computed_steps;
        *accepted_steps = result.solver.accepted_steps;
        *rejected_steps = result.solver.rejected_steps;
        *inner_fallback_count = interpolated.inner_fallback_count();
        *outer_fallback_count = interpolated.outer_fallback_count();
        if (result.rhs_failed) {
            set_status(status, kStatusInvalidArgument);
            return;
        }
        set_status(status, result.solver.status);
    } catch (...) {
        set_status(status, kStatusException);
    }
}

extern "C" void orblib_cpp_api_integrate_orbit_samples(
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
    double black_hole_mass,
    double black_hole_softening_arcsec,
    int dark_halo_profile_type,
    int dark_halo_parameter_count,
    const double* dark_halo_parameters,
    int n_radius,
    int n_theta,
    int n_phi,
    double rlogmin,
    double rlogmax,
    double omega,
    double t_start,
    double t_end,
    double rtol,
    double atol,
    int max_steps,
    const double* initial_state,
    const double* sample_times,
    int sample_count,
    double* final_state,
    double* sample_state_x,
    double* sample_state_y,
    double* sample_state_z,
    double* sample_state_vx,
    double* sample_state_vy,
    double* sample_state_vz,
    int* samples_written,
    double* final_time,
    int* function_evaluations,
    int* computed_steps,
    int* accepted_steps,
    int* rejected_steps,
    int* inner_fallback_count,
    int* outer_fallback_count,
    int* status
) noexcept {
    if (ngauss <= 0 || surf_pc == nullptr || sigobs_arcsec == nullptr || qobs == nullptr ||
        psi_obs_degrees == nullptr || black_hole_mass < 0.0 ||
        black_hole_softening_arcsec < 0.0 || dark_halo_parameter_count < 0 ||
        (dark_halo_parameter_count > 0 && dark_halo_parameters == nullptr) ||
        n_radius < 2 || n_theta < 2 || n_phi < 2 || rlogmax <= rlogmin ||
        t_end == t_start || rtol <= 0.0 || atol <= 0.0 || max_steps <= 0 ||
        sample_count < 0 || initial_state == nullptr || final_state == nullptr ||
        samples_written == nullptr || final_time == nullptr ||
        function_evaluations == nullptr || computed_steps == nullptr ||
        accepted_steps == nullptr || rejected_steps == nullptr ||
        inner_fallback_count == nullptr || outer_fallback_count == nullptr ||
        (sample_count > 0 &&
         (sample_times == nullptr || sample_state_x == nullptr || sample_state_y == nullptr ||
          sample_state_z == nullptr || sample_state_vx == nullptr || sample_state_vy == nullptr ||
          sample_state_vz == nullptr))) {
        set_status(status, kStatusInvalidArgument);
        return;
    }

    try {
        dynamite::orblib_cpp::TriaxialMgeSetup mge;
        if (!dynamite::orblib_cpp::setup_triaxial_mge_from_observed(
                ngauss,
                surf_pc,
                sigobs_arcsec,
                qobs,
                psi_obs_degrees,
                distance_mpc,
                theta_degrees,
                phi_degrees,
                psi_view_degrees,
                upsilon,
                mge
            )) {
            set_status(status, kStatusInvalidArgument);
            return;
        }

        dynamite::orblib_cpp::DarkHaloSetup halo;
        if (!dynamite::orblib_cpp::setup_dark_halo(
                dark_halo_profile_type,
                dark_halo_parameter_count,
                dark_halo_parameters,
                mge.total_mass,
                halo
            )) {
            set_status(status, kStatusInvalidArgument);
            return;
        }

        dynamite::orblib_cpp::InterpolationGridConfig config;
        config.n_radius = n_radius;
        config.n_theta = n_theta;
        config.n_phi = n_phi;
        config.rlogmin = rlogmin;
        config.rlogmax = rlogmax;

        dynamite::orblib_cpp::InterpolatedPotential interpolated;
        if (!interpolated.setup(
                mge,
                halo,
                black_hole_mass,
                black_hole_softening_arcsec * mge.conversion_factor,
                config
            )) {
            set_status(status, kStatusInvalidArgument);
            return;
        }

        std::vector<double> sample_states(static_cast<std::size_t>(sample_count) * 6U, 0.0);
        int written = 0;
        const dynamite::orblib_cpp::OrbitIntegrationResult result =
            dynamite::orblib_cpp::integrate_orbit_samples(
                interpolated,
                omega,
                t_start,
                initial_state,
                t_end,
                rtol,
                atol,
                max_steps,
                sample_times,
                sample_count,
                final_state,
                sample_states.data(),
                written
            );

        for (int i = 0; i < written; ++i) {
            const int offset = i * 6;
            sample_state_x[i] = sample_states[static_cast<std::size_t>(offset)];
            sample_state_y[i] = sample_states[static_cast<std::size_t>(offset + 1)];
            sample_state_z[i] = sample_states[static_cast<std::size_t>(offset + 2)];
            sample_state_vx[i] = sample_states[static_cast<std::size_t>(offset + 3)];
            sample_state_vy[i] = sample_states[static_cast<std::size_t>(offset + 4)];
            sample_state_vz[i] = sample_states[static_cast<std::size_t>(offset + 5)];
        }

        *samples_written = written;
        *final_time = result.final_time;
        *function_evaluations = result.solver.function_evaluations;
        *computed_steps = result.solver.computed_steps;
        *accepted_steps = result.solver.accepted_steps;
        *rejected_steps = result.solver.rejected_steps;
        *inner_fallback_count = interpolated.inner_fallback_count();
        *outer_fallback_count = interpolated.outer_fallback_count();
        if (result.rhs_failed) {
            set_status(status, kStatusInvalidArgument);
            return;
        }
        set_status(status, result.solver.status);
    } catch (...) {
        set_status(status, kStatusException);
    }
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

extern "C" void orblib_cpp_api_orbitstart_calc_start_state(
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
    double black_hole_mass,
    double black_hole_softening_arcsec,
    int dark_halo_profile_type,
    int dark_halo_parameter_count,
    const double* dark_halo_parameters,
    double radius,
    double start_theta,
    double energy,
    double* state,
    int* status
) noexcept {
    if (ngauss <= 0 || surf_pc == nullptr || sigobs_arcsec == nullptr || qobs == nullptr ||
        psi_obs_degrees == nullptr || black_hole_mass < 0.0 ||
        black_hole_softening_arcsec < 0.0 || dark_halo_parameter_count < 0 ||
        (dark_halo_parameter_count > 0 && dark_halo_parameters == nullptr) ||
        radius < 0.0 || state == nullptr || !std::isfinite(radius) ||
        !std::isfinite(start_theta) || !std::isfinite(energy)) {
        set_status(status, kStatusInvalidArgument);
        return;
    }

    try {
        dynamite::orblib_cpp::TriaxialMgeSetup mge;
        if (!dynamite::orblib_cpp::setup_triaxial_mge_from_observed(
                ngauss,
                surf_pc,
                sigobs_arcsec,
                qobs,
                psi_obs_degrees,
                distance_mpc,
                theta_degrees,
                phi_degrees,
                psi_view_degrees,
                upsilon,
                mge
            )) {
            set_status(status, kStatusInvalidArgument);
            return;
        }

        dynamite::orblib_cpp::DarkHaloSetup halo;
        if (!dynamite::orblib_cpp::setup_dark_halo(
                dark_halo_profile_type,
                dark_halo_parameter_count,
                dark_halo_parameters,
                mge.total_mass,
                halo
            )) {
            set_status(status, kStatusInvalidArgument);
            return;
        }

        if (!dynamite::orblib_cpp::calculate_orbit_start_state(
                mge,
                halo,
                black_hole_mass,
                black_hole_softening_arcsec * mge.conversion_factor,
                radius,
                start_theta,
                energy,
                state
            )) {
            set_status(status, kStatusInvalidArgument);
            return;
        }
        set_status(status, kStatusOk);
    } catch (...) {
        set_status(status, kStatusException);
    }
}

extern "C" void orblib_cpp_api_orbitstart_find_equivalent_radius(
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
    double black_hole_mass,
    double black_hole_softening_arcsec,
    int dark_halo_profile_type,
    int dark_halo_parameter_count,
    const double* dark_halo_parameters,
    double request_radius,
    double energy,
    double start_theta,
    double start_phi,
    double* radius,
    int* iterations,
    int* status
) noexcept {
    if (ngauss <= 0 || surf_pc == nullptr || sigobs_arcsec == nullptr || qobs == nullptr ||
        psi_obs_degrees == nullptr || black_hole_mass < 0.0 ||
        black_hole_softening_arcsec < 0.0 || dark_halo_parameter_count < 0 ||
        (dark_halo_parameter_count > 0 && dark_halo_parameters == nullptr) ||
        request_radius <= 0.0 || radius == nullptr || iterations == nullptr ||
        !std::isfinite(request_radius) || !std::isfinite(energy) ||
        !std::isfinite(start_theta) || !std::isfinite(start_phi)) {
        set_status(status, kStatusInvalidArgument);
        return;
    }

    try {
        dynamite::orblib_cpp::TriaxialMgeSetup mge;
        if (!dynamite::orblib_cpp::setup_triaxial_mge_from_observed(
                ngauss,
                surf_pc,
                sigobs_arcsec,
                qobs,
                psi_obs_degrees,
                distance_mpc,
                theta_degrees,
                phi_degrees,
                psi_view_degrees,
                upsilon,
                mge
            )) {
            set_status(status, kStatusInvalidArgument);
            return;
        }

        dynamite::orblib_cpp::DarkHaloSetup halo;
        if (!dynamite::orblib_cpp::setup_dark_halo(
                dark_halo_profile_type,
                dark_halo_parameter_count,
                dark_halo_parameters,
                mge.total_mass,
                halo
            )) {
            set_status(status, kStatusInvalidArgument);
            return;
        }

        double result_radius = 0.0;
        int result_iterations = 0;
        if (!dynamite::orblib_cpp::find_equivalent_radius(
                mge,
                halo,
                black_hole_mass,
                black_hole_softening_arcsec * mge.conversion_factor,
                request_radius,
                energy,
                start_theta,
                start_phi,
                result_radius,
                result_iterations
            )) {
            set_status(status, kStatusInvalidArgument);
            return;
        }
        *radius = result_radius;
        *iterations = result_iterations;
        set_status(status, kStatusOk);
    } catch (...) {
        set_status(status, kStatusException);
    }
}

extern "C" void orblib_cpp_api_orbitstart_box_start_record(
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
    double black_hole_mass,
    double black_hole_softening_arcsec,
    int dark_halo_profile_type,
    int dark_halo_parameter_count,
    const double* dark_halo_parameters,
    double request_radius,
    double energy,
    int i2_index,
    int i3_index,
    int i2_count,
    int i3_count,
    double circular_radius,
    double circular_period,
    double circular_velocity,
    double* record,
    int* iterations,
    int* status
) noexcept {
    if (ngauss <= 0 || surf_pc == nullptr || sigobs_arcsec == nullptr || qobs == nullptr ||
        psi_obs_degrees == nullptr || black_hole_mass < 0.0 ||
        black_hole_softening_arcsec < 0.0 || dark_halo_parameter_count < 0 ||
        (dark_halo_parameter_count > 0 && dark_halo_parameters == nullptr) ||
        request_radius <= 0.0 || i2_index < 0 || i3_index < 0 || i2_count <= 0 ||
        i3_count <= 0 || i2_index >= i2_count || i3_index >= i3_count ||
        record == nullptr || iterations == nullptr || !std::isfinite(request_radius) ||
        !std::isfinite(energy) || !std::isfinite(circular_radius) ||
        !std::isfinite(circular_period) || !std::isfinite(circular_velocity)) {
        set_status(status, kStatusInvalidArgument);
        return;
    }

    try {
        dynamite::orblib_cpp::TriaxialMgeSetup mge;
        if (!dynamite::orblib_cpp::setup_triaxial_mge_from_observed(
                ngauss,
                surf_pc,
                sigobs_arcsec,
                qobs,
                psi_obs_degrees,
                distance_mpc,
                theta_degrees,
                phi_degrees,
                psi_view_degrees,
                upsilon,
                mge
            )) {
            set_status(status, kStatusInvalidArgument);
            return;
        }

        dynamite::orblib_cpp::DarkHaloSetup halo;
        if (!dynamite::orblib_cpp::setup_dark_halo(
                dark_halo_profile_type,
                dark_halo_parameter_count,
                dark_halo_parameters,
                mge.total_mass,
                halo
            )) {
            set_status(status, kStatusInvalidArgument);
            return;
        }

        int result_iterations = 0;
        if (!dynamite::orblib_cpp::calculate_box_start_record(
                mge,
                halo,
                black_hole_mass,
                black_hole_softening_arcsec * mge.conversion_factor,
                request_radius,
                energy,
                i2_index,
                i3_index,
                i2_count,
                i3_count,
                circular_radius,
                circular_period,
                circular_velocity,
                record,
                result_iterations
            )) {
            set_status(status, kStatusInvalidArgument);
            return;
        }
        *iterations = result_iterations;
        set_status(status, kStatusOk);
    } catch (...) {
        set_status(status, kStatusException);
    }
}

extern "C" void orblib_cpp_api_orbitstart_unregularized_grid(
    int energy_count,
    int i2_count,
    const double* outer_boundaries,
    const double* middle_boundaries,
    const int* irregular,
    int* noreg_grid,
    int* status
) noexcept {
    if (!dynamite::orblib_cpp::compute_unregularized_orbit_grid(
            energy_count,
            i2_count,
            outer_boundaries,
            middle_boundaries,
            irregular,
            noreg_grid
        )) {
        set_status(status, kStatusInvalidArgument);
        return;
    }
    set_status(status, kStatusOk);
}

extern "C" void orblib_cpp_api_orbitstart_tube_schedule(
    int energy_count,
    int i2_count,
    int i3_count,
    const double* inner_boundaries,
    const double* middle_boundaries,
    const double* outer_boundaries,
    const int* irregular,
    const int* noreg_grid,
    double* start_radii,
    int* noreg_flags,
    int* status
) noexcept {
    if (!dynamite::orblib_cpp::compute_tube_start_schedule(
            energy_count,
            i2_count,
            i3_count,
            inner_boundaries,
            middle_boundaries,
            outer_boundaries,
            irregular,
            noreg_grid,
            start_radii,
            noreg_flags
        )) {
        set_status(status, kStatusInvalidArgument);
        return;
    }
    set_status(status, kStatusOk);
}

extern "C" void orblib_cpp_api_write_qgrid_file(
    const char* output_path,
    int orbit_count,
    int energy_count,
    int i2_count,
    int i3_count,
    int dithering,
    int not_regularizable_count,
    int radius_bin_count,
    int theta_bin_count,
    int phi_bin_count,
    const double* radius_boundaries,
    const double* theta_boundaries,
    const double* phi_boundaries,
    const int* orbit_types,
    const double* qgrids,
    int* status
) noexcept {
    if (output_path == nullptr || orbit_count <= 0 || energy_count <= 0 ||
        i2_count <= 0 || i3_count <= 0 || dithering <= 0 ||
        not_regularizable_count < 0 || radius_bin_count <= 0 ||
        theta_bin_count <= 0 || phi_bin_count <= 0 || radius_boundaries == nullptr ||
        theta_boundaries == nullptr || phi_boundaries == nullptr ||
        orbit_types == nullptr || qgrids == nullptr) {
        set_status(status, kStatusInvalidArgument);
        return;
    }

    try {
        if (!dynamite::orblib_cpp::write_qgrid_file(
                output_path,
                orbit_count,
                energy_count,
                i2_count,
                i3_count,
                dithering,
                not_regularizable_count,
                radius_bin_count,
                theta_bin_count,
                phi_bin_count,
                radius_boundaries,
                theta_boundaries,
                phi_boundaries,
                orbit_types,
                qgrids
            )) {
            set_status(status, kStatusIoError);
            return;
        }
        set_status(status, kStatusOk);
    } catch (...) {
        set_status(status, kStatusException);
    }
}

extern "C" void orblib_cpp_api_write_losvd_histogram_file(
    const char* output_path,
    int orbit_count,
    int aperture_count,
    int velocity_bin_count,
    double velocity_bin_width,
    const int* begin_offsets,
    const int* end_offsets,
    const double* histograms,
    int* status
) noexcept {
    if (output_path == nullptr || orbit_count <= 0 || aperture_count <= 0 ||
        velocity_bin_count <= 0 || velocity_bin_width <= 0.0 ||
        begin_offsets == nullptr || end_offsets == nullptr || histograms == nullptr ||
        !std::isfinite(velocity_bin_width)) {
        set_status(status, kStatusInvalidArgument);
        return;
    }

    try {
        if (!dynamite::orblib_cpp::write_losvd_histogram_file(
                output_path,
                orbit_count,
                aperture_count,
                velocity_bin_count,
                velocity_bin_width,
                begin_offsets,
                end_offsets,
                histograms
            )) {
            set_status(status, kStatusIoError);
            return;
        }
        set_status(status, kStatusOk);
    } catch (...) {
        set_status(status, kStatusException);
    }
}

extern "C" void orblib_cpp_api_write_population_mass_file(
    const char* output_path,
    int orbit_count,
    int population_count,
    const int* aperture_counts,
    const double* masses,
    int* status
) noexcept {
    if (output_path == nullptr || orbit_count <= 0 || population_count <= 0 ||
        aperture_counts == nullptr || masses == nullptr) {
        set_status(status, kStatusInvalidArgument);
        return;
    }

    try {
        if (!dynamite::orblib_cpp::write_population_mass_file(
                output_path,
                orbit_count,
                population_count,
                aperture_counts,
                masses
            )) {
            set_status(status, kStatusIoError);
            return;
        }
        set_status(status, kStatusOk);
    } catch (...) {
        set_status(status, kStatusException);
    }
}

extern "C" void orblib_cpp_api_write_orbit_class_file(
    const char* output_path,
    int orbit_count,
    int dither_count,
    const double* moments,
    int* status
) noexcept {
    if (output_path == nullptr || orbit_count <= 0 || dither_count <= 0 || moments == nullptr) {
        set_status(status, kStatusInvalidArgument);
        return;
    }

    try {
        if (!dynamite::orblib_cpp::write_orbit_class_file(
                output_path,
                orbit_count,
                dither_count,
                moments
            )) {
            set_status(status, kStatusIoError);
            return;
        }
        set_status(status, kStatusOk);
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
