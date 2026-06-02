#pragma once

#include <array>

namespace dynamite::orblib_cpp {

class Ran1 {
public:
    explicit Ran1(int seed) noexcept;

    double next() noexcept;

private:
    static constexpr int kIa = 16807;
    static constexpr int kIm = 2147483647;
    static constexpr int kIq = 127773;
    static constexpr int kIr = 2836;
    static constexpr int kNtab = 32;
    static constexpr int kNdiv = 1 + (kIm - 1) / kNtab;
    static constexpr double kAm = 1.0 / static_cast<double>(kIm);
    static constexpr double kRnmx = 1.0 - 2.23e-16;

    void initialize(int seed) noexcept;

    int idum_ = 1;
    int iy_ = 0;
    std::array<int, kNtab> iv_{};
};

}  // namespace dynamite::orblib_cpp
