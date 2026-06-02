#pragma once

namespace dynamite::orblib_cpp {

bool elliptic_f(double phi, double modulus, double& result) noexcept;
bool elliptic_e(double phi, double modulus, double& result) noexcept;

}  // namespace dynamite::orblib_cpp
