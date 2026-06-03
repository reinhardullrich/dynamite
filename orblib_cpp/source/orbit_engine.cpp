#include "orbit_engine.hpp"

#include "interpolated_potential.hpp"
#include "orbit_aperture.hpp"
#include "orbit_classification.hpp"
#include "orbit_histogram.hpp"
#include "orbit_integrator.hpp"
#include "orbit_output.hpp"
#include "orbit_projection.hpp"
#include "orbit_qgrid.hpp"
#include "potential.hpp"
#include "ran1.hpp"
#include "triaxial_mge.hpp"

#include <algorithm>
#include <cmath>
#include <cstddef>
#include <cstdio>
#include <cstdlib>
#include <limits>
#include <numeric>
#include <vector>

namespace dynamite::orblib_cpp {
namespace {

constexpr int kStatusOk = 0;
constexpr int kStatusInvalidArgument = -1;
constexpr int kStatusIoError = -2;
constexpr int kStatusException = -101;
constexpr int kQgridChannelCount = 16;
constexpr int kProjectionCount = 8;
constexpr int kStateSize = 6;
constexpr int kOrbitMomentCount = 5;
constexpr double kPi = 3.141592653589793238462643383279502884;
constexpr int kFortranInterpolationAccuracyRandomDraws = 20000 * 3;

struct BeginTable {
    std::vector<double> x;
    std::vector<double> y;
    std::vector<double> z;
    std::vector<double> vx;
    std::vector<double> vy;
    std::vector<double> vz;
    std::vector<double> rcirc;
    std::vector<double> tcirc;
    std::vector<double> vcirc;
    std::vector<int> not_regularizable;
};

struct ApertureRuntime {
    int source_pixel_count = 0;
    int target_pixel_count = 0;
    int velocity_bin_count = 0;
    int psf_index = 0;
    int histogram_dim = 0;
    int binning_type = 0;
    int losvd_row_offset = -1;
    int pops_row_offset = -1;
};

bool checked_mul_int(int lhs, int rhs, int& result) noexcept {
    if (lhs < 0 || rhs < 0) {
        return false;
    }
    if (lhs != 0 && rhs > std::numeric_limits<int>::max() / lhs) {
        return false;
    }
    result = lhs * rhs;
    return true;
}

double degrees_to_radians(double degrees) noexcept {
    return degrees * (kPi / 180.0);
}

double begin_value(const OrblibDirectInput& input, int row, int column) noexcept {
    return input.begin_values[
        static_cast<std::size_t>(row) +
        static_cast<std::size_t>(input.begin_rows) * static_cast<std::size_t>(column)
    ];
}

double matrix_value(const double* values, int leading_dimension, int row, int column) noexcept {
    return values[
        static_cast<std::size_t>(row) +
        static_cast<std::size_t>(leading_dimension) * static_cast<std::size_t>(column)
    ];
}

int matrix_int_value(const int* values, int leading_dimension, int row, int column) noexcept {
    return values[
        static_cast<std::size_t>(row) +
        static_cast<std::size_t>(leading_dimension) * static_cast<std::size_t>(column)
    ];
}

double quantize_legacy_begin_value(double value) noexcept {
    char buffer[64];
    const int written = std::snprintf(buffer, sizeof(buffer), "%30.10E", value);
    if (written <= 0 || written >= static_cast<int>(sizeof(buffer))) {
        return value;
    }
    char* end = nullptr;
    const double parsed = std::strtod(buffer, &end);
    return end == buffer ? value : parsed;
}

bool load_begin_table(const OrblibDirectInput& input, BeginTable& begin) {
    const std::size_t rows = static_cast<std::size_t>(input.begin_rows);
    begin.x.resize(rows);
    begin.y.resize(rows);
    begin.z.resize(rows);
    begin.vx.resize(rows);
    begin.vy.resize(rows);
    begin.vz.resize(rows);
    begin.rcirc.resize(rows);
    begin.tcirc.resize(rows);
    begin.vcirc.resize(rows);
    begin.not_regularizable.resize(rows);

    for (int row = 0; row < input.begin_rows; ++row) {
        begin.x[static_cast<std::size_t>(row)] = quantize_legacy_begin_value(begin_value(input, row, 0));
        begin.y[static_cast<std::size_t>(row)] = quantize_legacy_begin_value(begin_value(input, row, 1));
        begin.z[static_cast<std::size_t>(row)] = quantize_legacy_begin_value(begin_value(input, row, 2));
        begin.vx[static_cast<std::size_t>(row)] = quantize_legacy_begin_value(begin_value(input, row, 3));
        begin.vy[static_cast<std::size_t>(row)] = quantize_legacy_begin_value(begin_value(input, row, 4));
        begin.vz[static_cast<std::size_t>(row)] = quantize_legacy_begin_value(begin_value(input, row, 5));
        begin.rcirc[static_cast<std::size_t>(row)] = quantize_legacy_begin_value(begin_value(input, row, 6));
        begin.tcirc[static_cast<std::size_t>(row)] = quantize_legacy_begin_value(begin_value(input, row, 7));
        begin.vcirc[static_cast<std::size_t>(row)] = quantize_legacy_begin_value(begin_value(input, row, 8));
        begin.not_regularizable[static_cast<std::size_t>(row)] = input.begin_noreg[row];
        if (begin.not_regularizable[static_cast<std::size_t>(row)] < 0 ||
            !std::isfinite(begin.x[static_cast<std::size_t>(row)]) ||
            !std::isfinite(begin.y[static_cast<std::size_t>(row)]) ||
            !std::isfinite(begin.z[static_cast<std::size_t>(row)]) ||
            !std::isfinite(begin.vx[static_cast<std::size_t>(row)]) ||
            !std::isfinite(begin.vy[static_cast<std::size_t>(row)]) ||
            !std::isfinite(begin.vz[static_cast<std::size_t>(row)]) ||
            !std::isfinite(begin.tcirc[static_cast<std::size_t>(row)]) ||
            begin.tcirc[static_cast<std::size_t>(row)] <= 0.0) {
            return false;
        }
    }
    return true;
}

int dithered_begin_row(
    int orbit_number,
    int dither_number,
    int expanded_i2_count,
    int expanded_i3_count,
    int dithering
) noexcept {
    const int i3 = ((orbit_number - 1) % (expanded_i3_count / dithering)) + 1;
    const int i2 =
        (((orbit_number - 1) / (expanded_i3_count / dithering)) %
         (expanded_i2_count / dithering)) + 1;
    const int energy =
        ((orbit_number - 1) / (expanded_i3_count * expanded_i2_count / (dithering * dithering))) + 1;

    const int d3 = ((dither_number - 1) % dithering) + 1;
    const int d2 = (((dither_number - 1) / dithering) % dithering) + 1;
    const int d1 = ((dither_number - 1) / (dithering * dithering)) + 1;

    const int expanded_i3 = (i3 - 1) * dithering + d3;
    const int expanded_i2 = (i2 - 1) * dithering + d2;
    const int expanded_energy = (energy - 1) * dithering + d1;
    return (expanded_i3 - 1) +
           (expanded_i2 - 1) * expanded_i3_count +
           (expanded_energy - 1) * expanded_i3_count * expanded_i2_count;
}

bool compute_energy(
    const InterpolatedPotential& potential,
    double omega,
    const double state[kStateSize],
    double& energy
) noexcept {
    double potential_value = 0.0;
    if (!potential.evaluate_potential(state[0], state[1], state[2], potential_value)) {
        return false;
    }
    if (omega != 0.0) {
        potential_value += omega * (state[0] * state[4] - state[1] * state[3]);
    }
    energy = potential_value - 0.5 * (state[3] * state[3] + state[4] * state[4] + state[5] * state[5]);
    return std::isfinite(energy);
}

int nint_positive(double value) noexcept {
    return static_cast<int>(std::floor(value + 0.5));
}

bool build_sigma_map(
    int gaussian_count,
    const double* weights,
    const double* sigmas_km,
    int sample_count,
    std::vector<double>& sigma_map
) {
    sigma_map.assign(static_cast<std::size_t>(sample_count), 0.0);
    double weight_sum = 0.0;
    for (int gaussian = 0; gaussian < gaussian_count; ++gaussian) {
        weight_sum += std::abs(weights[gaussian]);
    }
    if (weight_sum <= 0.0) {
        return false;
    }

    std::vector<int> weight_index(static_cast<std::size_t>(gaussian_count + 1), 1);
    double cumulative_weight = 0.0;
    for (int gaussian = 0; gaussian < gaussian_count; ++gaussian) {
        cumulative_weight += std::abs(weights[gaussian]);
        weight_index[static_cast<std::size_t>(gaussian + 1)] =
            nint_positive(cumulative_weight * (static_cast<double>(sample_count - 1) / weight_sum)) + 1;
    }
    weight_index.front() = 1;
    weight_index.back() = sample_count;

    for (int gaussian = 0; gaussian < gaussian_count; ++gaussian) {
        for (int index = weight_index[static_cast<std::size_t>(gaussian)];
             index <= weight_index[static_cast<std::size_t>(gaussian + 1)];
             ++index) {
            sigma_map[static_cast<std::size_t>(index - 1)] = sigmas_km[gaussian];
        }
    }
    return true;
}

void gaussian_pair(Ran1& rng, double& x, double& y) noexcept {
    float v0 = 0.0f;
    float v1 = 0.0f;
    float rsq = 0.0f;
    do {
        v0 = static_cast<float>(rng.next());
        v1 = static_cast<float>(rng.next());
        v0 = 2.0f * v0 - 1.0f;
        v1 = 2.0f * v1 - 1.0f;
        rsq = v0 * v0 + v1 * v1;
    } while (rsq <= 0.0f || rsq >= 1.0f);

    const float scale = std::sqrt(-2.0f * std::log(rsq) / rsq);
    x = static_cast<double>(v0 * scale);
    y = static_cast<double>(v1 * scale);
}

bool apply_psf_persistent_rng(
    int gaussian_count,
    const double* sigmas_km,
    const std::vector<double>& sigma_map,
    int sample_count,
    const double* projected_x,
    const double* projected_y,
    Ran1& rng,
    std::vector<double>& gaussian_x,
    std::vector<double>& gaussian_y,
    double* convolved_x,
    double* convolved_y
) noexcept {
    if (gaussian_count == 1) {
        const double sigma = sigmas_km[0];
        if (sigma > 1.0) {
            for (int sample = 0; sample < sample_count; ++sample) {
                double dx = 0.0;
                double dy = 0.0;
                gaussian_pair(rng, dx, dy);
                convolved_x[sample] = projected_x[sample] + dx * sigma;
                convolved_y[sample] = projected_y[sample] + dy * sigma;
            }
        } else {
            for (int sample = 0; sample < sample_count; ++sample) {
                convolved_x[sample] = projected_x[sample];
                convolved_y[sample] = projected_y[sample];
            }
        }
        return true;
    }

    if (static_cast<int>(sigma_map.size()) != sample_count) {
        return false;
    }
    for (int sample = 0; sample < sample_count; ++sample) {
        gaussian_pair(
            rng,
            gaussian_x[static_cast<std::size_t>(sample)],
            gaussian_y[static_cast<std::size_t>(sample)]
        );
    }
    for (int sample = 0; sample < sample_count; ++sample) {
        const float selector = static_cast<float>(rng.next());
        const int sigma_index =
            static_cast<int>(selector * static_cast<float>(sample_count - 1) + 1.0f);
        const double sigma = sigma_map[static_cast<std::size_t>(sigma_index - 1)];
        convolved_x[sample] =
            projected_x[sample] + gaussian_x[static_cast<std::size_t>(sample)] * sigma;
        convolved_y[sample] =
            projected_y[sample] + gaussian_y[static_cast<std::size_t>(sample)] * sigma;
    }
    return true;
}

bool same_histogram_settings(
    int aperture_count,
    const int* ap_psf,
    const double* hist_width,
    const double* hist_center,
    const int* hist_bins
) noexcept {
    const int first_psf = ap_psf[0] - 1;
    const double width = hist_width[first_psf];
    const double center = hist_center[first_psf];
    const int bins = hist_bins[first_psf];
    for (int aperture = 1; aperture < aperture_count; ++aperture) {
        const int psf = ap_psf[aperture] - 1;
        if (hist_width[psf] != width || hist_center[psf] != center || hist_bins[psf] != bins) {
            return false;
        }
    }
    return true;
}

bool validate_common_input(const OrblibDirectInput& input) noexcept {
    return input.ngauss > 0 &&
           input.surf_pc != nullptr &&
           input.sigobs_arcsec != nullptr &&
           input.qobs != nullptr &&
           input.psi_obs_degrees != nullptr &&
           input.distance_mpc > 0.0 &&
           input.upsilon >= 0.0 &&
           input.black_hole_mass >= 0.0 &&
           input.black_hole_softening_arcsec >= 0.0 &&
           input.nener > 0 &&
           input.ni2 > 0 &&
           input.ni3 > 0 &&
           input.orbit_dithering > 0 &&
           input.n_radius >= 2 &&
           input.n_theta >= 2 &&
           input.n_phi >= 2 &&
           input.rlogmax_arcsec > input.rlogmin_arcsec &&
           input.dark_halo_parameter_count >= 0 &&
           (input.dark_halo_parameter_count == 0 || input.dark_halo_parameters != nullptr) &&
           input.begin_rows > 0 &&
           input.begin_values != nullptr &&
           input.begin_noreg != nullptr &&
           input.orbital_periods >= 1.0 &&
           input.sampling > 0 &&
           input.starting_orbit == 1 &&
           input.accuracy > 0.0 &&
           input.accuracy <= 0.5 &&
           input.psf_count > 0 &&
           input.max_psf_gauss > 0 &&
           input.psf_kind != nullptr &&
           input.psf_weight != nullptr &&
           input.psf_sigma != nullptr &&
           input.aperture_count > 0 &&
           input.ap_begin != nullptr &&
           input.ap_size != nullptr &&
           input.ap_rot != nullptr &&
           input.ap_binx != nullptr &&
           input.ap_biny != nullptr &&
           input.ap_psf != nullptr &&
           input.ap_hist_dim != nullptr &&
           input.hist_width != nullptr &&
           input.hist_center != nullptr &&
           input.hist_bins != nullptr &&
           input.max_bin_size > 0 &&
           input.bin_type != nullptr &&
           input.bin_size != nullptr &&
           input.bin_order != nullptr &&
           input.out_qgrid_path != nullptr &&
           input.out_losvd_path != nullptr &&
           input.out_orbclass_path != nullptr &&
           std::isfinite(input.distance_mpc) &&
           std::isfinite(input.theta_degrees) &&
           std::isfinite(input.phi_degrees) &&
           std::isfinite(input.psi_view_degrees) &&
           std::isfinite(input.upsilon) &&
           std::isfinite(input.black_hole_mass) &&
           std::isfinite(input.black_hole_softening_arcsec) &&
           std::isfinite(input.rlogmin_arcsec) &&
           std::isfinite(input.rlogmax_arcsec) &&
           std::isfinite(input.orbital_periods) &&
           std::isfinite(input.accuracy);
}

}  // namespace

int run_orblib_direct_generation(const OrblibDirectInput& input) noexcept {
    try {
        if (!validate_common_input(input)) {
            return kStatusInvalidArgument;
        }

        TriaxialMgeSetup mge;
        if (!setup_triaxial_mge_from_observed(
                input.ngauss,
                input.surf_pc,
                input.sigobs_arcsec,
                input.qobs,
                input.psi_obs_degrees,
                input.distance_mpc,
                input.theta_degrees,
                input.phi_degrees,
                input.psi_view_degrees,
                input.upsilon,
                mge
            ) || mge.conversion_factor <= 0.0) {
            return kStatusInvalidArgument;
        }

        DarkHaloSetup halo;
        if (!setup_dark_halo(
                input.dark_halo_profile_type,
                input.dark_halo_parameter_count,
                input.dark_halo_parameters,
                mge.total_mass,
                halo
            )) {
            return kStatusInvalidArgument;
        }

        int expanded_energy_count = 0;
        int expanded_i2_count = 0;
        int expanded_i3_count = 0;
        int expanded_plane_count = 0;
        int expanded_record_count = 0;
        int dither_square = 0;
        int dither_count = 0;
        int full_orbit_count = 0;
        if (!checked_mul_int(input.nener, input.orbit_dithering, expanded_energy_count) ||
            !checked_mul_int(input.ni2, input.orbit_dithering, expanded_i2_count) ||
            !checked_mul_int(input.ni3, input.orbit_dithering, expanded_i3_count) ||
            !checked_mul_int(expanded_i2_count, expanded_i3_count, expanded_plane_count) ||
            !checked_mul_int(expanded_energy_count, expanded_plane_count, expanded_record_count) ||
            !checked_mul_int(input.orbit_dithering, input.orbit_dithering, dither_square) ||
            !checked_mul_int(dither_square, input.orbit_dithering, dither_count) ||
            !checked_mul_int(input.nener, input.ni2, full_orbit_count) ||
            !checked_mul_int(full_orbit_count, input.ni3, full_orbit_count)) {
            return kStatusInvalidArgument;
        }
        if (input.begin_rows != expanded_record_count) {
            return kStatusInvalidArgument;
        }
        const int requested_final_orbit =
            input.number_orbits == -1 ? full_orbit_count : input.number_orbits;
        if (requested_final_orbit != full_orbit_count) {
            return kStatusInvalidArgument;
        }

        BeginTable begin;
        if (!load_begin_table(input, begin)) {
            return kStatusInvalidArgument;
        }

        InterpolationGridConfig config;
        config.n_radius = input.n_radius;
        config.n_theta = input.n_theta;
        config.n_phi = input.n_phi;
        config.rlogmin = input.rlogmin_arcsec + std::log10(mge.conversion_factor);
        config.rlogmax = input.rlogmax_arcsec + std::log10(mge.conversion_factor);

        InterpolatedPotential potential;
        const double black_hole_softening_km =
            input.black_hole_softening_arcsec * mge.conversion_factor;
        if (!potential.setup(
                mge,
                halo,
                input.black_hole_mass,
                black_hole_softening_km,
                config
            )) {
            return kStatusInvalidArgument;
        }

        std::vector<double> radius_boundaries(static_cast<std::size_t>(input.n_radius + 1), 0.0);
        std::vector<double> theta_boundaries(static_cast<std::size_t>(input.n_theta + 1), 0.0);
        std::vector<double> phi_boundaries(static_cast<std::size_t>(input.n_phi + 1), 0.0);
        if (!setup_qgrid_boundaries(
                input.n_radius,
                input.n_theta,
                input.n_phi,
                config.rlogmin,
                config.rlogmax,
                input.ngauss,
                mge.sigobs_km.data(),
                radius_boundaries.data(),
                theta_boundaries.data(),
                phi_boundaries.data()
            )) {
            return kStatusInvalidArgument;
        }

        std::vector<double> psf_sigma_km(
            static_cast<std::size_t>(input.max_psf_gauss) * static_cast<std::size_t>(input.psf_count),
            0.0
        );
        std::vector<std::vector<double>> psf_sigma_maps(static_cast<std::size_t>(input.psf_count));
        for (int psf = 0; psf < input.psf_count; ++psf) {
            const int gaussian_count = input.psf_kind[psf];
            if (gaussian_count < 1 || gaussian_count > input.max_psf_gauss ||
                input.hist_width[psf] <= 0.0 || input.hist_bins[psf] < 1 ||
                !std::isfinite(input.hist_width[psf]) ||
                !std::isfinite(input.hist_center[psf])) {
                return kStatusInvalidArgument;
            }
            for (int gaussian = 0; gaussian < gaussian_count; ++gaussian) {
                const double sigma = matrix_value(input.psf_sigma, input.max_psf_gauss, gaussian, psf);
                const double weight = matrix_value(input.psf_weight, input.max_psf_gauss, gaussian, psf);
                if (!std::isfinite(sigma) || !std::isfinite(weight)) {
                    return kStatusInvalidArgument;
                }
                psf_sigma_km[
                    static_cast<std::size_t>(gaussian) +
                    static_cast<std::size_t>(input.max_psf_gauss) * static_cast<std::size_t>(psf)
                ] = sigma * mge.conversion_factor;
            }
            if (gaussian_count > 1 &&
                !build_sigma_map(
                    gaussian_count,
                    input.psf_weight + static_cast<std::size_t>(input.max_psf_gauss) * static_cast<std::size_t>(psf),
                    psf_sigma_km.data() + static_cast<std::size_t>(input.max_psf_gauss) * static_cast<std::size_t>(psf),
                    input.sampling,
                    psf_sigma_maps[static_cast<std::size_t>(psf)]
                )) {
                return kStatusInvalidArgument;
            }
        }

        std::vector<ApertureRuntime> apertures(static_cast<std::size_t>(input.aperture_count));
        std::vector<int> psf_hist_aperture(static_cast<std::size_t>(input.psf_count), -1);
        int losvd_rows_per_orbit = 0;
        int pops_population_count = 0;
        int pops_total_rows = 0;
        int max_velocity_bin_count = 0;
        int max_aperture_pixels = 0;
        std::vector<int> population_aperture_counts;
        for (int aperture = 0; aperture < input.aperture_count; ++aperture) {
            const int bins_x = input.ap_binx[aperture];
            const int bins_y = input.ap_biny[aperture];
            const int psf_index = input.ap_psf[aperture] - 1;
            const int histogram_dim = input.ap_hist_dim[aperture];
            const int binning_type = input.bin_type[aperture];
            int source_pixel_count = 0;
            if (bins_x <= 0 || bins_y <= 0 ||
                !checked_mul_int(bins_x, bins_y, source_pixel_count) ||
                psf_index < 0 || psf_index >= input.psf_count ||
                (histogram_dim != 0 && histogram_dim != 1) ||
                (binning_type != 0 && binning_type != 1) ||
                input.ap_size[aperture] <= 0.0 ||
                input.ap_size[static_cast<std::size_t>(input.aperture_count) + static_cast<std::size_t>(aperture)] <= 0.0) {
                return kStatusInvalidArgument;
            }
            psf_hist_aperture[static_cast<std::size_t>(psf_index)] = aperture;
            const int velocity_bin_count = input.hist_bins[psf_index];
            int target_pixel_count = source_pixel_count;
            if (binning_type == 1) {
                if (input.bin_size[aperture] != source_pixel_count ||
                    input.bin_size[aperture] > input.max_bin_size) {
                    return kStatusInvalidArgument;
                }
                target_pixel_count = 0;
                for (int pixel = 0; pixel < source_pixel_count; ++pixel) {
                    const int target = matrix_int_value(input.bin_order, input.max_bin_size, pixel, aperture);
                    if (target < 0 || target > source_pixel_count) {
                        return kStatusInvalidArgument;
                    }
                    target_pixel_count = std::max(target_pixel_count, target);
                }
                if (target_pixel_count <= 0) {
                    return kStatusInvalidArgument;
                }
            }

            auto& runtime = apertures[static_cast<std::size_t>(aperture)];
            runtime.source_pixel_count = source_pixel_count;
            runtime.target_pixel_count = target_pixel_count;
            runtime.velocity_bin_count = velocity_bin_count;
            runtime.psf_index = psf_index;
            runtime.histogram_dim = histogram_dim;
            runtime.binning_type = binning_type;
            max_velocity_bin_count = std::max(max_velocity_bin_count, velocity_bin_count);
            max_aperture_pixels = std::max(max_aperture_pixels, source_pixel_count);
            if (histogram_dim == 1) {
                runtime.losvd_row_offset = losvd_rows_per_orbit;
                losvd_rows_per_orbit += target_pixel_count;
            } else {
                runtime.pops_row_offset = pops_total_rows;
                population_aperture_counts.push_back(target_pixel_count);
                pops_total_rows += target_pixel_count;
                pops_population_count += 1;
            }
        }
        if (losvd_rows_per_orbit <= 0 || max_velocity_bin_count <= 0) {
            return kStatusInvalidArgument;
        }
        for (int psf = 0; psf < input.psf_count; ++psf) {
            if (psf_hist_aperture[static_cast<std::size_t>(psf)] < 0) {
                return kStatusInvalidArgument;
            }
        }

        const bool histograms_same = same_histogram_settings(
            input.aperture_count,
            input.ap_psf,
            input.hist_width,
            input.hist_center,
            input.hist_bins
        );
        const int first_hist_psf = input.ap_psf[0] - 1;
        const double losvd_header_bin_width =
            input.hist_width[first_hist_psf] / static_cast<double>(input.hist_bins[first_hist_psf]);

        std::vector<int> row_velocity_bin_counts(static_cast<std::size_t>(losvd_rows_per_orbit), 0);
        for (const auto& runtime : apertures) {
            if (runtime.histogram_dim != 1) {
                continue;
            }
            for (int row = 0; row < runtime.target_pixel_count; ++row) {
                row_velocity_bin_counts[
                    static_cast<std::size_t>(runtime.losvd_row_offset + row)
                ] = runtime.velocity_bin_count;
            }
        }

        const std::size_t qgrid_stride =
            static_cast<std::size_t>(kQgridChannelCount) *
            static_cast<std::size_t>(input.n_phi) *
            static_cast<std::size_t>(input.n_theta) *
            static_cast<std::size_t>(input.n_radius);
        std::vector<double> qgrids(static_cast<std::size_t>(full_orbit_count) * qgrid_stride, 0.0);
        std::vector<int> orbit_types(static_cast<std::size_t>(full_orbit_count) * static_cast<std::size_t>(dither_count), 5);
        std::vector<int> not_regularizable_counts(static_cast<std::size_t>(full_orbit_count), 0);
        std::vector<double> moments(
            static_cast<std::size_t>(full_orbit_count) *
            static_cast<std::size_t>(dither_count) *
            static_cast<std::size_t>(kOrbitMomentCount),
            0.0
        );
        std::vector<int> losvd_begin_offsets(
            static_cast<std::size_t>(full_orbit_count) * static_cast<std::size_t>(losvd_rows_per_orbit),
            0
        );
        std::vector<int> losvd_end_offsets(losvd_begin_offsets.size(), 0);
        std::vector<double> losvd_histograms(
            static_cast<std::size_t>(full_orbit_count) *
            static_cast<std::size_t>(losvd_rows_per_orbit) *
            static_cast<std::size_t>(max_velocity_bin_count),
            0.0
        );
        std::vector<double> population_masses;
        if (pops_total_rows > 0) {
            population_masses.assign(
                static_cast<std::size_t>(full_orbit_count) * static_cast<std::size_t>(pops_total_rows),
                0.0
            );
        }

        std::vector<std::vector<double>> source_histograms(static_cast<std::size_t>(input.aperture_count));
        std::vector<std::vector<double>> target_histograms(static_cast<std::size_t>(input.aperture_count));
        std::vector<double> stored_counts(static_cast<std::size_t>(input.aperture_count), 0.0);
        for (int aperture = 0; aperture < input.aperture_count; ++aperture) {
            const auto& runtime = apertures[static_cast<std::size_t>(aperture)];
            source_histograms[static_cast<std::size_t>(aperture)].assign(
                static_cast<std::size_t>(runtime.source_pixel_count) *
                static_cast<std::size_t>(runtime.velocity_bin_count),
                0.0
            );
            target_histograms[static_cast<std::size_t>(aperture)].assign(
                static_cast<std::size_t>(runtime.target_pixel_count) *
                static_cast<std::size_t>(runtime.velocity_bin_count),
                0.0
            );
        }

        const int effective_seed = input.random_seed > 0 ? input.random_seed : 1;
        Ran1 rng(-effective_seed);
        (void)rng.next();
        for (int draw = 0; draw < kFortranInterpolationAccuracyRandomDraws; ++draw) {
            (void)rng.next();
        }

        constexpr double omega = 0.0;
        const double theta_radians = degrees_to_radians(input.theta_degrees);
        const double phi_radians = degrees_to_radians(input.phi_degrees);
        const double psi_radians = degrees_to_radians(input.psi_view_degrees);

        std::vector<double> sample_times(static_cast<std::size_t>(input.sampling), 0.0);
        std::vector<double> sample_states(
            static_cast<std::size_t>(input.sampling) * static_cast<std::size_t>(kStateSize),
            0.0
        );
        std::vector<double> old_sample_states(sample_states.size(), 0.0);
        std::vector<double> x(static_cast<std::size_t>(input.sampling), 0.0);
        std::vector<double> y(static_cast<std::size_t>(input.sampling), 0.0);
        std::vector<double> z(static_cast<std::size_t>(input.sampling), 0.0);
        std::vector<double> vx(static_cast<std::size_t>(input.sampling), 0.0);
        std::vector<double> vy(static_cast<std::size_t>(input.sampling), 0.0);
        std::vector<double> vz(static_cast<std::size_t>(input.sampling), 0.0);
        std::vector<double> projected_x(static_cast<std::size_t>(input.sampling), 0.0);
        std::vector<double> projected_y(static_cast<std::size_t>(input.sampling), 0.0);
        std::vector<double> los_velocity(static_cast<std::size_t>(input.sampling), 0.0);
        std::vector<double> convolved_x(static_cast<std::size_t>(input.sampling), 0.0);
        std::vector<double> convolved_y(static_cast<std::size_t>(input.sampling), 0.0);
        std::vector<double> gaussian_x(static_cast<std::size_t>(input.sampling), 0.0);
        std::vector<double> gaussian_y(static_cast<std::size_t>(input.sampling), 0.0);
        std::vector<int> velocity_bins(static_cast<std::size_t>(input.sampling), 0);
        std::vector<int> shared_velocity_bins(static_cast<std::size_t>(input.sampling), 0);
        std::vector<int> aperture_pixels(static_cast<std::size_t>(input.sampling), 0);
        std::vector<int> sparse_begin(static_cast<std::size_t>(max_aperture_pixels), 0);
        std::vector<int> sparse_end(static_cast<std::size_t>(max_aperture_pixels), 0);

        double integrator_initial_step = 0.0;
        bool have_old_orbit = false;

        for (int orbit_number = 1; orbit_number <= full_orbit_count; ++orbit_number) {
            for (auto& histogram : source_histograms) {
                std::fill(histogram.begin(), histogram.end(), 0.0);
            }
            for (auto& histogram : target_histograms) {
                std::fill(histogram.begin(), histogram.end(), 0.0);
            }
            std::fill(stored_counts.begin(), stored_counts.end(), 0.0);

            const int orbit_index = orbit_number - 1;
            double* orbit_qgrid = qgrids.data() + static_cast<std::size_t>(orbit_index) * qgrid_stride;

            for (int dither_number = 1; dither_number <= dither_count; ++dither_number) {
                const int dither_index = dither_number - 1;
                const int begin_row = dithered_begin_row(
                    orbit_number,
                    dither_number,
                    expanded_i2_count,
                    expanded_i3_count,
                    input.orbit_dithering
                );
                if (begin_row < 0 || begin_row >= input.begin_rows) {
                    return kStatusInvalidArgument;
                }
                if (begin.not_regularizable[static_cast<std::size_t>(begin_row)] == 1) {
                    not_regularizable_counts[static_cast<std::size_t>(orbit_index)] = 1;
                }

                double initial_state[kStateSize] = {
                    begin.x[static_cast<std::size_t>(begin_row)],
                    begin.y[static_cast<std::size_t>(begin_row)],
                    begin.z[static_cast<std::size_t>(begin_row)],
                    begin.vx[static_cast<std::size_t>(begin_row)],
                    begin.vy[static_cast<std::size_t>(begin_row)],
                    begin.vz[static_cast<std::size_t>(begin_row)],
                };
                const double t_end =
                    input.orbital_periods * begin.tcirc[static_cast<std::size_t>(begin_row)];
                if (!(t_end > 0.0) || !std::isfinite(t_end)) {
                    return kStatusInvalidArgument;
                }

                double begin_energy = 0.0;
                if (!compute_energy(potential, omega, initial_state, begin_energy)) {
                    return kStatusInvalidArgument;
                }

                bool accepted = false;
                double rtol = input.accuracy;
                double atol = input.accuracy;
                while (!accepted) {
                    const double step = t_end / static_cast<double>(input.sampling + 4);
                    const double random_offset = rng.next();
                    for (int sample = 0; sample < input.sampling; ++sample) {
                        sample_times[static_cast<std::size_t>(sample)] =
                            step * (1.0 + random_offset + static_cast<double>(sample));
                    }

                    const double max_step_count = std::min(
                        static_cast<double>(std::numeric_limits<int>::max() - 1),
                        (1.0 / rtol) * input.orbital_periods / 200.0
                    );
                    const int max_steps =
                        std::max(static_cast<int>(std::floor(max_step_count)), 100000);
                    double final_state[kStateSize] = {};
                    int samples_written = 0;
                    const OrbitIntegrationResult integration = integrate_orbit_samples(
                        potential,
                        omega,
                        0.0,
                        initial_state,
                        t_end,
                        rtol,
                        atol,
                        max_steps,
                        sample_times.data(),
                        input.sampling,
                        final_state,
                        sample_states.data(),
                        samples_written,
                        integrator_initial_step
                    );

                    bool energy_ok = false;
                    if (integration.solver.status == 1 && !integration.rhs_failed &&
                        samples_written == input.sampling) {
                        double end_energy = 0.0;
                        if (!compute_energy(potential, omega, final_state, end_energy)) {
                            return kStatusInvalidArgument;
                        }
                        if (begin_energy != 0.0) {
                            energy_ok = std::abs((begin_energy - end_energy) / begin_energy) < 0.01;
                        }
                    }

                    if (energy_ok) {
                        accepted = true;
                        old_sample_states = sample_states;
                        have_old_orbit = true;
                        integrator_initial_step = integration.solver.suggested_step;
                    } else if (rtol < 1.0e-12) {
                        if (!have_old_orbit) {
                            return kStatusInvalidArgument;
                        }
                        sample_states = old_sample_states;
                        accepted = true;
                    } else {
                        rtol *= 0.1;
                        atol *= 0.1;
                    }
                }

                for (int sample = 0; sample < input.sampling; ++sample) {
                    const std::size_t state_offset =
                        static_cast<std::size_t>(sample) * static_cast<std::size_t>(kStateSize);
                    x[static_cast<std::size_t>(sample)] = sample_states[state_offset];
                    y[static_cast<std::size_t>(sample)] = sample_states[state_offset + 1];
                    z[static_cast<std::size_t>(sample)] = sample_states[state_offset + 2];
                    vx[static_cast<std::size_t>(sample)] = sample_states[state_offset + 3];
                    vy[static_cast<std::size_t>(sample)] = sample_states[state_offset + 4];
                    vz[static_cast<std::size_t>(sample)] = sample_states[state_offset + 5];
                }

                OrbitClassificationResult classification;
                if (!classify_orbit_samples(
                        input.sampling,
                        x.data(),
                        y.data(),
                        z.data(),
                        vx.data(),
                        vy.data(),
                        vz.data(),
                        classification
                    )) {
                    return kStatusInvalidArgument;
                }
                orbit_types[
                    static_cast<std::size_t>(orbit_index) * static_cast<std::size_t>(dither_count) +
                    static_cast<std::size_t>(dither_index)
                ] = classification.type;
                for (int moment = 0; moment < kOrbitMomentCount; ++moment) {
                    moments[
                        static_cast<std::size_t>(moment) +
                        static_cast<std::size_t>(kOrbitMomentCount) *
                            (static_cast<std::size_t>(dither_index) +
                             static_cast<std::size_t>(dither_count) * static_cast<std::size_t>(orbit_index))
                    ] = classification.moments[moment];
                }

                if (!accumulate_qgrid_samples(
                        classification.type,
                        omega,
                        input.n_radius,
                        input.n_theta,
                        input.n_phi,
                        radius_boundaries.data(),
                        theta_boundaries.data(),
                        phi_boundaries.data(),
                        input.sampling,
                        x.data(),
                        y.data(),
                        z.data(),
                        vx.data(),
                        vy.data(),
                        vz.data(),
                        orbit_qgrid
                    )) {
                    return kStatusInvalidArgument;
                }

                for (int projection = 1; projection <= kProjectionCount; ++projection) {
                    if (!project_orbit_samples(
                            classification.type,
                            projection,
                            omega,
                            theta_radians,
                            phi_radians,
                            input.sampling,
                            x.data(),
                            y.data(),
                            z.data(),
                            vx.data(),
                            vy.data(),
                            vz.data(),
                            projected_x.data(),
                            projected_y.data(),
                            los_velocity.data()
                        )) {
                        return kStatusInvalidArgument;
                    }

                    if (histograms_same) {
                        const int aperture = psf_hist_aperture[static_cast<std::size_t>(0)];
                        const int psf = apertures[static_cast<std::size_t>(aperture)].psf_index;
                        if (!map_losvd_velocity_bins(
                                input.hist_width[psf],
                                input.hist_center[psf],
                                input.hist_bins[psf],
                                input.sampling,
                                los_velocity.data(),
                                shared_velocity_bins.data()
                            )) {
                            return kStatusInvalidArgument;
                        }
                    }

                    for (int psf = 0; psf < input.psf_count; ++psf) {
                        const int velocity_aperture =
                            psf_hist_aperture[static_cast<std::size_t>(psf)];
                        if (!histograms_same) {
                            const int velocity_psf =
                                apertures[static_cast<std::size_t>(velocity_aperture)].psf_index;
                            if (!map_losvd_velocity_bins(
                                    input.hist_width[velocity_psf],
                                    input.hist_center[velocity_psf],
                                    input.hist_bins[velocity_psf],
                                    input.sampling,
                                    los_velocity.data(),
                                    velocity_bins.data()
                                )) {
                                return kStatusInvalidArgument;
                            }
                        } else {
                            std::copy(shared_velocity_bins.begin(), shared_velocity_bins.end(), velocity_bins.begin());
                        }

                        if (!apply_psf_persistent_rng(
                                input.psf_kind[psf],
                                psf_sigma_km.data() +
                                    static_cast<std::size_t>(input.max_psf_gauss) * static_cast<std::size_t>(psf),
                                psf_sigma_maps[static_cast<std::size_t>(psf)],
                                input.sampling,
                                projected_x.data(),
                                projected_y.data(),
                                rng,
                                gaussian_x,
                                gaussian_y,
                                convolved_x.data(),
                                convolved_y.data()
                            )) {
                            return kStatusInvalidArgument;
                        }

                        for (int aperture = 0; aperture < input.aperture_count; ++aperture) {
                            const auto& runtime = apertures[static_cast<std::size_t>(aperture)];
                            if (runtime.psf_index != psf) {
                                continue;
                            }
                            if (!find_boxed_aperture_pixels(
                                    matrix_value(input.ap_begin, input.aperture_count, aperture, 0),
                                    matrix_value(input.ap_begin, input.aperture_count, aperture, 1),
                                    matrix_value(input.ap_size, input.aperture_count, aperture, 0),
                                    matrix_value(input.ap_size, input.aperture_count, aperture, 1),
                                    input.ap_rot[aperture],
                                    input.ap_binx[aperture],
                                    input.ap_biny[aperture],
                                    psi_radians,
                                    mge.conversion_factor,
                                    input.sampling,
                                    convolved_x.data(),
                                    convolved_y.data(),
                                    aperture_pixels.data()
                                )) {
                                return kStatusInvalidArgument;
                            }
                            if (!accumulate_losvd_histogram(
                                    runtime.source_pixel_count,
                                    runtime.velocity_bin_count,
                                    input.sampling,
                                    aperture_pixels.data(),
                                    velocity_bins.data(),
                                    input.sampling,
                                    source_histograms[static_cast<std::size_t>(aperture)].data(),
                                    &stored_counts[static_cast<std::size_t>(aperture)]
                                )) {
                                return kStatusInvalidArgument;
                            }
                        }
                    }
                }
            }

            if (!normalize_qgrid(input.n_radius, input.n_theta, input.n_phi, orbit_qgrid)) {
                return kStatusInvalidArgument;
            }

            for (int aperture = 0; aperture < input.aperture_count; ++aperture) {
                const auto& runtime = apertures[static_cast<std::size_t>(aperture)];
                auto& source = source_histograms[static_cast<std::size_t>(aperture)];
                auto& target = target_histograms[static_cast<std::size_t>(aperture)];
                if (runtime.binning_type == 1) {
                    if (!collapse_losvd_binning(
                            runtime.source_pixel_count,
                            runtime.velocity_bin_count,
                            runtime.target_pixel_count,
                            input.bin_order + static_cast<std::size_t>(input.max_bin_size) * static_cast<std::size_t>(aperture),
                            source.data(),
                            target.data()
                        )) {
                        return kStatusInvalidArgument;
                    }
                } else {
                    std::copy(source.begin(), source.end(), target.begin());
                }
                if (!normalize_losvd_histogram(
                        runtime.target_pixel_count,
                        runtime.velocity_bin_count,
                        stored_counts[static_cast<std::size_t>(aperture)],
                        target.data()
                    )) {
                    return kStatusInvalidArgument;
                }

                if (runtime.histogram_dim == 1) {
                    if (!compute_sparse_losvd_ranges(
                            runtime.target_pixel_count,
                            runtime.velocity_bin_count,
                            target.data(),
                            sparse_begin.data(),
                            sparse_end.data()
                        )) {
                        return kStatusInvalidArgument;
                    }
                    for (int row = 0; row < runtime.target_pixel_count; ++row) {
                        const int output_row =
                            orbit_index * losvd_rows_per_orbit + runtime.losvd_row_offset + row;
                        losvd_begin_offsets[static_cast<std::size_t>(output_row)] =
                            sparse_begin[static_cast<std::size_t>(row)];
                        losvd_end_offsets[static_cast<std::size_t>(output_row)] =
                            sparse_end[static_cast<std::size_t>(row)];
                        double* destination =
                            losvd_histograms.data() +
                            static_cast<std::size_t>(output_row) * static_cast<std::size_t>(max_velocity_bin_count);
                        const double* source_row =
                            target.data() +
                            static_cast<std::size_t>(row) * static_cast<std::size_t>(runtime.velocity_bin_count);
                        std::copy(
                            source_row,
                            source_row + runtime.velocity_bin_count,
                            destination
                        );
                    }
                } else if (pops_total_rows > 0) {
                    double* destination =
                        population_masses.data() +
                        static_cast<std::size_t>(orbit_index) * static_cast<std::size_t>(pops_total_rows) +
                        static_cast<std::size_t>(runtime.pops_row_offset);
                    for (int row = 0; row < runtime.target_pixel_count; ++row) {
                        destination[row] = target[
                            static_cast<std::size_t>(row) * static_cast<std::size_t>(runtime.velocity_bin_count)
                        ];
                    }
                }
            }
        }

        if (!write_qgrid_file_with_not_regularizable_counts(
                input.out_qgrid_path,
                full_orbit_count,
                input.nener,
                input.ni2,
                input.ni3,
                input.orbit_dithering,
                not_regularizable_counts.data(),
                input.n_radius,
                input.n_theta,
                input.n_phi,
                radius_boundaries.data(),
                theta_boundaries.data(),
                phi_boundaries.data(),
                orbit_types.data(),
                qgrids.data()
            )) {
            return kStatusIoError;
        }
        if (!write_losvd_histogram_file_mixed(
                input.out_losvd_path,
                full_orbit_count,
                losvd_rows_per_orbit,
                max_velocity_bin_count,
                row_velocity_bin_counts.data(),
                losvd_header_bin_width,
                losvd_begin_offsets.data(),
                losvd_end_offsets.data(),
                losvd_histograms.data()
            )) {
            return kStatusIoError;
        }
        if (pops_population_count > 0 &&
            !write_population_mass_file(
                input.out_pops_path,
                full_orbit_count,
                pops_population_count,
                population_aperture_counts.data(),
                population_masses.data()
            )) {
            return kStatusIoError;
        }
        if (!write_orbit_class_file(
                input.out_orbclass_path,
                full_orbit_count,
                dither_count,
                moments.data()
            )) {
            return kStatusIoError;
        }

        return kStatusOk;
    } catch (...) {
        return kStatusException;
    }
}

}  // namespace dynamite::orblib_cpp
