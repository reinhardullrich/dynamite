#pragma once

#include "potential.hpp"

#include <vector>

namespace dynamite::orblib_cpp {

struct InterpolationGridConfig {
    int n_radius = 640;
    int n_theta = 64;
    int n_phi = 64;
    double rlogmin = 0.0;
    double rlogmax = 0.0;
};

struct InterpolationGridMetadata {
    double theta_step = 0.0;
    double phi_step = 0.0;
    double rlog_step = 0.0;
    double rlog_min = 0.0;
    double rmin2 = 0.0;
    double rmax2 = 0.0;
};

class InterpolatedPotential {
public:
    bool setup(
        const TriaxialMgeSetup& mge,
        const DarkHaloSetup& halo,
        double black_hole_mass,
        double black_hole_softening_km,
        const InterpolationGridConfig& config
    );

    bool evaluate_potential(
        double x,
        double y,
        double z,
        double& potential
    ) const noexcept;

    bool evaluate_acceleration(
        double x,
        double y,
        double z,
        double& accel_x,
        double& accel_y,
        double& accel_z
    ) noexcept;

    const InterpolationGridMetadata& metadata() const noexcept { return metadata_; }
    int inner_fallback_count() const noexcept { return inner_fallback_count_; }
    int outer_fallback_count() const noexcept { return outer_fallback_count_; }

private:
    std::size_t grid_index(int component, int phi, int theta, int radius) const noexcept;
    bool evaluate_direct_acceleration(
        double x,
        double y,
        double z,
        double& accel_x,
        double& accel_y,
        double& accel_z
    ) const noexcept;

    TriaxialMgeSetup mge_;
    DarkHaloSetup halo_;
    double black_hole_mass_ = 0.0;
    double black_hole_softening_km_ = 0.0;
    int n_radius_ = 0;
    int n_theta_ = 0;
    int n_phi_ = 0;
    InterpolationGridMetadata metadata_;
    std::vector<double> grid_;
    int inner_fallback_count_ = 0;
    int outer_fallback_count_ = 0;
};

}  // namespace dynamite::orblib_cpp
