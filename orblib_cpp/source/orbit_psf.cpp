#include "orbit_psf.hpp"

#include "ran1.hpp"

#include <cmath>
#include <vector>

namespace dynamite::orblib_cpp {
namespace {

int nint_positive(double value) noexcept {
    return static_cast<int>(std::floor(value + 0.5));
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

bool build_sigma_map(
    int gaussian_count,
    const double* weights,
    const double* sigmas,
    double sigma_scale,
    int sample_count,
    std::vector<double>& sigma_map
) {
    sigma_map.assign(static_cast<std::size_t>(sample_count), 0.0);
    std::vector<double> absolute_weights(static_cast<std::size_t>(gaussian_count), 0.0);
    double weight_sum = 0.0;
    for (int i = 0; i < gaussian_count; ++i) {
        absolute_weights[static_cast<std::size_t>(i)] = std::abs(weights[i]);
        weight_sum += absolute_weights[static_cast<std::size_t>(i)];
    }
    if (weight_sum <= 0.0) {
        return false;
    }

    std::vector<int> weight_index(static_cast<std::size_t>(gaussian_count + 1), 1);
    double cumulative_weight = 0.0;
    for (int i = 0; i < gaussian_count; ++i) {
        cumulative_weight += absolute_weights[static_cast<std::size_t>(i)];
        weight_index[static_cast<std::size_t>(i + 1)] =
            nint_positive(cumulative_weight * (static_cast<double>(sample_count - 1) / weight_sum)) +
            1;
    }
    weight_index.front() = 1;
    weight_index.back() = sample_count;

    for (int i = 0; i < gaussian_count; ++i) {
        const double sigma = sigmas[i] * sigma_scale;
        const int first = weight_index[static_cast<std::size_t>(i)];
        const int last = weight_index[static_cast<std::size_t>(i + 1)];
        for (int j = first; j <= last; ++j) {
            sigma_map[static_cast<std::size_t>(j - 1)] = sigma;
        }
    }
    return true;
}

}  // namespace

bool apply_psf_to_projected_samples(
    int gaussian_count,
    const double* weights,
    const double* sigmas,
    double sigma_scale,
    int sample_count,
    const double* projected_x,
    const double* projected_y,
    int seed,
    double* convolved_x,
    double* convolved_y
) noexcept {
    if (gaussian_count < 1 || weights == nullptr || sigmas == nullptr || sample_count < 0 ||
        projected_x == nullptr || projected_y == nullptr || convolved_x == nullptr ||
        convolved_y == nullptr) {
        return false;
    }

    Ran1 rng(seed);
    if (gaussian_count == 1) {
        const double sigma = sigmas[0] * sigma_scale;
        if (sigma > 1.0) {
            for (int i = 0; i < sample_count; ++i) {
                double dx = 0.0;
                double dy = 0.0;
                gaussian_pair(rng, dx, dy);
                convolved_x[i] = projected_x[i] + dx * sigma;
                convolved_y[i] = projected_y[i] + dy * sigma;
            }
        } else {
            for (int i = 0; i < sample_count; ++i) {
                convolved_x[i] = projected_x[i];
                convolved_y[i] = projected_y[i];
            }
        }
        return true;
    }

    std::vector<double> sigma_map;
    if (!build_sigma_map(gaussian_count, weights, sigmas, sigma_scale, sample_count, sigma_map)) {
        return false;
    }

    std::vector<double> gaussian_x(static_cast<std::size_t>(sample_count), 0.0);
    std::vector<double> gaussian_y(static_cast<std::size_t>(sample_count), 0.0);
    for (int i = 0; i < sample_count; ++i) {
        gaussian_pair(rng, gaussian_x[static_cast<std::size_t>(i)], gaussian_y[static_cast<std::size_t>(i)]);
    }
    for (int i = 0; i < sample_count; ++i) {
        const float selector = static_cast<float>(rng.next());
        const int sigma_index =
            static_cast<int>(selector * static_cast<float>(sample_count - 1) + 1.0f);
        const double sigma = sigma_map[static_cast<std::size_t>(sigma_index - 1)];
        convolved_x[i] = projected_x[i] + gaussian_x[static_cast<std::size_t>(i)] * sigma;
        convolved_y[i] = projected_y[i] + gaussian_y[static_cast<std::size_t>(i)] * sigma;
    }
    return true;
}

}  // namespace dynamite::orblib_cpp
