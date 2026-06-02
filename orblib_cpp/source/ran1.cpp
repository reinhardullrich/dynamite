#include "ran1.hpp"

#include <algorithm>

namespace dynamite::orblib_cpp {

Ran1::Ran1(int seed) noexcept {
    initialize(seed);
}

void Ran1::initialize(int seed) noexcept {
    int value = std::max(-seed, 1);
    for (int j = kNtab + 8; j >= 1; --j) {
        const int k = value / kIq;
        value = kIa * (value - k * kIq) - kIr * k;
        if (value < 0) {
            value += kIm;
        }
        if (j <= kNtab) {
            iv_[static_cast<std::size_t>(j - 1)] = value;
        }
    }
    iy_ = iv_[0];
    idum_ = value;
}

double Ran1::next() noexcept {
    const int k = idum_ / kIq;
    idum_ = kIa * (idum_ - k * kIq) - kIr * k;
    if (idum_ < 0) {
        idum_ += kIm;
    }

    const int j = iy_ / kNdiv;
    iy_ = iv_[static_cast<std::size_t>(j)];
    iv_[static_cast<std::size_t>(j)] = idum_;
    return std::min(kAm * static_cast<double>(iy_), kRnmx);
}

}  // namespace dynamite::orblib_cpp
