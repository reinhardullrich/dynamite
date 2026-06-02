#include "elliptic_integrals.hpp"

#include <algorithm>
#include <cmath>

namespace dynamite::orblib_cpp {
namespace {

bool carlson_rf(double x, double y, double z, double& result) noexcept {
    constexpr double kErrTol = 1.0e-5;
    constexpr double kTiny = 1.5e-38;
    constexpr double kBig = 3.0e37;
    constexpr double kThird = 1.0 / 3.0;
    constexpr double kC1 = 1.0 / 24.0;
    constexpr double kC2 = 0.1;
    constexpr double kC3 = 3.0 / 44.0;
    constexpr double kC4 = 1.0 / 14.0;

    if (std::min({x, y, z}) < 0.0 || std::min({x + y, x + z, y + z}) < kTiny ||
        std::max({x, y, z}) > kBig) {
        return false;
    }

    double xt = x;
    double yt = y;
    double zt = z;
    double ave = 0.0;
    double delx = 0.0;
    double dely = 0.0;
    double delz = 0.0;

    for (;;) {
        const double sqrtx = std::sqrt(xt);
        const double sqrty = std::sqrt(yt);
        const double sqrtz = std::sqrt(zt);
        const double alamb = sqrtx * (sqrty + sqrtz) + sqrty * sqrtz;
        xt = 0.25 * (xt + alamb);
        yt = 0.25 * (yt + alamb);
        zt = 0.25 * (zt + alamb);
        ave = kThird * (xt + yt + zt);
        delx = (ave - xt) / ave;
        dely = (ave - yt) / ave;
        delz = (ave - zt) / ave;
        if (std::max({std::abs(delx), std::abs(dely), std::abs(delz)}) <= kErrTol) {
            break;
        }
    }

    const double e2 = delx * dely - delz * delz;
    const double e3 = delx * dely * delz;
    result = (1.0 + (kC1 * e2 - kC2 - kC3 * e3) * e2 + kC4 * e3) / std::sqrt(ave);
    return true;
}

bool carlson_rd(double x, double y, double z, double& result) noexcept {
    constexpr double kErrTol = 1.0e-5;
    constexpr double kTiny = 1.5e-25;
    constexpr double kBig = 4.5e21;
    constexpr double kC1 = 3.0 / 14.0;
    constexpr double kC2 = 1.0 / 6.0;
    constexpr double kC3 = 9.0 / 22.0;
    constexpr double kC4 = 3.0 / 26.0;
    constexpr double kC5 = 0.25 * kC3;
    constexpr double kC6 = 1.5 * kC4;

    if (std::min(x, y) < 0.0 || std::min(x + y, z) < kTiny || std::max({x, y, z}) > kBig) {
        return false;
    }

    double xt = x;
    double yt = y;
    double zt = z;
    double sum = 0.0;
    double fac = 1.0;
    double ave = 0.0;
    double delx = 0.0;
    double dely = 0.0;
    double delz = 0.0;

    for (;;) {
        const double sqrtx = std::sqrt(xt);
        const double sqrty = std::sqrt(yt);
        const double sqrtz = std::sqrt(zt);
        const double alamb = sqrtx * (sqrty + sqrtz) + sqrty * sqrtz;
        sum += fac / (sqrtz * (zt + alamb));
        fac *= 0.25;
        xt = 0.25 * (xt + alamb);
        yt = 0.25 * (yt + alamb);
        zt = 0.25 * (zt + alamb);
        ave = 0.2 * (xt + yt + 3.0 * zt);
        delx = (ave - xt) / ave;
        dely = (ave - yt) / ave;
        delz = (ave - zt) / ave;
        if (std::max({std::abs(delx), std::abs(dely), std::abs(delz)}) <= kErrTol) {
            break;
        }
    }

    const double ea = delx * dely;
    const double eb = delz * delz;
    const double ec = ea - eb;
    const double ed = ea - 6.0 * eb;
    const double ee = ed + ec + ec;
    result = 3.0 * sum +
             fac * (1.0 + ed * (-kC1 + kC5 * ed - kC6 * delz * ee) +
                    delz * (kC2 * ee + delz * (-kC3 * ec + delz * kC4 * ea))) /
                 (ave * std::sqrt(ave));
    return true;
}

}  // namespace

bool elliptic_f(double phi, double modulus, double& result) noexcept {
    const double s = std::sin(phi);
    double rf_value = 0.0;
    if (!carlson_rf(std::cos(phi) * std::cos(phi), (1.0 - s * modulus) * (1.0 + s * modulus), 1.0, rf_value)) {
        return false;
    }
    result = s * rf_value;
    return true;
}

bool elliptic_e(double phi, double modulus, double& result) noexcept {
    const double s = std::sin(phi);
    const double cos_squared = std::cos(phi) * std::cos(phi);
    const double q = (1.0 - s * modulus) * (1.0 + s * modulus);
    double rf_value = 0.0;
    double rd_value = 0.0;
    if (!carlson_rf(cos_squared, q, 1.0, rf_value) ||
        !carlson_rd(cos_squared, q, 1.0, rd_value)) {
        return false;
    }
    result = s * (rf_value - ((s * modulus) * (s * modulus)) * rd_value / 3.0);
    return true;
}

}  // namespace dynamite::orblib_cpp
