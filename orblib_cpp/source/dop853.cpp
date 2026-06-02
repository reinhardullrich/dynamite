#include "dop853.hpp"

#include <algorithm>
#include <cmath>
#include <limits>

namespace dynamite::orblib_cpp {
namespace {

constexpr int kStatusSuccess = 1;
constexpr int kStatusInterrupted = 2;
constexpr int kStatusInvalidInput = -1;
constexpr int kStatusTooManySteps = -2;
constexpr int kStatusStepTooSmall = -3;
constexpr int kStatusProbablyStiff = -4;

constexpr double c2 = 0.526001519587677318785587544488e-1;
constexpr double c3 = 0.789002279381515978178381316732e-1;
constexpr double c4 = 0.118350341907227396726757197510e+0;
constexpr double c5 = 0.281649658092772603273242802490e+0;
constexpr double c6 = 0.333333333333333333333333333333e+0;
constexpr double c7 = 0.25e+0;
constexpr double c8 = 0.307692307692307692307692307692e+0;
constexpr double c9 = 0.651282051282051282051282051282e+0;
constexpr double c10 = 0.6e+0;
constexpr double c11 = 0.857142857142857142857142857142e+0;
constexpr double c14 = 0.1e+0;
constexpr double c15 = 0.2e+0;
constexpr double c16 = 0.777777777777777777777777777778e+0;

constexpr double b1 = 5.42937341165687622380535766363e-2;
constexpr double b6 = 4.45031289275240888144113950566e+0;
constexpr double b7 = 1.89151789931450038304281599044e+0;
constexpr double b8 = -5.8012039600105847814672114227e+0;
constexpr double b9 = 3.1116436695781989440891606237e-1;
constexpr double b10 = -1.52160949662516078556178806805e-1;
constexpr double b11 = 2.01365400804030348374776537501e-1;
constexpr double b12 = 4.47106157277725905176885569043e-2;

constexpr double bhh1 = 0.244094488188976377952755905512e+0;
constexpr double bhh2 = 0.733846688281611857341361741547e+0;
constexpr double bhh3 = 0.220588235294117647058823529412e-1;

constexpr double er1 = 0.1312004499419488073250102996e-1;
constexpr double er6 = -0.1225156446376204440720569753e+1;
constexpr double er7 = -0.4957589496572501915214079952e+0;
constexpr double er8 = 0.1664377182454986536961530415e+1;
constexpr double er9 = -0.3503288487499736816886487290e+0;
constexpr double er10 = 0.3341791187130174790297318841e+0;
constexpr double er11 = 0.8192320648511571246570742613e-1;
constexpr double er12 = -0.2235530786388629525884427845e-1;

constexpr double a21 = 5.26001519587677318785587544488e-2;
constexpr double a31 = 1.97250569845378994544595329183e-2;
constexpr double a32 = 5.91751709536136983633785987549e-2;
constexpr double a41 = 2.95875854768068491816892993775e-2;
constexpr double a43 = 8.87627564304205475450678981324e-2;
constexpr double a51 = 2.41365134159266685502369798665e-1;
constexpr double a53 = -8.84549479328286085344864962717e-1;
constexpr double a54 = 9.24834003261792003115737966543e-1;
constexpr double a61 = 3.7037037037037037037037037037e-2;
constexpr double a64 = 1.70828608729473871279604482173e-1;
constexpr double a65 = 1.25467687566822425016691814123e-1;
constexpr double a71 = 3.7109375e-2;
constexpr double a74 = 1.70252211019544039314978060272e-1;
constexpr double a75 = 6.02165389804559606850219397283e-2;
constexpr double a76 = -1.7578125e-2;
constexpr double a81 = 3.70920001185047927108779319836e-2;
constexpr double a84 = 1.70383925712239993810214054705e-1;
constexpr double a85 = 1.07262030446373284651809199168e-1;
constexpr double a86 = -1.53194377486244017527936158236e-2;
constexpr double a87 = 8.27378916381402288758473766002e-3;
constexpr double a91 = 6.24110958716075717114429577812e-1;
constexpr double a94 = -3.36089262944694129406857109825e+0;
constexpr double a95 = -8.68219346841726006818189891453e-1;
constexpr double a96 = 2.75920996994467083049415600797e+1;
constexpr double a97 = 2.01540675504778934086186788979e+1;
constexpr double a98 = -4.34898841810699588477366255144e+1;
constexpr double a101 = 4.77662536438264365890433908527e-1;
constexpr double a104 = -2.48811461997166764192642586468e+0;
constexpr double a105 = -5.90290826836842996371446475743e-1;
constexpr double a106 = 2.12300514481811942347288949897e+1;
constexpr double a107 = 1.52792336328824235832596922938e+1;
constexpr double a108 = -3.32882109689848629194453265587e+1;
constexpr double a109 = -2.03312017085086261358222928593e-2;
constexpr double a111 = -9.3714243008598732571704021658e-1;
constexpr double a114 = 5.18637242884406370830023853209e+0;
constexpr double a115 = 1.09143734899672957818500254654e+0;
constexpr double a116 = -8.14978701074692612513997267357e+0;
constexpr double a117 = -1.85200656599969598641566180701e+1;
constexpr double a118 = 2.27394870993505042818970056734e+1;
constexpr double a119 = 2.49360555267965238987089396762e+0;
constexpr double a1110 = -3.0467644718982195003823669022e+0;
constexpr double a121 = 2.27331014751653820792359768449e+0;
constexpr double a124 = -1.05344954667372501984066689879e+1;
constexpr double a125 = -2.00087205822486249909675718444e+0;
constexpr double a126 = -1.79589318631187989172765950534e+1;
constexpr double a127 = 2.79488845294199600508499808837e+1;
constexpr double a128 = -2.85899827713502369474065508674e+0;
constexpr double a129 = -8.87285693353062954433549289258e+0;
constexpr double a1210 = 1.23605671757943030647266201528e+1;
constexpr double a1211 = 6.43392746015763530355970484046e-1;
constexpr double a141 = 5.61675022830479523392909219681e-2;
constexpr double a147 = 2.53500210216624811088794765333e-1;
constexpr double a148 = -2.46239037470802489917441475441e-1;
constexpr double a149 = -1.24191423263816360469010140626e-1;
constexpr double a1410 = 1.5329179827876569731206322685e-1;
constexpr double a1411 = 8.20105229563468988491666602057e-3;
constexpr double a1412 = 7.56789766054569976138603589584e-3;
constexpr double a1413 = -8.298e-3;
constexpr double a151 = 3.18346481635021405060768473261e-2;
constexpr double a156 = 2.83009096723667755288322961402e-2;
constexpr double a157 = 5.35419883074385676223797384372e-2;
constexpr double a158 = -5.49237485713909884646569340306e-2;
constexpr double a1511 = -1.08347328697249322858509316994e-4;
constexpr double a1512 = 3.82571090835658412954920192323e-4;
constexpr double a1513 = -3.40465008687404560802977114492e-4;
constexpr double a1514 = 1.41312443674632500278074618366e-1;
constexpr double a161 = -4.28896301583791923408573538692e-1;
constexpr double a166 = -4.69762141536116384314449447206e+0;
constexpr double a167 = 7.68342119606259904184240953878e+0;
constexpr double a168 = 4.06898981839711007970213554331e+0;
constexpr double a169 = 3.56727187455281109270669543021e-1;
constexpr double a1613 = -1.39902416515901462129418009734e-3;
constexpr double a1614 = 2.9475147891527723389556272149e+0;
constexpr double a1615 = -9.15095847217987001081870187138e+0;

constexpr double d41 = -0.84289382761090128651353491142e+1;
constexpr double d46 = 0.56671495351937776962531783590e+0;
constexpr double d47 = -0.30689499459498916912797304727e+1;
constexpr double d48 = 0.23846676565120698287728149680e+1;
constexpr double d49 = 0.21170345824450282767155149946e+1;
constexpr double d410 = -0.87139158377797299206789907490e+0;
constexpr double d411 = 0.22404374302607882758541771650e+1;
constexpr double d412 = 0.63157877876946881815570249290e+0;
constexpr double d413 = -0.88990336451333310820698117400e-1;
constexpr double d414 = 0.18148505520854727256656404962e+2;
constexpr double d415 = -0.91946323924783554000451984436e+1;
constexpr double d416 = -0.44360363875948939664310572000e+1;
constexpr double d51 = 0.10427508642579134603413151009e+2;
constexpr double d56 = 0.24228349177525818288430175319e+3;
constexpr double d57 = 0.16520045171727028198505394887e+3;
constexpr double d58 = -0.37454675472269020279518312152e+3;
constexpr double d59 = -0.22113666853125306036270938578e+2;
constexpr double d510 = 0.77334326684722638389603898808e+1;
constexpr double d511 = -0.30674084731089398182061213626e+2;
constexpr double d512 = -0.93321305264302278729567221706e+1;
constexpr double d513 = 0.15697238121770843886131091075e+2;
constexpr double d514 = -0.31139403219565177677282850411e+2;
constexpr double d515 = -0.93529243588444783865713862664e+1;
constexpr double d516 = 0.35816841486394083752465898540e+2;
constexpr double d61 = 0.19985053242002433820987653617e+2;
constexpr double d66 = -0.38703730874935176555105901742e+3;
constexpr double d67 = -0.18917813819516756882830838328e+3;
constexpr double d68 = 0.52780815920542364900561016686e+3;
constexpr double d69 = -0.11573902539959630126141871134e+2;
constexpr double d610 = 0.68812326946963000169666922661e+1;
constexpr double d611 = -0.10006050966910838403183860980e+1;
constexpr double d612 = 0.77771377980534432092869265740e+0;
constexpr double d613 = -0.27782057523535084065932004339e+1;
constexpr double d614 = -0.60196695231264120758267380846e+2;
constexpr double d615 = 0.84320405506677161018159903784e+2;
constexpr double d616 = 0.11992291136182789328035130030e+2;
constexpr double d71 = -0.25693933462703749003312586129e+2;
constexpr double d76 = -0.15418974869023643374053993627e+3;
constexpr double d77 = -0.23152937917604549567536039109e+3;
constexpr double d78 = 0.35763911791061412378285349910e+3;
constexpr double d79 = 0.93405324183624310003907691704e+2;
constexpr double d710 = -0.37458323136451633156875139351e+2;
constexpr double d711 = 0.10409964950896230045147246184e+3;
constexpr double d712 = 0.29840293426660503123344363579e+2;
constexpr double d713 = -0.43533456590011143754432175058e+2;
constexpr double d714 = 0.96324553959188282948394950600e+2;
constexpr double d715 = -0.39177261675615439165231486172e+2;
constexpr double d716 = -0.14972683625798562581422125276e+3;

double signed_step(double magnitude, double direction) noexcept {
    return std::copysign(std::abs(magnitude), direction);
}

}  // namespace

void Dop853::ensure_workspace(int n, int dense_components) {
    if (n == n_ && dense_components == dense_components_) {
        return;
    }

    n_ = n;
    dense_components_ = dense_components;
    k1_.assign(static_cast<std::size_t>(n), 0.0);
    k2_.assign(static_cast<std::size_t>(n), 0.0);
    k3_.assign(static_cast<std::size_t>(n), 0.0);
    k4_.assign(static_cast<std::size_t>(n), 0.0);
    k5_.assign(static_cast<std::size_t>(n), 0.0);
    k6_.assign(static_cast<std::size_t>(n), 0.0);
    k7_.assign(static_cast<std::size_t>(n), 0.0);
    k8_.assign(static_cast<std::size_t>(n), 0.0);
    k9_.assign(static_cast<std::size_t>(n), 0.0);
    k10_.assign(static_cast<std::size_t>(n), 0.0);
    y1_.assign(static_cast<std::size_t>(n), 0.0);
    cont_.assign(static_cast<std::size_t>(8 * dense_components), 0.0);
    components_.resize(static_cast<std::size_t>(dense_components));
    for (int i = 0; i < dense_components; ++i) {
        components_[static_cast<std::size_t>(i)] = i;
    }
}

double Dop853::initial_step(
    int n,
    double x,
    const double* y,
    double,
    double posneg,
    double max_step,
    double atol,
    double rtol,
    Dop853Rhs rhs,
    void* rhs_context
) {
    double dnf = 0.0;
    double dny = 0.0;
    for (int i = 0; i < n; ++i) {
        const double sk = atol + rtol * std::abs(y[i]);
        dnf += (k1_[static_cast<std::size_t>(i)] / sk) * (k1_[static_cast<std::size_t>(i)] / sk);
        dny += (y[i] / sk) * (y[i] / sk);
    }

    double h = 0.0;
    if (dnf <= 1.0e-10 || dny <= 1.0e-10) {
        h = 1.0e-6;
    } else {
        h = std::sqrt(dny / dnf) * 0.01;
    }
    h = std::min(h, max_step);
    h = signed_step(h, posneg);

    for (int i = 0; i < n; ++i) {
        y1_[static_cast<std::size_t>(i)] = y[i] + h * k1_[static_cast<std::size_t>(i)];
    }
    rhs(n, x + h, y1_.data(), k2_.data(), rhs_context);

    double der2 = 0.0;
    for (int i = 0; i < n; ++i) {
        const double sk = atol + rtol * std::abs(y[i]);
        const double value = (k2_[static_cast<std::size_t>(i)] - k1_[static_cast<std::size_t>(i)]) / sk;
        der2 += value * value;
    }
    der2 = std::sqrt(der2) / h;

    const double der12 = std::max(std::abs(der2), std::sqrt(dnf));
    double h1 = 0.0;
    if (der12 <= 1.0e-15) {
        h1 = std::max(1.0e-6, std::abs(h) * 1.0e-3);
    } else {
        h1 = std::pow(0.01 / der12, 1.0 / 8.0);
    }
    h = std::min({100.0 * std::abs(h), h1, max_step});
    return signed_step(h, posneg);
}

double Dop853::dense_value(int component, double x) const noexcept {
    int dense_index = -1;
    for (int j = 0; j < dense_components_; ++j) {
        if (components_[static_cast<std::size_t>(j)] == component) {
            dense_index = j;
            break;
        }
    }
    if (dense_index < 0 || dense_step_ == 0.0) {
        return std::numeric_limits<double>::quiet_NaN();
    }

    const int i = dense_index;
    const int nd = dense_components_;
    const double s = (x - x_old_) / dense_step_;
    const double s1 = 1.0 - s;
    const auto at = [&](int block) noexcept -> double {
        return cont_[static_cast<std::size_t>(i + nd * block)];
    };
    const double conpar = at(4) + s * (at(5) + s1 * (at(6) + s * at(7)));
    return at(0) + s * (at(1) + s1 * (at(2) + s * (at(3) + s1 * conpar)));
}

Dop853Result Dop853::integrate(
    int n,
    double& x,
    double* y,
    double x_end,
    Dop853Rhs rhs,
    void* rhs_context,
    const Dop853Options& options,
    Dop853Solout solout,
    void* solout_context
) {
    Dop853Result result;

    if (n <= 0 || y == nullptr || rhs == nullptr || options.rtol <= 0.0 || options.atol <= 0.0 ||
        options.uround <= 1.0e-35 || options.uround >= 1.0 || options.safety >= 1.0 ||
        options.safety <= 1.0e-4 || options.fac1 <= 0.0 || options.fac2 <= 0.0 ||
        options.beta > 0.2 || options.max_steps <= 0 || options.dense_components < 0 ||
        options.dense_components > n) {
        result.status = kStatusInvalidInput;
        return result;
    }

    const int dense_components = options.dense_components;
    ensure_workspace(n, dense_components);

    int nstiff = options.stiffness_check_interval;
    if (nstiff == 0) {
        nstiff = 1000;
    }
    if (nstiff < 0) {
        nstiff = options.max_steps + 10;
    }

    const double beta = options.beta < 0.0 ? 0.0 : options.beta;
    const double fac1 = options.fac1;
    const double fac2 = options.fac2;
    const double facc1 = 1.0 / fac1;
    const double facc2 = 1.0 / fac2;
    const double expo1 = 1.0 / 8.0 - beta * 0.2;
    const double posneg = std::copysign(1.0, x_end - x);
    double max_step = options.max_step == 0.0 ? x_end - x : options.max_step;
    max_step = std::abs(max_step);
    double h = options.initial_step;
    bool reject = false;
    bool last = false;
    int nonsti = 0;
    int iasti = 0;
    double hlamb = 0.0;
    double facold = 1.0e-4;
    int observer_signal = 1;

    rhs(n, x, y, k1_.data(), rhs_context);
    result.function_evaluations += 1;
    if (h == 0.0) {
        h = initial_step(n, x, y, x_end, posneg, max_step, options.atol, options.rtol, rhs, rhs_context);
        result.function_evaluations += 1;
    }

    x_old_ = x;
    dense_step_ = 1.0;
    if (solout != nullptr) {
        observer_signal = solout(result.accepted_steps + 1, x_old_, x, y, n, *this, solout_context);
        if (observer_signal < 0) {
            result.status = kStatusInterrupted;
            result.suggested_step = h;
            return result;
        }
    }

    for (;;) {
        if (result.computed_steps > options.max_steps) {
            result.status = kStatusTooManySteps;
            result.suggested_step = h;
            return result;
        }
        if (0.1 * std::abs(h) <= std::abs(x) * options.uround) {
            result.status = kStatusStepTooSmall;
            result.suggested_step = h;
            return result;
        }
        if ((x + 1.01 * h - x_end) * posneg > 0.0) {
            h = x_end - x;
            last = true;
        }

        result.computed_steps += 1;
        if (observer_signal >= 2) {
            rhs(n, x, y, k1_.data(), rhs_context);
            result.function_evaluations += 1;
        }

        for (int i = 0; i < n; ++i) {
            const auto idx = static_cast<std::size_t>(i);
            y1_[idx] = y[i] + h * a21 * k1_[idx];
        }
        rhs(n, x + c2 * h, y1_.data(), k2_.data(), rhs_context);

        for (int i = 0; i < n; ++i) {
            const auto idx = static_cast<std::size_t>(i);
            y1_[idx] = y[i] + h * (a31 * k1_[idx] + a32 * k2_[idx]);
        }
        rhs(n, x + c3 * h, y1_.data(), k3_.data(), rhs_context);

        for (int i = 0; i < n; ++i) {
            const auto idx = static_cast<std::size_t>(i);
            y1_[idx] = y[i] + h * (a41 * k1_[idx] + a43 * k3_[idx]);
        }
        rhs(n, x + c4 * h, y1_.data(), k4_.data(), rhs_context);

        for (int i = 0; i < n; ++i) {
            const auto idx = static_cast<std::size_t>(i);
            y1_[idx] = y[i] + h * (a51 * k1_[idx] + a53 * k3_[idx] + a54 * k4_[idx]);
        }
        rhs(n, x + c5 * h, y1_.data(), k5_.data(), rhs_context);

        for (int i = 0; i < n; ++i) {
            const auto idx = static_cast<std::size_t>(i);
            y1_[idx] = y[i] + h * (a61 * k1_[idx] + a64 * k4_[idx] + a65 * k5_[idx]);
        }
        rhs(n, x + c6 * h, y1_.data(), k6_.data(), rhs_context);

        for (int i = 0; i < n; ++i) {
            const auto idx = static_cast<std::size_t>(i);
            y1_[idx] = y[i] + h * (a71 * k1_[idx] + a74 * k4_[idx] + a75 * k5_[idx] + a76 * k6_[idx]);
        }
        rhs(n, x + c7 * h, y1_.data(), k7_.data(), rhs_context);

        for (int i = 0; i < n; ++i) {
            const auto idx = static_cast<std::size_t>(i);
            y1_[idx] = y[i] + h * (a81 * k1_[idx] + a84 * k4_[idx] + a85 * k5_[idx] +
                                   a86 * k6_[idx] + a87 * k7_[idx]);
        }
        rhs(n, x + c8 * h, y1_.data(), k8_.data(), rhs_context);

        for (int i = 0; i < n; ++i) {
            const auto idx = static_cast<std::size_t>(i);
            y1_[idx] = y[i] + h * (a91 * k1_[idx] + a94 * k4_[idx] + a95 * k5_[idx] +
                                   a96 * k6_[idx] + a97 * k7_[idx] + a98 * k8_[idx]);
        }
        rhs(n, x + c9 * h, y1_.data(), k9_.data(), rhs_context);

        for (int i = 0; i < n; ++i) {
            const auto idx = static_cast<std::size_t>(i);
            y1_[idx] = y[i] + h * (a101 * k1_[idx] + a104 * k4_[idx] + a105 * k5_[idx] +
                                   a106 * k6_[idx] + a107 * k7_[idx] + a108 * k8_[idx] +
                                   a109 * k9_[idx]);
        }
        rhs(n, x + c10 * h, y1_.data(), k10_.data(), rhs_context);

        for (int i = 0; i < n; ++i) {
            const auto idx = static_cast<std::size_t>(i);
            y1_[idx] = y[i] + h * (a111 * k1_[idx] + a114 * k4_[idx] + a115 * k5_[idx] +
                                   a116 * k6_[idx] + a117 * k7_[idx] + a118 * k8_[idx] +
                                   a119 * k9_[idx] + a1110 * k10_[idx]);
        }
        rhs(n, x + c11 * h, y1_.data(), k2_.data(), rhs_context);

        const double xph = x + h;
        for (int i = 0; i < n; ++i) {
            const auto idx = static_cast<std::size_t>(i);
            y1_[idx] = y[i] + h * (a121 * k1_[idx] + a124 * k4_[idx] + a125 * k5_[idx] +
                                   a126 * k6_[idx] + a127 * k7_[idx] + a128 * k8_[idx] +
                                   a129 * k9_[idx] + a1210 * k10_[idx] + a1211 * k2_[idx]);
        }
        rhs(n, xph, y1_.data(), k3_.data(), rhs_context);
        result.function_evaluations += 11;

        for (int i = 0; i < n; ++i) {
            const auto idx = static_cast<std::size_t>(i);
            k4_[idx] = b1 * k1_[idx] + b6 * k6_[idx] + b7 * k7_[idx] + b8 * k8_[idx] +
                       b9 * k9_[idx] + b10 * k10_[idx] + b11 * k2_[idx] + b12 * k3_[idx];
            k5_[idx] = y[i] + h * k4_[idx];
        }

        double err = 0.0;
        double err2 = 0.0;
        for (int i = 0; i < n; ++i) {
            const auto idx = static_cast<std::size_t>(i);
            const double sk = options.atol + options.rtol * std::max(std::abs(y[i]), std::abs(k5_[idx]));
            double erri = k4_[idx] - bhh1 * k1_[idx] - bhh2 * k9_[idx] - bhh3 * k3_[idx];
            err2 += (erri / sk) * (erri / sk);
            erri = er1 * k1_[idx] + er6 * k6_[idx] + er7 * k7_[idx] + er8 * k8_[idx] +
                   er9 * k9_[idx] + er10 * k10_[idx] + er11 * k2_[idx] + er12 * k3_[idx];
            err += (erri / sk) * (erri / sk);
        }

        double deno = err + 0.01 * err2;
        if (deno <= 0.0) {
            deno = 1.0;
        }
        err = std::abs(h) * err * std::sqrt(1.0 / (static_cast<double>(n) * deno));
        const double fac11 = std::pow(err, expo1);
        double fac = fac11 / std::pow(facold, beta);
        fac = std::max(facc2, std::min(facc1, fac / options.safety));
        double hnew = h / fac;

        if (err <= 1.0) {
            facold = std::max(err, 1.0e-4);
            result.accepted_steps += 1;
            rhs(n, xph, k5_.data(), k4_.data(), rhs_context);
            result.function_evaluations += 1;

            if ((result.accepted_steps % nstiff == 0) || iasti > 0) {
                double stnum = 0.0;
                double stden = 0.0;
                for (int i = 0; i < n; ++i) {
                    const auto idx = static_cast<std::size_t>(i);
                    const double num = k4_[idx] - k3_[idx];
                    const double den = k5_[idx] - y1_[idx];
                    stnum += num * num;
                    stden += den * den;
                }
                if (stden > 0.0) {
                    hlamb = std::abs(h) * std::sqrt(stnum / stden);
                }
                if (hlamb > 6.1) {
                    nonsti = 0;
                    iasti += 1;
                    if (iasti == 15) {
                        result.status = kStatusProbablyStiff;
                        result.suggested_step = h;
                        return result;
                    }
                } else {
                    nonsti += 1;
                    if (nonsti == 6) {
                        iasti = 0;
                    }
                }
            }

            if (dense_components > 0 && solout != nullptr) {
                const int nd = dense_components;
                for (int j = 0; j < nd; ++j) {
                    const int i = components_[static_cast<std::size_t>(j)];
                    const auto idx = static_cast<std::size_t>(i);
                    const double ydiff = k5_[idx] - y[i];
                    const double bspl = h * k1_[idx] - ydiff;
                    cont_[static_cast<std::size_t>(j)] = y[i];
                    cont_[static_cast<std::size_t>(j + nd)] = ydiff;
                    cont_[static_cast<std::size_t>(j + nd * 2)] = bspl;
                    cont_[static_cast<std::size_t>(j + nd * 3)] = ydiff - h * k4_[idx] - bspl;
                    cont_[static_cast<std::size_t>(j + nd * 4)] =
                        d41 * k1_[idx] + d46 * k6_[idx] + d47 * k7_[idx] + d48 * k8_[idx] +
                        d49 * k9_[idx] + d410 * k10_[idx] + d411 * k2_[idx] + d412 * k3_[idx];
                    cont_[static_cast<std::size_t>(j + nd * 5)] =
                        d51 * k1_[idx] + d56 * k6_[idx] + d57 * k7_[idx] + d58 * k8_[idx] +
                        d59 * k9_[idx] + d510 * k10_[idx] + d511 * k2_[idx] + d512 * k3_[idx];
                    cont_[static_cast<std::size_t>(j + nd * 6)] =
                        d61 * k1_[idx] + d66 * k6_[idx] + d67 * k7_[idx] + d68 * k8_[idx] +
                        d69 * k9_[idx] + d610 * k10_[idx] + d611 * k2_[idx] + d612 * k3_[idx];
                    cont_[static_cast<std::size_t>(j + nd * 7)] =
                        d71 * k1_[idx] + d76 * k6_[idx] + d77 * k7_[idx] + d78 * k8_[idx] +
                        d79 * k9_[idx] + d710 * k10_[idx] + d711 * k2_[idx] + d712 * k3_[idx];
                }

                for (int i = 0; i < n; ++i) {
                    const auto idx = static_cast<std::size_t>(i);
                    y1_[idx] = y[i] + h * (a141 * k1_[idx] + a147 * k7_[idx] + a148 * k8_[idx] +
                                           a149 * k9_[idx] + a1410 * k10_[idx] + a1411 * k2_[idx] +
                                           a1412 * k3_[idx] + a1413 * k4_[idx]);
                }
                rhs(n, x + c14 * h, y1_.data(), k10_.data(), rhs_context);

                for (int i = 0; i < n; ++i) {
                    const auto idx = static_cast<std::size_t>(i);
                    y1_[idx] = y[i] + h * (a151 * k1_[idx] + a156 * k6_[idx] + a157 * k7_[idx] +
                                           a158 * k8_[idx] + a1511 * k2_[idx] + a1512 * k3_[idx] +
                                           a1513 * k4_[idx] + a1514 * k10_[idx]);
                }
                rhs(n, x + c15 * h, y1_.data(), k2_.data(), rhs_context);

                for (int i = 0; i < n; ++i) {
                    const auto idx = static_cast<std::size_t>(i);
                    y1_[idx] = y[i] + h * (a161 * k1_[idx] + a166 * k6_[idx] + a167 * k7_[idx] +
                                           a168 * k8_[idx] + a169 * k9_[idx] + a1613 * k4_[idx] +
                                           a1614 * k10_[idx] + a1615 * k2_[idx]);
                }
                rhs(n, x + c16 * h, y1_.data(), k3_.data(), rhs_context);
                result.function_evaluations += 3;

                for (int j = 0; j < nd; ++j) {
                    const int i = components_[static_cast<std::size_t>(j)];
                    const auto idx = static_cast<std::size_t>(i);
                    cont_[static_cast<std::size_t>(j + nd * 4)] =
                        h * (cont_[static_cast<std::size_t>(j + nd * 4)] + d413 * k4_[idx] +
                             d414 * k10_[idx] + d415 * k2_[idx] + d416 * k3_[idx]);
                    cont_[static_cast<std::size_t>(j + nd * 5)] =
                        h * (cont_[static_cast<std::size_t>(j + nd * 5)] + d513 * k4_[idx] +
                             d514 * k10_[idx] + d515 * k2_[idx] + d516 * k3_[idx]);
                    cont_[static_cast<std::size_t>(j + nd * 6)] =
                        h * (cont_[static_cast<std::size_t>(j + nd * 6)] + d613 * k4_[idx] +
                             d614 * k10_[idx] + d615 * k2_[idx] + d616 * k3_[idx]);
                    cont_[static_cast<std::size_t>(j + nd * 7)] =
                        h * (cont_[static_cast<std::size_t>(j + nd * 7)] + d713 * k4_[idx] +
                             d714 * k10_[idx] + d715 * k2_[idx] + d716 * k3_[idx]);
                }
                dense_step_ = h;
            }

            for (int i = 0; i < n; ++i) {
                const auto idx = static_cast<std::size_t>(i);
                k1_[idx] = k4_[idx];
                y[i] = k5_[idx];
            }
            x_old_ = x;
            x = xph;

            if (solout != nullptr) {
                observer_signal = solout(result.accepted_steps + 1, x_old_, x, y, n, *this, solout_context);
                if (observer_signal < 0) {
                    result.status = kStatusInterrupted;
                    result.suggested_step = h;
                    return result;
                }
            }

            if (last) {
                result.status = kStatusSuccess;
                result.suggested_step = hnew;
                return result;
            }
            if (std::abs(hnew) > max_step) {
                hnew = posneg * max_step;
            }
            if (reject) {
                hnew = posneg * std::min(std::abs(hnew), std::abs(h));
            }
            reject = false;
        } else {
            hnew = h / std::min(facc1, fac11 / options.safety);
            reject = true;
            if (result.accepted_steps >= 1) {
                result.rejected_steps += 1;
            }
            last = false;
        }
        h = hnew;
    }
}

}  // namespace dynamite::orblib_cpp
