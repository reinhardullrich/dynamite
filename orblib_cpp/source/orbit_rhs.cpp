#include "orbit_rhs.hpp"

namespace dynamite::orblib_cpp {

bool evaluate_orbit_rhs(
    InterpolatedPotential& potential,
    double omega,
    const double state[6],
    double derivative[6]
) noexcept {
    double accel_x = 0.0;
    double accel_y = 0.0;
    double accel_z = 0.0;
    if (!potential.evaluate_acceleration(state[0], state[1], state[2], accel_x, accel_y, accel_z)) {
        return false;
    }

    if (omega == 0.0) {
        derivative[0] = state[3];
        derivative[1] = state[4];
        derivative[2] = state[5];
        derivative[3] = accel_x;
        derivative[4] = accel_y;
        derivative[5] = accel_z;
        return true;
    }

    derivative[0] = state[3] + omega * state[1];
    derivative[1] = state[4] - omega * state[0];
    derivative[2] = state[5];
    derivative[3] = accel_x + omega * state[4];
    derivative[4] = accel_y - omega * state[3];
    derivative[5] = accel_z;
    return true;
}

}  // namespace dynamite::orblib_cpp
