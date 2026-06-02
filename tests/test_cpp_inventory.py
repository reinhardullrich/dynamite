import ctypes

import numpy as np
import pytest
import scipy.integrate
import scipy.io
import scipy.special

from conftest import (
    ORBLIB_CPP_DIR,
    ORBLIB_CPP_SHARED_LIBRARY,
    ORBLIB_FORTRAN_SHARED_LIBRARY,
)
from dynamite import orblib_api
from dynamite.myrand import MyRand


CPP_SOURCES = [
    "Makefile",
    "include/dop853.hpp",
    "include/elliptic_integrals.hpp",
    "include/interpolated_potential.hpp",
    "include/orbit_aperture.hpp",
    "include/orbit_classification.hpp",
    "include/orbit_histogram.hpp",
    "include/orbit_integrator.hpp",
    "include/orbit_output.hpp",
    "include/orbit_projection.hpp",
    "include/orbit_psf.hpp",
    "include/orbit_qgrid.hpp",
    "include/orbit_rhs.hpp",
    "include/orbit_start.hpp",
    "include/potential.hpp",
    "include/ran1.hpp",
    "include/triaxial_mge.hpp",
    "source/dop853.cpp",
    "source/elliptic_integrals.cpp",
    "source/interpolated_potential.cpp",
    "source/orbit_aperture.cpp",
    "source/orbit_classification.cpp",
    "source/orbit_histogram.cpp",
    "source/orbit_integrator.cpp",
    "source/orbit_output.cpp",
    "source/orbit_projection.cpp",
    "source/orbit_psf.cpp",
    "source/orbit_qgrid.cpp",
    "source/orbit_rhs.cpp",
    "source/orbit_start.cpp",
    "source/orblib_cpp_api.cpp",
    "source/potential.cpp",
    "source/ran1.cpp",
    "source/triaxial_mge.cpp",
]


PARSEC_KM = 1.4959787068e8 * (648e3 / np.pi)
GRAV_CONST_KM = 6.67428e-11 * 1.98892e30 / 1e9
RHO_CRIT = (3.0 * (7.0e-5 / PARSEC_KM) ** 2) / (8.0 * np.pi * GRAV_CONST_KM)


def test_cpp_backend_sources_are_present():
    missing = [
        source for source in CPP_SOURCES
        if not (ORBLIB_CPP_DIR / source).is_file()
    ]
    assert missing == []


@pytest.mark.orblib_cpp
def test_orblib_cpp_shared_library_is_built():
    assert ORBLIB_CPP_SHARED_LIBRARY.is_file()


@pytest.mark.orblib_cpp
def test_orblib_cpp_shared_library_reports_expected_abi_version():
    library = ctypes.CDLL(str(ORBLIB_CPP_SHARED_LIBRARY))
    abi_version = library.orblib_cpp_api_abi_version
    abi_version.argtypes = []
    abi_version.restype = ctypes.c_int
    assert abi_version() == orblib_api.CPP_SHARED_LIBRARY_ABI_VERSION


@pytest.mark.orblib_cpp
def test_orblib_cpp_ran1_matches_python_reference_sequence():
    count = 64
    values = np.empty(count, dtype=np.float64)
    status = ctypes.c_int(-999)
    library = ctypes.CDLL(str(ORBLIB_CPP_SHARED_LIBRARY))
    function = library.orblib_cpp_api_ran1_sequence
    function.argtypes = [
        ctypes.c_int,
        ctypes.c_int,
        ctypes.POINTER(ctypes.c_double),
        ctypes.POINTER(ctypes.c_int),
    ]
    function.restype = None

    function(
        ctypes.c_int(-4242),
        ctypes.c_int(count),
        values.ctypes.data_as(ctypes.POINTER(ctypes.c_double)),
        ctypes.byref(status),
    )

    python_rng = MyRand(-4242)
    expected = np.array([python_rng.ran1() for _ in range(count)])
    assert status.value == 0
    np.testing.assert_allclose(values, expected, rtol=0.0, atol=1e-15)


@pytest.mark.orblib_cpp
@pytest.mark.parametrize(
    ("phi", "modulus"),
    [
        (0.1, 0.0),
        (0.4, 0.2),
        (0.9, 0.5),
        (1.2, 0.8),
    ],
)
def test_orblib_cpp_elliptic_integrals_match_scipy(phi, modulus):
    value_f = ctypes.c_double(np.nan)
    value_e = ctypes.c_double(np.nan)
    status = ctypes.c_int(-999)
    library = ctypes.CDLL(str(ORBLIB_CPP_SHARED_LIBRARY))
    function = library.orblib_cpp_api_elliptic_legendre
    function.argtypes = [
        ctypes.c_double,
        ctypes.c_double,
        ctypes.POINTER(ctypes.c_double),
        ctypes.POINTER(ctypes.c_double),
        ctypes.POINTER(ctypes.c_int),
    ]
    function.restype = None

    function(
        ctypes.c_double(phi),
        ctypes.c_double(modulus),
        ctypes.byref(value_f),
        ctypes.byref(value_e),
        ctypes.byref(status),
    )

    assert status.value == 0
    np.testing.assert_allclose(
        value_f.value,
        scipy.special.ellipkinc(phi, modulus * modulus),
        rtol=0.0,
        atol=2e-12,
    )
    np.testing.assert_allclose(
        value_e.value,
        scipy.special.ellipeinc(phi, modulus * modulus),
        rtol=0.0,
        atol=2e-12,
    )


def _expected_triaxial_mge_setup(
    surf_pc,
    sigobs_arcsec,
    qobs,
    psi_obs,
    distance,
    theta,
    phi,
    psi,
    upsilon,
):
    theta_rad = np.deg2rad(theta)
    phi_rad = np.deg2rad(phi)
    psi_obs_rad = np.deg2rad(psi_obs + psi)
    conversion_factor = distance * 1.0e6 * np.tan(np.pi / 648e3) * PARSEC_KM
    surf_km = surf_pc / PARSEC_KM**2 * upsilon
    sigobs_km = sigobs_arcsec * conversion_factor
    delp = 1.0 - qobs**2
    secth = 1.0 / np.cos(theta_rad)
    cotph = 1.0 / np.tan(phi_rad)
    nom1minq2 = delp * (
        2.0 * np.cos(2.0 * psi_obs_rad)
        + np.sin(2.0 * psi_obs_rad)
        * (secth * cotph - np.cos(theta_rad) * np.tan(phi_rad))
    )
    nomp2minq2 = delp * (
        2.0 * np.cos(2.0 * psi_obs_rad)
        + np.sin(2.0 * psi_obs_rad)
        * (np.cos(theta_rad) * cotph - secth * np.tan(phi_rad))
    )
    denom = 2.0 * np.sin(theta_rad) ** 2 * (
        delp
        * np.cos(psi_obs_rad)
        * (np.cos(psi_obs_rad) + secth * cotph * np.sin(psi_obs_rad))
        - 1.0
    )
    qintr = np.sqrt(1.0 - nom1minq2 / denom)
    pintr = np.sqrt(qintr**2 + nomp2minq2 / denom)
    sigintr_km = sigobs_km * np.sqrt(
        qobs
        / np.sqrt(
            (pintr * np.cos(theta_rad)) ** 2
            + (qintr * np.sin(theta_rad)) ** 2
            * ((pintr * np.cos(phi_rad)) ** 2 + np.sin(phi_rad) ** 2)
        )
    )
    density = (
        surf_km
        * qobs
        * sigobs_km**2
        / (np.sqrt(2.0 * np.pi) * pintr * qintr * sigintr_km**3)
    )
    v0 = 4.0 * np.pi * GRAV_CONST_KM * sigintr_km**2 * pintr * qintr * density
    triaxiality = (1.0 - pintr**2) / (1.0 - qintr**2)
    total_mass = 2.0 * np.pi * np.sum(surf_km * qobs * sigobs_km**2)
    amplitude = np.arccos(qintr)
    modulus = np.sqrt((1.0 - pintr**2) / (1.0 - qintr**2))
    elliptic_f = scipy.special.ellipkinc(amplitude, modulus**2)
    elliptic_e = scipy.special.ellipeinc(amplitude, modulus**2)
    a1 = (elliptic_f - elliptic_e) / (1.0 - pintr**2)
    a2 = (
        (1.0 - qintr**2) * elliptic_e
        - (pintr**2 - qintr**2) * elliptic_f
        - (qintr / pintr) * (1.0 - pintr**2) * np.sqrt(1.0 - qintr**2)
    ) / ((1.0 - pintr**2) * (pintr**2 - qintr**2))
    a3 = (
        (pintr / qintr) * np.sqrt(1.0 - qintr**2)
        - elliptic_e
    ) / (pintr**2 - qintr**2)
    return {
        "conversion_factor": conversion_factor,
        "sigobs_km": sigobs_km,
        "pintr": pintr,
        "qintr": qintr,
        "sigintr_km": sigintr_km,
        "density": density,
        "v0": v0,
        "triaxiality": triaxiality,
        "total_mass": total_mass,
        "elliptic_f": elliptic_f,
        "a1": a1,
        "a2": a2,
        "a3": a3,
    }


def _expected_one_gaussian_mge_evaluation(setup, index, point):
    x, y, z = point
    radius_squared = x * x + y * y + z * z
    sigma = setup["sigintr_km"][index]
    p = setup["pintr"][index]
    q = setup["qintr"][index]
    v0 = setup["v0"][index]

    if radius_squared < (1.0e-4 * sigma) ** 2:
        p2 = p * p
        q2 = q * q
        x2 = x * x
        y2 = y * y
        z2 = z * z
        sigma2 = sigma * sigma
        sigma4 = sigma2 * sigma2
        a1 = setup["a1"][index]
        a2 = setup["a2"][index]
        a3 = setup["a3"][index]
        a12 = -(a1 - a2) / (1.0 - p2)
        a23 = -(a2 - a3) / (p2 - q2)
        a31 = -(a3 - a1) / (q2 - 1.0)
        a11 = (1.0 / 3.0) * (2.0 - a12 - a31)
        a22 = (1.0 / 3.0) * (2.0 / p2 - a23 - a12)
        a33 = (1.0 / 3.0) * (2.0 / q2 - a31 - a23)
        scale = v0 / np.sqrt(1.0 - q2)
        o1 = -0.5 / sigma2 * (a1 * x2 + a2 * y2 + a3 * z2)
        o2 = 0.125 / sigma4 * (
            a11 * x2 * x2 + a22 * y2 * y2 + a33 * z2 * z2
            + 2.0 * a12 * x2 * y2
            + 2.0 * a23 * y2 * z2
            + 2.0 * a31 * z2 * x2
        )
        potential = scale * (setup["elliptic_f"][index] + o1 + o2)
        accel = np.array(
            [
                -scale * x / sigma2 * (
                    a1 - 0.5 / sigma2 * (a11 * x2 + a12 * y2 + a31 * z2)
                ),
                -scale * y / sigma2 * (
                    a2 - 0.5 / sigma2 * (a12 * x2 + a22 * y2 + a23 * z2)
                ),
                -scale * z / sigma2 * (
                    a3 - 0.5 / sigma2 * (a31 * x2 + a23 * y2 + a33 * z2)
                ),
            ],
        )
        return potential, accel

    if radius_squared >= (300.0 * sigma) ** 2:
        radius = np.sqrt(radius_squared)
        scale = np.sqrt(np.pi / 2.0) * sigma * v0
        potential = scale / radius
        accel = np.array(point) * (-scale / radius_squared**1.5)
        return potential, accel

    sigma2 = sigma * sigma
    p_factor = 1.0 - p * p
    q_factor = 1.0 - q * q

    def common(t):
        d = 1.0 - p_factor * t * t
        e = 1.0 - q_factor * t * t
        exponent = np.exp(
            -t * t / (2.0 * sigma2)
            * (x * x + y * y / d + z * z / e)
        )
        return d, e, exponent

    def integrate(function):
        return scipy.integrate.quad(
            function,
            0.0,
            1.0,
            epsabs=0.0,
            epsrel=1.0e-11,
            limit=100,
        )[0]

    potential = v0 * integrate(
        lambda t: common(t)[2] / np.sqrt(common(t)[0] * common(t)[1]),
    )
    accel_x = v0 * integrate(
        lambda t: -x / sigma2 * t * t * common(t)[2] / np.sqrt(common(t)[0] * common(t)[1]),
    )
    accel_y = v0 * integrate(
        lambda t: (
            -y / sigma2 * t * t / common(t)[0]
            * common(t)[2]
            / np.sqrt(common(t)[0] * common(t)[1])
        ),
    )
    accel_z = v0 * integrate(
        lambda t: (
            -z / sigma2 * t * t / common(t)[1]
            * common(t)[2]
            / np.sqrt(common(t)[0] * common(t)[1])
        ),
    )
    return potential, np.array([accel_x, accel_y, accel_z])


def _expected_triaxial_mge_evaluation(setup, points):
    potentials = []
    accelerations = []
    for point in points:
        point_potential = 0.0
        point_acceleration = np.zeros(3)
        for index in range(setup["pintr"].size):
            potential, acceleration = _expected_one_gaussian_mge_evaluation(
                setup,
                index,
                point,
            )
            point_potential += potential
            point_acceleration += acceleration
        potentials.append(point_potential)
        accelerations.append(point_acceleration)
    return np.array(potentials), np.array(accelerations)


def _stable_nfw_log1p(ratio):
    ratio = np.asarray(ratio, dtype=np.float64)
    return np.where(
        ratio >= 1.0,
        np.log1p(ratio),
        2.0 * np.arctanh(ratio / (2.0 + ratio)),
    )


def _zh_gammln(xx):
    coefficients = np.array(
        [
            76.18009172947146,
            -86.50532032941677,
            24.01409824083091,
            -1.231739572450155,
            0.1208650973866179e-2,
            -0.5395239384953e-5,
        ],
        dtype=np.float64,
    )
    x = float(xx)
    y = x
    tmp = x + 5.5
    tmp = (x + 0.5) * np.log(tmp) - tmp
    series = 1.000000000190015
    for coefficient in coefficients:
        y += 1.0
        series += coefficient / y
    return tmp + np.log(2.5066282746310005 * series / x)


def _zh_beta(z, w):
    return np.exp(_zh_gammln(z) + _zh_gammln(w) - _zh_gammln(z + w))


def _zh_betacf(a, b, x):
    qab = a + b
    qap = a + 1.0
    qam = a - 1.0
    c = 1.0
    d = 1.0 - qab * x / qap
    if abs(d) < 1.0e-30:
        d = 1.0e-30
    d = 1.0 / d
    h = d
    for m in range(1, 501):
        m2 = 2 * m
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1.0 + aa * d
        if abs(d) < 1.0e-30:
            d = 1.0e-30
        c = 1.0 + aa / c
        if abs(c) < 1.0e-30:
            c = 1.0e-30
        d = 1.0 / d
        h *= d * c

        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1.0 + aa * d
        if abs(d) < 1.0e-30:
            d = 1.0e-30
        c = 1.0 + aa / c
        if abs(c) < 1.0e-30:
            c = 1.0e-30
        d = 1.0 / d
        delta = d * c
        h *= delta
        if abs(delta - 1.0) < 3.0e-7:
            break
    return h


def _zh_betai(a, b, x):
    if x == 0.0:
        bt = 0.0
    elif x == 1.0:
        return _zh_beta(a, b)
    else:
        bt = x**a * (1.0 - x) ** b
    if x < (a + 1.0) / (a + b + 2.0) or b <= 0.0:
        return bt * _zh_betacf(a, b, x) / a
    return _zh_beta(a, b) - bt * _zh_betacf(b, a, 1.0 - x) / b


def _expected_gnfw_zeta(concentration, gamma):
    if gamma < 1.0:
        return (
            ((1.0 + concentration) / concentration) ** (gamma - 2.0)
            * (2.0 * gamma * concentration - 3.0 * concentration + gamma - 2.0)
            / (gamma**2 - 3.0 * gamma + 2.0)
            / concentration
            + np.exp(_zh_gammln(2.0 - gamma) - _zh_gammln(1.0 - gamma))
            * _zh_betai(1.0 - gamma, 0.0, concentration / (concentration + 1.0))
            / (1.0 - gamma)
        )
    if gamma == 1.0:
        return np.log1p(concentration) - concentration / (1.0 + concentration)
    tmp_gamma = np.pi / np.sin(np.pi * (1.0 - gamma)) / np.exp(_zh_gammln(gamma))
    return (
        ((1.0 + concentration) / concentration) ** (gamma - 2.0)
        * (2.0 * gamma * concentration - 3.0 * concentration + gamma - 2.0)
        / (gamma**2 - 3.0 * gamma + 2.0)
        / concentration
        + (np.exp(_zh_gammln(2.0 - gamma)) / tmp_gamma)
        * _zh_betai(1.0 - gamma, 0.0, concentration / (concentration + 1.0))
        / (1.0 - gamma)
    )


def _expected_dark_halo_setup(profile_type, params, total_stellar_mass):
    params = np.asarray(params, dtype=np.float64)
    if profile_type == 0:
        return {"profile_type": 0}
    if profile_type == 1:
        concentration = params[0]
        dark_fraction = params[1]
        rhoc = (
            (200.0 / 3.0)
            * RHO_CRIT
            * concentration**3
            / (np.log1p(concentration) - concentration / (1.0 + concentration))
        )
        rc = (
            3.0
            / (800.0 * np.pi * RHO_CRIT * concentration**3)
            * dark_fraction
            * total_stellar_mass
        ) ** (1.0 / 3.0)
        return {"profile_type": 1, "rhoc": rhoc, "rc": rc}
    if profile_type == 2:
        return {"profile_type": 2, "rhoc": params[0], "rc": params[1]}
    if profile_type == 3:
        return {
            "profile_type": 3,
            "vc_squared": params[0] ** 2,
            "core_radius_squared": (params[1] * PARSEC_KM * 1.0e3) ** 2,
            "p_squared": params[2] ** 2,
            "q_squared": params[3] ** 2,
        }
    if profile_type == 5:
        concentration = params[0]
        virial_mass = params[1]
        gamma = params[2]
        zeta = _expected_gnfw_zeta(concentration, gamma)
        rhoc = (200.0 / 3.0) * RHO_CRIT * concentration**3 / zeta
        rc = (
            3.0
            * virial_mass
            / (800.0 * np.pi * RHO_CRIT * concentration**3)
        ) ** (1.0 / 3.0)
        return {"profile_type": 5, "rhoc": rhoc, "rc": rc, "gamma": gamma}
    raise ValueError(f"unsupported test profile {profile_type}")


def _expected_dark_halo_evaluation(halo, points):
    points = np.asarray(points, dtype=np.float64)
    potentials = np.zeros(points.shape[0], dtype=np.float64)
    accelerations = np.zeros_like(points)
    radius_squared = np.einsum("ij,ij->i", points, points)
    radius = np.sqrt(radius_squared)

    if halo["profile_type"] == 0:
        return potentials, accelerations
    if halo["profile_type"] == 1:
        ratio = radius / halo["rc"]
        log_term = _stable_nfw_log1p(ratio)
        enclosed_term = log_term - ratio / (1.0 + ratio)
        potential_scale = 4.0 * np.pi * GRAV_CONST_KM * halo["rhoc"] * halo["rc"] ** 3
        potentials = potential_scale / radius * log_term
        acceleration_scale = -potential_scale / radius_squared * enclosed_term / radius
        accelerations = points * acceleration_scale[:, np.newaxis]
        return potentials, accelerations
    if halo["profile_type"] == 2:
        potentials = (
            4.0
            * np.pi
            * GRAV_CONST_KM
            * halo["rhoc"]
            * halo["rc"] ** 2
            / (2.0 * (1.0 + radius / halo["rc"]))
        )
        acceleration_r = (
            -2.0
            * np.pi
            * GRAV_CONST_KM
            * halo["rhoc"]
            * halo["rc"]
            / (1.0 + radius / halo["rc"]) ** 2
        )
        accelerations = points / radius[:, np.newaxis] * acceleration_r[:, np.newaxis]
        return potentials, accelerations
    if halo["profile_type"] == 3:
        denominator = (
            halo["core_radius_squared"]
            + points[:, 0] ** 2
            + points[:, 1] ** 2 / halo["p_squared"]
            + points[:, 2] ** 2 / halo["q_squared"]
        )
        potentials = -0.5 * halo["vc_squared"] * np.log(denominator)
        accelerations[:, 0] = -halo["vc_squared"] * points[:, 0] / denominator
        accelerations[:, 1] = (
            -halo["vc_squared"] * (points[:, 1] / halo["p_squared"]) / denominator
        )
        accelerations[:, 2] = (
            -halo["vc_squared"] * (points[:, 2] / halo["q_squared"]) / denominator
        )
        return potentials, accelerations
    if halo["profile_type"] == 5:
        gamma = halo["gamma"]
        dnorm = radius / halo["rc"]
        xi = dnorm / (1.0 + dnorm)
        ibeta_v2 = np.array(
            [_zh_betai(3.0 - gamma, 0.0, float(value)) for value in xi],
            dtype=np.float64,
        )
        ibeta_v3 = np.array(
            [_zh_betai(1.0, 2.0 - gamma, float(1.0 - value)) for value in xi],
            dtype=np.float64,
        )
        potentials = (
            4.0
            * np.pi
            * GRAV_CONST_KM
            * halo["rhoc"]
            * (ibeta_v2 / dnorm + ibeta_v3)
            * halo["rc"] ** 2
        )
        acceleration_r = 4.0 * np.pi * GRAV_CONST_KM * halo["rhoc"] * halo["rc"] / dnorm
        t1 = (
            xi ** (2.0 - gamma)
            / (1.0 - xi)
            / halo["rc"]
            / dnorm
            / (1.0 + dnorm) ** 2
        )
        t2 = xi ** (1.0 - gamma) / halo["rc"] / (1.0 + dnorm) ** 2
        t3 = ibeta_v2 * halo["rc"] / radius_squared
        acceleration_scale = acceleration_r * (t1 - t2 - t3)
        accelerations = points * acceleration_scale[:, np.newaxis]
        return potentials, accelerations
    raise ValueError(f"unsupported test profile {halo['profile_type']}")


def _expected_potential_stack_evaluation(
    setup,
    points,
    black_hole_mass,
    black_hole_softening_arcsec,
    dark_halo_profile_type,
    dark_halo_parameters,
):
    potentials, accelerations = _expected_triaxial_mge_evaluation(setup, points)
    radius_squared = np.einsum("ij,ij->i", points, points)
    black_hole_softening_km = black_hole_softening_arcsec * setup["conversion_factor"]
    softened_radius_squared = radius_squared + black_hole_softening_km**2
    potentials = potentials + GRAV_CONST_KM * black_hole_mass / np.sqrt(softened_radius_squared)
    acceleration_scale = (
        -GRAV_CONST_KM
        * black_hole_mass
        / (softened_radius_squared * np.sqrt(softened_radius_squared))
    )
    accelerations = accelerations + points * acceleration_scale[:, np.newaxis]

    halo = _expected_dark_halo_setup(
        dark_halo_profile_type,
        dark_halo_parameters,
        setup["total_mass"],
    )
    halo_potential, halo_acceleration = _expected_dark_halo_evaluation(halo, points)
    return potentials + halo_potential, accelerations + halo_acceleration


def _expected_orbit_classification(samples):
    samples = np.asarray(samples, dtype=np.float64)
    positions = samples[:, :3]
    velocities = samples[:, 3:]

    lx = positions[:, 1] * velocities[:, 2] - positions[:, 2] * velocities[:, 1]
    ly = positions[:, 2] * velocities[:, 0] - positions[:, 0] * velocities[:, 2]
    lz = positions[:, 0] * velocities[:, 1] - positions[:, 1] * velocities[:, 0]
    lxc = np.max(lx) * np.min(lx)
    lyc = np.max(ly) * np.min(ly)
    lzc = np.max(lz) * np.min(lz)

    orbit_type = 5
    if lxc > 0.0 and lyc < 0.0 and lzc < 0.0:
        orbit_type = 1
    if lxc < 0.0 and lyc > 0.0 and lzc < 0.0:
        orbit_type = 2
    if lxc < 0.0 and lyc < 0.0 and lzc > 0.0:
        orbit_type = 3
    if lxc < 0.0 and lyc < 0.0 and lzc < 0.0:
        orbit_type = 4

    moments = np.empty(5, dtype=np.float64)
    moments[0] = np.sum(lx) / samples.shape[0]
    moments[1] = np.sum(ly) / samples.shape[0]
    moments[2] = np.sum(lz) / samples.shape[0]
    moments[3] = np.sum(np.sqrt(np.sum(positions**2, axis=1))) / samples.shape[0]
    moments[4] = (
        np.sum(
            np.sum(velocities**2, axis=1)
            + 2.0
            * (
                velocities[:, 0] * velocities[:, 1]
                + velocities[:, 1] * velocities[:, 2]
                + velocities[:, 2] * velocities[:, 0]
            ),
        )
        / samples.shape[0]
    )

    cylindrical_radius = np.sqrt(positions[:, 0] ** 2 + positions[:, 1] ** 2)
    vr = (
        positions[:, 0] * velocities[:, 0] + positions[:, 1] * velocities[:, 1]
    ) / cylindrical_radius
    vt = (
        positions[:, 0] * velocities[:, 1] + positions[:, 1] * velocities[:, 0]
    ) / cylindrical_radius
    vz = velocities[:, 2]
    moments2 = np.array(
        [
            np.sqrt(np.sum((vr - np.sum(vr) / samples.shape[0]) ** 2) / samples.shape[0]),
            np.sqrt(np.sum((vt - np.sum(vt) / samples.shape[0]) ** 2) / samples.shape[0]),
            np.sqrt(np.sum((vz - np.sum(vz) / samples.shape[0]) ** 2) / samples.shape[0]),
        ],
        dtype=np.float64,
    )
    return orbit_type, moments, moments2


POSITION_SIGNS_NONROTATING = np.array(
    [
        [1, 1, 1],
        [-1, 1, 1],
        [-1, -1, 1],
        [1, -1, 1],
        [1, 1, -1],
        [-1, 1, -1],
        [-1, -1, -1],
        [1, -1, -1],
    ],
    dtype=np.float64,
)
POSITION_SIGNS_ROTATING = np.array(
    [
        [1, 1, 1],
        [1, 1, 1],
        [-1, -1, 1],
        [-1, -1, 1],
        [1, 1, -1],
        [1, 1, -1],
        [-1, -1, -1],
        [-1, -1, -1],
    ],
    dtype=np.float64,
)
VELOCITY_SIGNS_NONROTATING = np.array(
    [
        [
            [1, 1, 1],
            [-1, 1, 1],
            [1, 1, -1],
            [-1, 1, -1],
            [-1, -1, 1],
            [1, -1, 1],
            [-1, -1, -1],
            [1, -1, -1],
        ],
        [
            [1, 1, 1],
            [1, -1, -1],
            [1, 1, -1],
            [1, -1, 1],
            [-1, -1, 1],
            [-1, 1, -1],
            [-1, -1, -1],
            [-1, 1, 1],
        ],
        [
            [1, 1, 1],
            [1, -1, -1],
            [-1, -1, 1],
            [-1, 1, -1],
            [1, 1, -1],
            [1, -1, 1],
            [-1, -1, -1],
            [-1, 1, 1],
        ],
        [
            [1, 1, 1],
            [-1, 1, 1],
            [-1, -1, 1],
            [1, -1, 1],
            [1, 1, -1],
            [-1, 1, -1],
            [-1, -1, -1],
            [1, -1, -1],
        ],
        [
            [1, 1, 1],
            [-1, 1, 1],
            [-1, -1, 1],
            [1, -1, 1],
            [1, 1, -1],
            [-1, 1, -1],
            [-1, -1, -1],
            [1, -1, -1],
        ],
    ],
    dtype=np.float64,
)
VELOCITY_SIGNS_ROTATING = np.array(
    [
        [
            [1, 1, 1],
            [1, 1, 1],
            [-1, -1, 1],
            [-1, -1, 1],
            [1, 1, -1],
            [1, 1, -1],
            [-1, -1, -1],
            [-1, -1, -1],
        ],
        [
            [1, 1, 1],
            [1, 1, 1],
            [1, 1, -1],
            [1, 1, -1],
            [-1, -1, 1],
            [-1, -1, 1],
            [-1, -1, -1],
            [-1, -1, -1],
        ],
        [
            [1, 1, 1],
            [1, 1, 1],
            [-1, -1, 1],
            [-1, -1, 1],
            [1, 1, -1],
            [1, 1, -1],
            [-1, -1, -1],
            [-1, -1, -1],
        ],
        [
            [1, 1, 1],
            [1, 1, 1],
            [-1, -1, 1],
            [-1, -1, 1],
            [1, 1, -1],
            [1, 1, -1],
            [-1, -1, -1],
            [-1, -1, -1],
        ],
        [
            [1, 1, 1],
            [1, 1, 1],
            [-1, -1, 1],
            [-1, -1, 1],
            [1, 1, -1],
            [1, 1, -1],
            [-1, -1, -1],
            [-1, -1, -1],
        ],
    ],
    dtype=np.float64,
)


def _expected_orbit_projection(samples, orbit_type, projection_number, omega, theta, phi):
    samples = np.asarray(samples, dtype=np.float64)
    positions = samples[:, :3]
    velocities = samples[:, 3:]
    projection_index = projection_number - 1
    orbit_type_index = orbit_type - 1
    if omega == 0.0:
        psgn = POSITION_SIGNS_NONROTATING[projection_index]
        vsgn = VELOCITY_SIGNS_NONROTATING[orbit_type_index, projection_index]
    else:
        psgn = POSITION_SIGNS_ROTATING[projection_index]
        vsgn = VELOCITY_SIGNS_ROTATING[orbit_type_index, projection_index]

    projected_x = (
        -np.sin(phi) * psgn[0] * positions[:, 0]
        + np.cos(phi) * psgn[1] * positions[:, 1]
    )
    projected_y = (
        -np.cos(theta) * np.cos(phi) * psgn[0] * positions[:, 0]
        - np.cos(theta) * np.sin(phi) * psgn[1] * positions[:, 1]
        + np.sin(theta) * psgn[2] * positions[:, 2]
    )
    los_velocity = (
        np.sin(theta) * np.cos(phi) * vsgn[0] * velocities[:, 0]
        + np.sin(theta) * np.sin(phi) * vsgn[1] * velocities[:, 1]
        + np.cos(theta) * vsgn[2] * velocities[:, 2]
    )
    return projected_x, projected_y, los_velocity


def _expected_qgrid_boundaries(rlogmin, rlogmax, n_radius, n_theta, n_phi, sigobs_km):
    radius = np.empty(n_radius + 1, dtype=np.float64)
    theta = np.empty(n_theta + 1, dtype=np.float64)
    phi = np.empty(n_phi + 1, dtype=np.float64)
    radius[0] = 0.0
    for index in range(1, n_radius):
        radius[index] = 10.0 ** (
            rlogmin
            + (rlogmax - rlogmin + np.log10(0.5)) * (index / n_radius)
        )
    radius[-1] = max(10.0**rlogmax * 100.0, np.max(sigobs_km) * 10.0)
    theta[0] = 0.0
    theta[-1] = 0.5 * np.pi
    for index in range(1, n_theta):
        theta[index] = 0.5 * np.pi * index / n_theta
    phi[0] = 0.0
    phi[-1] = 0.5 * np.pi
    for index in range(1, n_phi):
        phi[index] = 0.5 * np.pi * index / n_phi
    return radius, theta, phi


def _qgrid_index(channel, phi_bin, theta_bin, radius_bin, n_phi, n_theta):
    return channel + 16 * (phi_bin + n_phi * (theta_bin + n_theta * radius_bin))


def _fortran_hunt_boundary_bin(boundaries, value, transform):
    for bin_index, boundary in enumerate(boundaries[1:-1]):
        if value <= transform(boundary):
            return bin_index
    return boundaries.size - 2


def _expected_qgrid_raw(samples, orbit_type, omega, radius, theta, phi):
    samples = np.asarray(samples, dtype=np.float64)
    n_radius = radius.size - 1
    n_theta = theta.size - 1
    n_phi = phi.size - 1
    qgrid = np.zeros(16 * n_phi * n_theta * n_radius, dtype=np.float64)
    if orbit_type == 1:
        store_type_channel = 13
    elif orbit_type == 3:
        store_type_channel = 14
    else:
        store_type_channel = 15
    if omega == 0.0:
        position_signs = POSITION_SIGNS_NONROTATING
        velocity_signs = VELOCITY_SIGNS_NONROTATING[orbit_type - 1]
    else:
        position_signs = POSITION_SIGNS_ROTATING
        velocity_signs = VELOCITY_SIGNS_ROTATING[orbit_type - 1]

    for sample in samples:
        position = sample[:3]
        velocity = sample[3:]
        for projection_index in range(8):
            folded_position = position * position_signs[projection_index]
            x, y, z = folded_position
            if x > 0.0 and y >= 0.0 and z > 0.0:
                folded_velocity = velocity * velocity_signs[projection_index]
                vx, vy, vz = folded_velocity
                radius_squared = x * x + y * y + z * z
                tan_theta_squared = (x * x + y * y) / (z * z)
                tan_phi = y / x
                radius_bin = _fortran_hunt_boundary_bin(radius, radius_squared, lambda b: b * b)
                theta_bin = _fortran_hunt_boundary_bin(
                    theta,
                    tan_theta_squared,
                    lambda b: np.tan(b) ** 2,
                )
                phi_bin = _fortran_hunt_boundary_bin(phi, tan_phi, np.tan)
                values = np.array(
                    [
                        1.0,
                        x,
                        y,
                        z,
                        vx,
                        vy,
                        vz,
                        vx * vx,
                        vy * vy,
                        vz * vz,
                        vx * vy,
                        vy * vz,
                        vz * vx,
                    ],
                    dtype=np.float64,
                )
                for channel, value in enumerate(values):
                    qgrid[_qgrid_index(channel, phi_bin, theta_bin, radius_bin, n_phi, n_theta)] += value
                qgrid[
                    _qgrid_index(store_type_channel, phi_bin, theta_bin, radius_bin, n_phi, n_theta)
                ] += 1.0
    return qgrid


def _expected_qgrid_normalized(raw_qgrid, n_radius, n_theta, n_phi):
    qgrid = np.array(raw_qgrid, copy=True)
    total_count = 0.0
    for radius_bin in range(n_radius):
        for theta_bin in range(n_theta):
            for phi_bin in range(n_phi):
                total_count += qgrid[_qgrid_index(0, phi_bin, theta_bin, radius_bin, n_phi, n_theta)]

    for radius_bin in range(n_radius):
        for theta_bin in range(n_theta):
            for phi_bin in range(n_phi):
                count_index = _qgrid_index(0, phi_bin, theta_bin, radius_bin, n_phi, n_theta)
                count = qgrid[count_index]
                if count != 0.0:
                    for channel in range(1, 13):
                        qgrid[_qgrid_index(channel, phi_bin, theta_bin, radius_bin, n_phi, n_theta)] /= count
                    if total_count != 0.0:
                        qgrid[count_index] /= total_count
                        for channel in range(13, 16):
                            qgrid[
                                _qgrid_index(channel, phi_bin, theta_bin, radius_bin, n_phi, n_theta)
                            ] /= total_count
    return qgrid


def _fortran_gaussian_pair(rng):
    while True:
        values = np.array([rng.ran1(), rng.ran1()], dtype=np.float32)
        values = np.float32(2.0) * values - np.float32(1.0)
        rsq = np.float32(np.sum(values * values, dtype=np.float32))
        if np.float32(0.0) < rsq < np.float32(1.0):
            break
    scale = np.float32(
        np.sqrt(np.float32(-2.0) * np.float32(np.log(rsq)) / rsq),
    )
    return (values * scale).astype(np.float64)


def _fortran_nint_positive(value):
    return int(np.floor(value + 0.5))


def _expected_psf_application(projected, weights, sigmas, sigma_scale, seed):
    projected = np.asarray(projected, dtype=np.float64)
    weights = np.asarray(weights, dtype=np.float64)
    sigmas = np.asarray(sigmas, dtype=np.float64) * sigma_scale
    expected = np.empty_like(projected)
    rng = MyRand(seed)
    sample_count = projected.shape[0]

    if sigmas.size == 1:
        if sigmas[0] > 1.0:
            for index in range(sample_count):
                expected[index] = projected[index] + _fortran_gaussian_pair(rng) * sigmas[0]
        else:
            expected[:, :] = projected[:, :]
        return expected

    weight_sum = np.sum(np.abs(weights))
    weight_index = np.ones(sigmas.size + 1, dtype=np.int64)
    cumulative = 0.0
    for index in range(sigmas.size):
        cumulative += abs(weights[index])
        weight_index[index + 1] = (
            _fortran_nint_positive(cumulative * ((sample_count - 1) / weight_sum)) + 1
        )
    weight_index[0] = 1
    weight_index[-1] = sample_count
    sigma_map = np.zeros(sample_count, dtype=np.float64)
    for index, sigma in enumerate(sigmas):
        for map_index in range(weight_index[index], weight_index[index + 1] + 1):
            sigma_map[map_index - 1] = sigma

    gaussian = np.empty_like(projected)
    for index in range(sample_count):
        gaussian[index] = _fortran_gaussian_pair(rng)
    for index in range(sample_count):
        selector = np.float32(rng.ran1())
        sigma_index = int(
            np.float32(selector * np.float32(sample_count - 1) + np.float32(1.0)),
        )
        expected[index] = projected[index] + gaussian[index] * sigma_map[sigma_index - 1]
    return expected


def _projected_from_boxed_aperture_local(
    local_points,
    begin,
    rotation_degrees,
    psi_radians,
    coordinate_scale,
):
    local_points = np.asarray(local_points, dtype=np.float64)
    scaled_begin = np.asarray(begin, dtype=np.float64) * coordinate_scale
    angle = -np.deg2rad(rotation_degrees) + 0.5 * np.pi - psi_radians
    r1 = np.cos(angle)
    r2 = np.sin(angle)
    shifted_x = local_points[:, 0] + scaled_begin[0]
    shifted_y = local_points[:, 1] + scaled_begin[1]
    return np.ascontiguousarray(
        np.column_stack(
            [
                shifted_x * r1 + shifted_y * r2,
                -shifted_x * r2 + shifted_y * r1,
            ],
        ),
        dtype=np.float64,
    )


def _expected_boxed_aperture_pixels(
    projected,
    begin,
    size,
    rotation_degrees,
    bins_x,
    bins_y,
    psi_radians,
    coordinate_scale,
):
    projected = np.asarray(projected, dtype=np.float64)
    scaled_begin = np.asarray(begin, dtype=np.float64) * coordinate_scale
    scaled_size = np.asarray(size, dtype=np.float64) * coordinate_scale
    angle = -np.deg2rad(rotation_degrees) + 0.5 * np.pi - psi_radians
    r1 = np.cos(angle)
    r2 = np.sin(angle)
    idx = bins_x / scaled_size[0]
    idy = bins_y / scaled_size[1]
    pixels = np.zeros(projected.shape[0], dtype=np.int32)

    for index, (t, q) in enumerate(projected):
        x = t * r1 - q * r2 - scaled_begin[0]
        if 0.0 < x < scaled_size[0]:
            y = t * r2 + q * r1 - scaled_begin[1]
            if 0.0 < y < scaled_size[1]:
                pixels[index] = int(x * idx) + int(y * idy) * bins_x + 1
    return pixels


def _expected_losvd_velocity_bins(los_velocity, histogram_width, histogram_center, bin_count):
    begin = histogram_center - 0.5 * histogram_width
    end = histogram_center + 0.5 * histogram_width
    bin_width = histogram_width / bin_count
    velocity_bins = np.ones(los_velocity.size, dtype=np.int32)
    for index, velocity in enumerate(los_velocity):
        if velocity > begin:
            if velocity < end:
                velocity_bins[index] = int((velocity - begin) / bin_width) + 1
            else:
                velocity_bins[index] = bin_count
    return velocity_bins


def _expected_losvd_histogram(aperture_pixels, velocity_bins, aperture_pixel_count, bin_count):
    histogram = np.zeros((aperture_pixel_count, bin_count), dtype=np.float64)
    for pixel, velocity_bin in zip(aperture_pixels, velocity_bins):
        if pixel != 0:
            histogram[pixel - 1, velocity_bin - 1] += 1.0
    return histogram


def _expected_collapsed_losvd_histogram(source_histogram, bin_order, target_pixel_count):
    collapsed = np.zeros((target_pixel_count, source_histogram.shape[1]), dtype=np.float64)
    for source_index, target in enumerate(bin_order):
        if target != 0:
            collapsed[target - 1] += source_histogram[source_index]
    return collapsed


def _expected_sparse_losvd_ranges(histogram):
    velocity_bin_count = histogram.shape[1]
    center_bin = int(velocity_bin_count / 2.0 + 1.0)
    begin_offsets = np.empty(histogram.shape[0], dtype=np.int32)
    end_offsets = np.empty(histogram.shape[0], dtype=np.int32)
    for row_index, row in enumerate(histogram):
        nonzero = np.flatnonzero(row > 0.0) + 1
        if nonzero.size == 0:
            begin = 2 * velocity_bin_count
            end = -2 * velocity_bin_count
        else:
            begin = int(nonzero.min())
            end = int(nonzero.max())
        begin_offsets[row_index] = begin - center_bin
        end_offsets[row_index] = end - center_bin
    return begin_offsets, end_offsets


def _expected_interpolation_metadata(setup, rlogmin, rlogmax, n_radius, n_theta, n_phi):
    rmin2 = (np.min(setup["sigobs_km"]) / 10.0) ** 2
    rmax2 = (np.max(setup["sigintr_km"]) * 6.0) ** 2
    rmin2 = min((10.0**rlogmin * 0.01) ** 2, rmin2)
    rmax2 = max((10.0**rlogmax * 1.05) ** 2, rmax2 * 2.0)
    rlog_min = np.log10(np.sqrt(rmin2))
    rlog_max = np.log10(np.sqrt(rmax2))
    return {
        "theta_step": (0.5 * np.pi) / (n_theta - 1),
        "phi_step": (0.5 * np.pi) / (n_phi - 1),
        "rlog_step": (rlog_max - rlog_min) / (n_radius - 1),
        "rlog_min": rlog_min,
        "rmin2": rmin2,
        "rmax2": rmax2,
    }


def _expected_interpolated_potential_evaluation(
    setup,
    points,
    black_hole_mass,
    black_hole_softening_arcsec,
    dark_halo_profile_type,
    dark_halo_parameters,
    rlogmin,
    rlogmax,
    n_radius,
    n_theta,
    n_phi,
):
    metadata = _expected_interpolation_metadata(
        setup,
        rlogmin,
        rlogmax,
        n_radius,
        n_theta,
        n_phi,
    )
    log_tiny = np.log(np.finfo(np.float64).tiny)
    tiny = np.finfo(np.float64).tiny
    grid = np.full((3, n_phi, n_theta, n_radius), log_tiny, dtype=np.float64)
    grid_points = []
    grid_indices = []
    for radius_index in range(n_radius):
        radius = 10.0 ** (
            metadata["rlog_min"] + radius_index * metadata["rlog_step"]
        )
        for theta_index in range(n_theta):
            theta = theta_index * metadata["theta_step"]
            if theta_index == 0:
                theta = 0.5 * metadata["theta_step"]
            if theta_index == n_theta - 1:
                theta = (n_theta - 1.1) * metadata["theta_step"]
            sin_theta = np.sin(theta)
            z = radius * np.cos(theta)
            for phi_index in range(n_phi):
                phi = phi_index * metadata["phi_step"]
                if phi_index == 0:
                    phi = 0.5 * metadata["phi_step"]
                if phi_index == n_phi - 1:
                    phi = (n_phi - 1.1) * metadata["phi_step"]
                x = radius * sin_theta * np.cos(phi)
                y = radius * sin_theta * np.sin(phi)
                grid_points.append([x, y, z])
                grid_indices.append((phi_index, theta_index, radius_index, x, y, z))

    _, grid_acceleration = _expected_potential_stack_evaluation(
        setup,
        np.asarray(grid_points, dtype=np.float64),
        black_hole_mass,
        black_hole_softening_arcsec,
        dark_halo_profile_type,
        dark_halo_parameters,
    )
    for acceleration, (phi_index, theta_index, radius_index, x, y, z) in zip(
        grid_acceleration,
        grid_indices,
    ):
        if -acceleration[0] > tiny * x:
            grid[0, phi_index, theta_index, radius_index] = np.log(-acceleration[0] / x)
        if -acceleration[1] > tiny * y:
            grid[1, phi_index, theta_index, radius_index] = np.log(-acceleration[1] / y)
        if -acceleration[2] > tiny * z:
            grid[2, phi_index, theta_index, radius_index] = np.log(-acceleration[2] / z)

    direct_potential, direct_acceleration = _expected_potential_stack_evaluation(
        setup,
        points,
        black_hole_mass,
        black_hole_softening_arcsec,
        dark_halo_profile_type,
        dark_halo_parameters,
    )
    interpolated_acceleration = direct_acceleration.copy()
    inner_fallback_count = 0
    outer_fallback_count = 0
    for index, point in enumerate(points):
        x, y, z = point
        radius_squared = np.dot(point, point)
        if radius_squared <= metadata["rmin2"] or radius_squared >= metadata["rmax2"]:
            if radius_squared < metadata["rmin2"]:
                inner_fallback_count += 1
            if radius_squared > metadata["rmax2"]:
                outer_fallback_count += 1
            continue

        theta = np.arctan2(np.sqrt(x * x + y * y), abs(z))
        phi = np.arctan2(abs(y), abs(x))
        radius_log = 0.5 * np.log10(radius_squared)
        theta_scaled = theta / metadata["theta_step"]
        phi_scaled = phi / metadata["phi_step"]
        radius_scaled = (radius_log - metadata["rlog_min"]) / metadata["rlog_step"]
        theta_index = int(np.floor(theta_scaled))
        phi_index = int(np.floor(phi_scaled))
        radius_index = int(np.floor(radius_scaled))
        if (
            theta_index < 0
            or phi_index < 0
            or radius_index < 0
            or theta_index + 1 >= n_theta
            or phi_index + 1 >= n_phi
            or radius_index + 1 >= n_radius
        ):
            continue

        tf = theta_scaled - np.floor(theta_scaled)
        pf = phi_scaled - np.floor(phi_scaled)
        rf = radius_scaled - np.floor(radius_scaled)
        acc_log = (
            (1.0 - pf) * (1.0 - tf) * (1.0 - rf)
            * grid[:, phi_index, theta_index, radius_index]
            + (1.0 - pf) * (1.0 - tf) * rf
            * grid[:, phi_index, theta_index, radius_index + 1]
            + (1.0 - pf) * tf * rf
            * grid[:, phi_index, theta_index + 1, radius_index + 1]
            + (1.0 - pf) * tf * (1.0 - rf)
            * grid[:, phi_index, theta_index + 1, radius_index]
            + pf * (1.0 - tf) * (1.0 - rf)
            * grid[:, phi_index + 1, theta_index, radius_index]
            + pf * (1.0 - tf) * rf
            * grid[:, phi_index + 1, theta_index, radius_index + 1]
            + pf * tf * rf
            * grid[:, phi_index + 1, theta_index + 1, radius_index + 1]
            + pf * tf * (1.0 - rf)
            * grid[:, phi_index + 1, theta_index + 1, radius_index]
        )
        interpolated_acceleration[index] = -point * np.exp(acc_log)

    return (
        direct_potential,
        interpolated_acceleration,
        metadata,
        inner_fallback_count,
        outer_fallback_count,
    )


def _expected_orbit_rhs_evaluation(interpolated_acceleration, states, omega):
    derivatives = np.empty_like(states)
    if omega == 0.0:
        derivatives[:, 0:3] = states[:, 3:6]
        derivatives[:, 3:6] = interpolated_acceleration
        return derivatives

    derivatives[:, 0] = states[:, 3] + omega * states[:, 1]
    derivatives[:, 1] = states[:, 4] - omega * states[:, 0]
    derivatives[:, 2] = states[:, 5]
    derivatives[:, 3] = interpolated_acceleration[:, 0] + omega * states[:, 4]
    derivatives[:, 4] = interpolated_acceleration[:, 1] - omega * states[:, 3]
    derivatives[:, 5] = interpolated_acceleration[:, 2]
    return derivatives


@pytest.mark.orblib_cpp
def test_orblib_cpp_triaxial_mge_setup_matches_fortran_formulas():
    surf_pc = np.array(
        [26819.14, 2456.39, 456.8, 645.49, 14.73, 122.85, 1.0],
        dtype=np.float64,
    )
    sigobs_arcsec = np.array(
        [0.49416, 2.04299, 2.44313, 6.5305, 17.41488, 21.84711, 21.84711],
        dtype=np.float64,
    )
    qobs = np.array(
        [0.89541, 0.79093, 0.9999, 0.55097, 0.9999, 0.55097, 0.55097],
        dtype=np.float64,
    )
    psi_obs = np.zeros_like(qobs)
    theta = 82.444308859
    psi = 90.021481540
    phi = 84.245110877
    distance = 39.9
    upsilon = 1.0

    expected = _expected_triaxial_mge_setup(
        surf_pc,
        sigobs_arcsec,
        qobs,
        psi_obs,
        distance,
        theta,
        phi,
        psi,
        upsilon,
    )
    count = surf_pc.size
    pintr = np.empty(count, dtype=np.float64)
    qintr = np.empty(count, dtype=np.float64)
    sigintr_km = np.empty(count, dtype=np.float64)
    density = np.empty(count, dtype=np.float64)
    v0 = np.empty(count, dtype=np.float64)
    triaxiality = np.empty(count, dtype=np.float64)
    total_mass = ctypes.c_double(np.nan)
    status = ctypes.c_int(-999)
    library = ctypes.CDLL(str(ORBLIB_CPP_SHARED_LIBRARY))
    function = library.orblib_cpp_api_triaxial_mge_setup
    double_p = ctypes.POINTER(ctypes.c_double)
    function.argtypes = [
        ctypes.c_int,
        double_p,
        double_p,
        double_p,
        double_p,
        ctypes.c_double,
        ctypes.c_double,
        ctypes.c_double,
        ctypes.c_double,
        ctypes.c_double,
        double_p,
        double_p,
        double_p,
        double_p,
        double_p,
        double_p,
        ctypes.POINTER(ctypes.c_double),
        ctypes.POINTER(ctypes.c_int),
    ]
    function.restype = None

    function(
        ctypes.c_int(count),
        surf_pc.ctypes.data_as(double_p),
        sigobs_arcsec.ctypes.data_as(double_p),
        qobs.ctypes.data_as(double_p),
        psi_obs.ctypes.data_as(double_p),
        ctypes.c_double(distance),
        ctypes.c_double(theta),
        ctypes.c_double(phi),
        ctypes.c_double(psi),
        ctypes.c_double(upsilon),
        pintr.ctypes.data_as(double_p),
        qintr.ctypes.data_as(double_p),
        sigintr_km.ctypes.data_as(double_p),
        density.ctypes.data_as(double_p),
        v0.ctypes.data_as(double_p),
        triaxiality.ctypes.data_as(double_p),
        ctypes.byref(total_mass),
        ctypes.byref(status),
    )

    assert status.value == 0
    np.testing.assert_allclose(pintr, expected["pintr"], rtol=0.0, atol=2e-12)
    np.testing.assert_allclose(qintr, expected["qintr"], rtol=0.0, atol=2e-12)
    np.testing.assert_allclose(
        sigintr_km,
        expected["sigintr_km"],
        rtol=2e-14,
        atol=0.0,
    )
    np.testing.assert_allclose(density, expected["density"], rtol=2e-14, atol=0.0)
    np.testing.assert_allclose(v0, expected["v0"], rtol=2e-14, atol=0.0)
    np.testing.assert_allclose(
        triaxiality,
        expected["triaxiality"],
        rtol=0.0,
        atol=2e-12,
    )
    np.testing.assert_allclose(total_mass.value, expected["total_mass"], rtol=2e-14, atol=0.0)


@pytest.mark.orblib_cpp
def test_orblib_cpp_triaxial_mge_evaluator_matches_formula_branches():
    surf_pc = np.array(
        [26819.14, 2456.39, 456.8, 645.49, 14.73, 122.85, 1.0],
        dtype=np.float64,
    )
    sigobs_arcsec = np.array(
        [0.49416, 2.04299, 2.44313, 6.5305, 17.41488, 21.84711, 21.84711],
        dtype=np.float64,
    )
    qobs = np.array(
        [0.89541, 0.79093, 0.9999, 0.55097, 0.9999, 0.55097, 0.55097],
        dtype=np.float64,
    )
    psi_obs = np.zeros_like(qobs)
    theta = 82.444308859
    psi = 90.021481540
    phi = 84.245110877
    distance = 39.9
    upsilon = 1.0
    points = np.ascontiguousarray(
        [
            [1.0e8, -2.0e8, 3.0e8],
            [3.0e15, 2.0e15, -1.0e15],
            [5.0e20, -2.0e20, 1.0e20],
        ],
        dtype=np.float64,
    )
    expected_setup = _expected_triaxial_mge_setup(
        surf_pc,
        sigobs_arcsec,
        qobs,
        psi_obs,
        distance,
        theta,
        phi,
        psi,
        upsilon,
    )
    expected_potential, expected_acceleration = _expected_triaxial_mge_evaluation(
        expected_setup,
        points,
    )
    point_x = np.ascontiguousarray(points[:, 0], dtype=np.float64)
    point_y = np.ascontiguousarray(points[:, 1], dtype=np.float64)
    point_z = np.ascontiguousarray(points[:, 2], dtype=np.float64)

    potential = np.empty(points.shape[0], dtype=np.float64)
    accel_x = np.empty(points.shape[0], dtype=np.float64)
    accel_y = np.empty(points.shape[0], dtype=np.float64)
    accel_z = np.empty(points.shape[0], dtype=np.float64)
    status = ctypes.c_int(-999)
    library = ctypes.CDLL(str(ORBLIB_CPP_SHARED_LIBRARY))
    function = library.orblib_cpp_api_triaxial_mge_evaluate
    double_p = ctypes.POINTER(ctypes.c_double)
    function.argtypes = [
        ctypes.c_int,
        double_p,
        double_p,
        double_p,
        double_p,
        ctypes.c_double,
        ctypes.c_double,
        ctypes.c_double,
        ctypes.c_double,
        ctypes.c_double,
        ctypes.c_int,
        double_p,
        double_p,
        double_p,
        double_p,
        double_p,
        double_p,
        double_p,
        ctypes.POINTER(ctypes.c_int),
    ]
    function.restype = None

    function(
        ctypes.c_int(surf_pc.size),
        surf_pc.ctypes.data_as(double_p),
        sigobs_arcsec.ctypes.data_as(double_p),
        qobs.ctypes.data_as(double_p),
        psi_obs.ctypes.data_as(double_p),
        ctypes.c_double(distance),
        ctypes.c_double(theta),
        ctypes.c_double(phi),
        ctypes.c_double(psi),
        ctypes.c_double(upsilon),
        ctypes.c_int(points.shape[0]),
        point_x.ctypes.data_as(double_p),
        point_y.ctypes.data_as(double_p),
        point_z.ctypes.data_as(double_p),
        potential.ctypes.data_as(double_p),
        accel_x.ctypes.data_as(double_p),
        accel_y.ctypes.data_as(double_p),
        accel_z.ctypes.data_as(double_p),
        ctypes.byref(status),
    )

    assert status.value == 0
    actual_acceleration = np.column_stack([accel_x, accel_y, accel_z])
    np.testing.assert_allclose(
        potential,
        expected_potential,
        rtol=2e-10,
        atol=0.0,
    )
    np.testing.assert_allclose(
        actual_acceleration,
        expected_acceleration,
        rtol=2e-10,
        atol=0.0,
    )


@pytest.mark.orblib_cpp
@pytest.mark.parametrize(
    ("dark_halo_profile_type", "dark_halo_parameters"),
    [
        (0, []),
        (1, [3.0, 0.8]),
        (2, [2.0e-58, 2.0e18]),
        (3, [160.0, 2.0, 0.9, 0.7]),
        (5, [8.0, 5.0e12, 0.7]),
        (5, [8.0, 5.0e12, 1.0]),
        (5, [8.0, 5.0e12, 1.4]),
    ],
)
def test_orblib_cpp_potential_stack_matches_black_hole_and_supported_dark_halos(
    dark_halo_profile_type,
    dark_halo_parameters,
):
    surf_pc = np.array(
        [26819.14, 2456.39, 456.8, 645.49, 14.73, 122.85, 1.0],
        dtype=np.float64,
    )
    sigobs_arcsec = np.array(
        [0.49416, 2.04299, 2.44313, 6.5305, 17.41488, 21.84711, 21.84711],
        dtype=np.float64,
    )
    qobs = np.array(
        [0.89541, 0.79093, 0.9999, 0.55097, 0.9999, 0.55097, 0.55097],
        dtype=np.float64,
    )
    psi_obs = np.zeros_like(qobs)
    theta = 82.444308859
    psi = 90.021481540
    phi = 84.245110877
    distance = 39.9
    upsilon = 1.0
    black_hole_mass = 2.0e9
    black_hole_softening_arcsec = 0.02
    points = np.ascontiguousarray(
        [
            [1.0e10, -2.0e10, 3.0e10],
            [3.0e15, 2.0e15, -1.0e15],
            [5.0e20, -2.0e20, 1.0e20],
        ],
        dtype=np.float64,
    )
    expected_setup = _expected_triaxial_mge_setup(
        surf_pc,
        sigobs_arcsec,
        qobs,
        psi_obs,
        distance,
        theta,
        phi,
        psi,
        upsilon,
    )
    dark_halo_parameters = np.ascontiguousarray(dark_halo_parameters, dtype=np.float64)
    expected_potential, expected_acceleration = _expected_potential_stack_evaluation(
        expected_setup,
        points,
        black_hole_mass,
        black_hole_softening_arcsec,
        dark_halo_profile_type,
        dark_halo_parameters,
    )
    point_x = np.ascontiguousarray(points[:, 0], dtype=np.float64)
    point_y = np.ascontiguousarray(points[:, 1], dtype=np.float64)
    point_z = np.ascontiguousarray(points[:, 2], dtype=np.float64)

    potential = np.empty(points.shape[0], dtype=np.float64)
    accel_x = np.empty(points.shape[0], dtype=np.float64)
    accel_y = np.empty(points.shape[0], dtype=np.float64)
    accel_z = np.empty(points.shape[0], dtype=np.float64)
    status = ctypes.c_int(-999)
    library = ctypes.CDLL(str(ORBLIB_CPP_SHARED_LIBRARY))
    function = library.orblib_cpp_api_potential_stack_evaluate
    double_p = ctypes.POINTER(ctypes.c_double)
    function.argtypes = [
        ctypes.c_int,
        double_p,
        double_p,
        double_p,
        double_p,
        ctypes.c_double,
        ctypes.c_double,
        ctypes.c_double,
        ctypes.c_double,
        ctypes.c_double,
        ctypes.c_double,
        ctypes.c_double,
        ctypes.c_int,
        ctypes.c_int,
        double_p,
        ctypes.c_int,
        double_p,
        double_p,
        double_p,
        double_p,
        double_p,
        double_p,
        double_p,
        ctypes.POINTER(ctypes.c_int),
    ]
    function.restype = None
    dark_halo_pointer = (
        None
        if dark_halo_parameters.size == 0
        else dark_halo_parameters.ctypes.data_as(double_p)
    )

    function(
        ctypes.c_int(surf_pc.size),
        surf_pc.ctypes.data_as(double_p),
        sigobs_arcsec.ctypes.data_as(double_p),
        qobs.ctypes.data_as(double_p),
        psi_obs.ctypes.data_as(double_p),
        ctypes.c_double(distance),
        ctypes.c_double(theta),
        ctypes.c_double(phi),
        ctypes.c_double(psi),
        ctypes.c_double(upsilon),
        ctypes.c_double(black_hole_mass),
        ctypes.c_double(black_hole_softening_arcsec),
        ctypes.c_int(dark_halo_profile_type),
        ctypes.c_int(dark_halo_parameters.size),
        dark_halo_pointer,
        ctypes.c_int(points.shape[0]),
        point_x.ctypes.data_as(double_p),
        point_y.ctypes.data_as(double_p),
        point_z.ctypes.data_as(double_p),
        potential.ctypes.data_as(double_p),
        accel_x.ctypes.data_as(double_p),
        accel_y.ctypes.data_as(double_p),
        accel_z.ctypes.data_as(double_p),
        ctypes.byref(status),
    )

    assert status.value == 0
    actual_acceleration = np.column_stack([accel_x, accel_y, accel_z])
    np.testing.assert_allclose(
        potential,
        expected_potential,
        rtol=2e-10,
        atol=0.0,
    )
    np.testing.assert_allclose(
        actual_acceleration,
        expected_acceleration,
        rtol=2e-10,
        atol=0.0,
    )


@pytest.mark.orblib_cpp
def test_orblib_cpp_interpolated_potential_matches_fortran_grid_formula():
    surf_pc = np.array([0.0], dtype=np.float64)
    sigobs_arcsec = np.array([0.49416], dtype=np.float64)
    qobs = np.array([0.89541], dtype=np.float64)
    psi_obs = np.zeros_like(qobs)
    theta = 82.444308859
    psi = 90.021481540
    phi = 84.245110877
    distance = 39.9
    upsilon = 1.0
    black_hole_mass = 2.0e9
    black_hole_softening_arcsec = 0.02
    dark_halo_profile_type = 0
    dark_halo_parameters = np.ascontiguousarray([], dtype=np.float64)
    n_radius = 4
    n_theta = 4
    n_phi = 4
    rlogmin = 18.0
    rlogmax = 19.0

    def spherical_point(radius, theta_value, phi_value):
        return [
            radius * np.sin(theta_value) * np.cos(phi_value),
            -radius * np.sin(theta_value) * np.sin(phi_value),
            radius * np.cos(theta_value),
        ]

    points = np.ascontiguousarray(
        [
            spherical_point(1.0e17, 0.7, 0.35),
            spherical_point(1.0e13, 0.8, 0.4),
            spherical_point(3.0e19, 0.9, 0.5),
        ],
        dtype=np.float64,
    )
    expected_setup = _expected_triaxial_mge_setup(
        surf_pc,
        sigobs_arcsec,
        qobs,
        psi_obs,
        distance,
        theta,
        phi,
        psi,
        upsilon,
    )
    (
        expected_potential,
        expected_acceleration,
        expected_metadata,
        expected_inner_fallback_count,
        expected_outer_fallback_count,
    ) = _expected_interpolated_potential_evaluation(
        expected_setup,
        points,
        black_hole_mass,
        black_hole_softening_arcsec,
        dark_halo_profile_type,
        dark_halo_parameters,
        rlogmin,
        rlogmax,
        n_radius,
        n_theta,
        n_phi,
    )
    point_x = np.ascontiguousarray(points[:, 0], dtype=np.float64)
    point_y = np.ascontiguousarray(points[:, 1], dtype=np.float64)
    point_z = np.ascontiguousarray(points[:, 2], dtype=np.float64)
    potential = np.empty(points.shape[0], dtype=np.float64)
    accel_x = np.empty(points.shape[0], dtype=np.float64)
    accel_y = np.empty(points.shape[0], dtype=np.float64)
    accel_z = np.empty(points.shape[0], dtype=np.float64)
    theta_step = ctypes.c_double(np.nan)
    phi_step = ctypes.c_double(np.nan)
    rlog_step = ctypes.c_double(np.nan)
    rlog_min = ctypes.c_double(np.nan)
    rmin2 = ctypes.c_double(np.nan)
    rmax2 = ctypes.c_double(np.nan)
    inner_fallback_count = ctypes.c_int(-1)
    outer_fallback_count = ctypes.c_int(-1)
    status = ctypes.c_int(-999)
    library = ctypes.CDLL(str(ORBLIB_CPP_SHARED_LIBRARY))
    function = library.orblib_cpp_api_interpolated_potential_evaluate
    double_p = ctypes.POINTER(ctypes.c_double)
    function.argtypes = [
        ctypes.c_int,
        double_p,
        double_p,
        double_p,
        double_p,
        ctypes.c_double,
        ctypes.c_double,
        ctypes.c_double,
        ctypes.c_double,
        ctypes.c_double,
        ctypes.c_double,
        ctypes.c_double,
        ctypes.c_int,
        ctypes.c_int,
        double_p,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_double,
        ctypes.c_double,
        ctypes.c_int,
        double_p,
        double_p,
        double_p,
        double_p,
        double_p,
        double_p,
        double_p,
        ctypes.POINTER(ctypes.c_double),
        ctypes.POINTER(ctypes.c_double),
        ctypes.POINTER(ctypes.c_double),
        ctypes.POINTER(ctypes.c_double),
        ctypes.POINTER(ctypes.c_double),
        ctypes.POINTER(ctypes.c_double),
        ctypes.POINTER(ctypes.c_int),
        ctypes.POINTER(ctypes.c_int),
        ctypes.POINTER(ctypes.c_int),
    ]
    function.restype = None

    function(
        ctypes.c_int(surf_pc.size),
        surf_pc.ctypes.data_as(double_p),
        sigobs_arcsec.ctypes.data_as(double_p),
        qobs.ctypes.data_as(double_p),
        psi_obs.ctypes.data_as(double_p),
        ctypes.c_double(distance),
        ctypes.c_double(theta),
        ctypes.c_double(phi),
        ctypes.c_double(psi),
        ctypes.c_double(upsilon),
        ctypes.c_double(black_hole_mass),
        ctypes.c_double(black_hole_softening_arcsec),
        ctypes.c_int(dark_halo_profile_type),
        ctypes.c_int(dark_halo_parameters.size),
        None,
        ctypes.c_int(n_radius),
        ctypes.c_int(n_theta),
        ctypes.c_int(n_phi),
        ctypes.c_double(rlogmin),
        ctypes.c_double(rlogmax),
        ctypes.c_int(points.shape[0]),
        point_x.ctypes.data_as(double_p),
        point_y.ctypes.data_as(double_p),
        point_z.ctypes.data_as(double_p),
        potential.ctypes.data_as(double_p),
        accel_x.ctypes.data_as(double_p),
        accel_y.ctypes.data_as(double_p),
        accel_z.ctypes.data_as(double_p),
        ctypes.byref(theta_step),
        ctypes.byref(phi_step),
        ctypes.byref(rlog_step),
        ctypes.byref(rlog_min),
        ctypes.byref(rmin2),
        ctypes.byref(rmax2),
        ctypes.byref(inner_fallback_count),
        ctypes.byref(outer_fallback_count),
        ctypes.byref(status),
    )

    assert status.value == 0
    assert inner_fallback_count.value == expected_inner_fallback_count
    assert outer_fallback_count.value == expected_outer_fallback_count
    np.testing.assert_allclose(theta_step.value, expected_metadata["theta_step"], rtol=0.0, atol=1e-15)
    np.testing.assert_allclose(phi_step.value, expected_metadata["phi_step"], rtol=0.0, atol=1e-15)
    np.testing.assert_allclose(rlog_step.value, expected_metadata["rlog_step"], rtol=0.0, atol=1e-15)
    np.testing.assert_allclose(rlog_min.value, expected_metadata["rlog_min"], rtol=0.0, atol=1e-15)
    np.testing.assert_allclose(rmin2.value, expected_metadata["rmin2"], rtol=2e-15, atol=0.0)
    np.testing.assert_allclose(rmax2.value, expected_metadata["rmax2"], rtol=2e-15, atol=0.0)
    np.testing.assert_allclose(potential, expected_potential, rtol=2e-12, atol=0.0)
    np.testing.assert_allclose(
        np.column_stack([accel_x, accel_y, accel_z]),
        expected_acceleration,
        rtol=2e-12,
        atol=0.0,
    )


@pytest.mark.orblib_cpp
@pytest.mark.parametrize("omega", [0.0, 1.5e-16])
def test_orblib_cpp_orbit_rhs_matches_fortran_derivs_formula(omega):
    surf_pc = np.array([0.0], dtype=np.float64)
    sigobs_arcsec = np.array([0.49416], dtype=np.float64)
    qobs = np.array([0.89541], dtype=np.float64)
    psi_obs = np.zeros_like(qobs)
    theta = 82.444308859
    psi = 90.021481540
    phi = 84.245110877
    distance = 39.9
    upsilon = 1.0
    black_hole_mass = 2.0e9
    black_hole_softening_arcsec = 0.02
    dark_halo_profile_type = 0
    dark_halo_parameters = np.ascontiguousarray([], dtype=np.float64)
    n_radius = 4
    n_theta = 4
    n_phi = 4
    rlogmin = 18.0
    rlogmax = 19.0

    def spherical_point(radius, theta_value, phi_value):
        return [
            radius * np.sin(theta_value) * np.cos(phi_value),
            -radius * np.sin(theta_value) * np.sin(phi_value),
            radius * np.cos(theta_value),
        ]

    positions = np.ascontiguousarray(
        [
            spherical_point(1.0e17, 0.7, 0.35),
            spherical_point(1.0e13, 0.8, 0.4),
            spherical_point(3.0e19, 0.9, 0.5),
        ],
        dtype=np.float64,
    )
    velocities = np.ascontiguousarray(
        [
            [12.0, -21.0, 5.0],
            [-7.5, 4.0, 2.5],
            [30.0, -11.0, -3.0],
        ],
        dtype=np.float64,
    )
    states = np.ascontiguousarray(np.column_stack([positions, velocities]), dtype=np.float64)
    expected_setup = _expected_triaxial_mge_setup(
        surf_pc,
        sigobs_arcsec,
        qobs,
        psi_obs,
        distance,
        theta,
        phi,
        psi,
        upsilon,
    )
    (
        _,
        expected_acceleration,
        _,
        expected_inner_fallback_count,
        expected_outer_fallback_count,
    ) = _expected_interpolated_potential_evaluation(
        expected_setup,
        positions,
        black_hole_mass,
        black_hole_softening_arcsec,
        dark_halo_profile_type,
        dark_halo_parameters,
        rlogmin,
        rlogmax,
        n_radius,
        n_theta,
        n_phi,
    )
    expected_derivative = _expected_orbit_rhs_evaluation(
        expected_acceleration,
        states,
        omega,
    )

    derivatives = np.empty_like(states)
    inner_fallback_count = ctypes.c_int(-1)
    outer_fallback_count = ctypes.c_int(-1)
    status = ctypes.c_int(-999)
    library = ctypes.CDLL(str(ORBLIB_CPP_SHARED_LIBRARY))
    function = library.orblib_cpp_api_orbit_rhs_evaluate
    double_p = ctypes.POINTER(ctypes.c_double)
    function.argtypes = [
        ctypes.c_int,
        double_p,
        double_p,
        double_p,
        double_p,
        ctypes.c_double,
        ctypes.c_double,
        ctypes.c_double,
        ctypes.c_double,
        ctypes.c_double,
        ctypes.c_double,
        ctypes.c_double,
        ctypes.c_int,
        ctypes.c_int,
        double_p,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_double,
        ctypes.c_double,
        ctypes.c_double,
        ctypes.c_int,
        double_p,
        double_p,
        double_p,
        double_p,
        double_p,
        double_p,
        double_p,
        double_p,
        double_p,
        double_p,
        double_p,
        double_p,
        ctypes.POINTER(ctypes.c_int),
        ctypes.POINTER(ctypes.c_int),
        ctypes.POINTER(ctypes.c_int),
    ]
    function.restype = None
    state_x = np.ascontiguousarray(states[:, 0], dtype=np.float64)
    state_y = np.ascontiguousarray(states[:, 1], dtype=np.float64)
    state_z = np.ascontiguousarray(states[:, 2], dtype=np.float64)
    state_vx = np.ascontiguousarray(states[:, 3], dtype=np.float64)
    state_vy = np.ascontiguousarray(states[:, 4], dtype=np.float64)
    state_vz = np.ascontiguousarray(states[:, 5], dtype=np.float64)
    derivative_x = np.ascontiguousarray(derivatives[:, 0])
    derivative_y = np.ascontiguousarray(derivatives[:, 1])
    derivative_z = np.ascontiguousarray(derivatives[:, 2])
    derivative_vx = np.ascontiguousarray(derivatives[:, 3])
    derivative_vy = np.ascontiguousarray(derivatives[:, 4])
    derivative_vz = np.ascontiguousarray(derivatives[:, 5])

    function(
        ctypes.c_int(surf_pc.size),
        surf_pc.ctypes.data_as(double_p),
        sigobs_arcsec.ctypes.data_as(double_p),
        qobs.ctypes.data_as(double_p),
        psi_obs.ctypes.data_as(double_p),
        ctypes.c_double(distance),
        ctypes.c_double(theta),
        ctypes.c_double(phi),
        ctypes.c_double(psi),
        ctypes.c_double(upsilon),
        ctypes.c_double(black_hole_mass),
        ctypes.c_double(black_hole_softening_arcsec),
        ctypes.c_int(dark_halo_profile_type),
        ctypes.c_int(dark_halo_parameters.size),
        None,
        ctypes.c_int(n_radius),
        ctypes.c_int(n_theta),
        ctypes.c_int(n_phi),
        ctypes.c_double(rlogmin),
        ctypes.c_double(rlogmax),
        ctypes.c_double(omega),
        ctypes.c_int(states.shape[0]),
        state_x.ctypes.data_as(double_p),
        state_y.ctypes.data_as(double_p),
        state_z.ctypes.data_as(double_p),
        state_vx.ctypes.data_as(double_p),
        state_vy.ctypes.data_as(double_p),
        state_vz.ctypes.data_as(double_p),
        derivative_x.ctypes.data_as(double_p),
        derivative_y.ctypes.data_as(double_p),
        derivative_z.ctypes.data_as(double_p),
        derivative_vx.ctypes.data_as(double_p),
        derivative_vy.ctypes.data_as(double_p),
        derivative_vz.ctypes.data_as(double_p),
        ctypes.byref(inner_fallback_count),
        ctypes.byref(outer_fallback_count),
        ctypes.byref(status),
    )

    assert status.value == 0
    assert inner_fallback_count.value == expected_inner_fallback_count
    assert outer_fallback_count.value == expected_outer_fallback_count
    actual_derivative = np.column_stack(
        [derivative_x, derivative_y, derivative_z, derivative_vx, derivative_vy, derivative_vz],
    )
    np.testing.assert_allclose(
        actual_derivative,
        expected_derivative,
        rtol=2e-12,
        atol=0.0,
    )


def _synthetic_classification_samples(kind):
    t = np.linspace(0.11, 2.0 * np.pi + 0.11, 97, endpoint=False, dtype=np.float64)
    radius = 3.0
    epsilon = 0.4
    if kind == 1:
        positions = np.column_stack(
            [
                epsilon * np.sin(2.0 * t),
                radius * np.cos(t),
                radius * np.sin(t),
            ],
        )
        velocities = np.column_stack(
            [
                2.0 * epsilon * np.cos(2.0 * t),
                -radius * np.sin(t),
                radius * np.cos(t),
            ],
        )
    elif kind == 2:
        positions = np.column_stack(
            [
                radius * np.cos(t),
                epsilon * np.sin(2.0 * t),
                radius * np.sin(t),
            ],
        )
        velocities = np.column_stack(
            [
                -radius * np.sin(t),
                2.0 * epsilon * np.cos(2.0 * t),
                radius * np.cos(t),
            ],
        )
    elif kind == 3:
        positions = np.column_stack(
            [
                radius * np.cos(t),
                radius * np.sin(t),
                epsilon * np.sin(2.0 * t),
            ],
        )
        velocities = np.column_stack(
            [
                -radius * np.sin(t),
                radius * np.cos(t),
                2.0 * epsilon * np.cos(2.0 * t),
            ],
        )
    elif kind == 4:
        positions = np.column_stack(
            [
                np.cos(t),
                np.cos(1.7 * t + 0.3),
                np.cos(2.3 * t + 0.8),
            ],
        )
        velocities = np.column_stack(
            [
                -np.sin(t),
                -1.7 * np.sin(1.7 * t + 0.3),
                -2.3 * np.sin(2.3 * t + 0.8),
            ],
        )
    elif kind == 5:
        positions = np.column_stack(
            [
                radius * np.cos(t),
                radius * np.sin(t),
                radius * np.cos(t),
            ],
        )
        velocities = np.column_stack(
            [
                -radius * np.sin(t),
                radius * np.cos(t),
                -radius * np.sin(t),
            ],
        )
    else:
        raise ValueError(kind)
    return np.ascontiguousarray(np.column_stack([positions, velocities]), dtype=np.float64)


@pytest.mark.orblib_cpp
@pytest.mark.parametrize("expected_kind", [1, 2, 3, 4, 5])
def test_orblib_cpp_classifies_orbit_samples_like_fortran(expected_kind):
    samples = _synthetic_classification_samples(expected_kind)
    expected_type, expected_moments, expected_moments2 = _expected_orbit_classification(
        samples,
    )
    assert expected_type == expected_kind

    state_x = np.ascontiguousarray(samples[:, 0], dtype=np.float64)
    state_y = np.ascontiguousarray(samples[:, 1], dtype=np.float64)
    state_z = np.ascontiguousarray(samples[:, 2], dtype=np.float64)
    state_vx = np.ascontiguousarray(samples[:, 3], dtype=np.float64)
    state_vy = np.ascontiguousarray(samples[:, 4], dtype=np.float64)
    state_vz = np.ascontiguousarray(samples[:, 5], dtype=np.float64)
    moments = np.empty(5, dtype=np.float64)
    moments2 = np.empty(3, dtype=np.float64)
    orbit_type = ctypes.c_int(-1)
    status = ctypes.c_int(-999)
    library = ctypes.CDLL(str(ORBLIB_CPP_SHARED_LIBRARY))
    function = library.orblib_cpp_api_classify_orbit_samples
    double_p = ctypes.POINTER(ctypes.c_double)
    function.argtypes = [
        ctypes.c_int,
        double_p,
        double_p,
        double_p,
        double_p,
        double_p,
        double_p,
        ctypes.POINTER(ctypes.c_int),
        double_p,
        double_p,
        ctypes.POINTER(ctypes.c_int),
    ]
    function.restype = None
    function(
        ctypes.c_int(samples.shape[0]),
        state_x.ctypes.data_as(double_p),
        state_y.ctypes.data_as(double_p),
        state_z.ctypes.data_as(double_p),
        state_vx.ctypes.data_as(double_p),
        state_vy.ctypes.data_as(double_p),
        state_vz.ctypes.data_as(double_p),
        ctypes.byref(orbit_type),
        moments.ctypes.data_as(double_p),
        moments2.ctypes.data_as(double_p),
        ctypes.byref(status),
    )

    assert status.value == 0
    assert orbit_type.value == expected_kind
    np.testing.assert_allclose(moments, expected_moments, rtol=2e-14, atol=1e-14)
    np.testing.assert_allclose(moments2, expected_moments2, rtol=2e-14, atol=1e-14)


@pytest.mark.orblib_cpp
@pytest.mark.parametrize("omega", [0.0, 1.5e-16])
def test_orblib_cpp_projects_orbit_samples_like_fortran(omega):
    samples = np.ascontiguousarray(
        [
            [1.5, -2.0, 3.5, 11.0, -7.0, 5.0],
            [-4.0, 2.25, -1.5, -3.0, 13.0, -17.0],
            [2.75, 3.25, 0.5, 19.0, -23.0, 29.0],
        ],
        dtype=np.float64,
    )
    theta = np.deg2rad(82.444308859)
    phi = np.deg2rad(84.245110877)
    state_x = np.ascontiguousarray(samples[:, 0], dtype=np.float64)
    state_y = np.ascontiguousarray(samples[:, 1], dtype=np.float64)
    state_z = np.ascontiguousarray(samples[:, 2], dtype=np.float64)
    state_vx = np.ascontiguousarray(samples[:, 3], dtype=np.float64)
    state_vy = np.ascontiguousarray(samples[:, 4], dtype=np.float64)
    state_vz = np.ascontiguousarray(samples[:, 5], dtype=np.float64)
    projected_x = np.empty(samples.shape[0], dtype=np.float64)
    projected_y = np.empty(samples.shape[0], dtype=np.float64)
    los_velocity = np.empty(samples.shape[0], dtype=np.float64)
    status = ctypes.c_int(-999)
    library = ctypes.CDLL(str(ORBLIB_CPP_SHARED_LIBRARY))
    function = library.orblib_cpp_api_project_orbit_samples
    double_p = ctypes.POINTER(ctypes.c_double)
    function.argtypes = [
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_double,
        ctypes.c_double,
        ctypes.c_double,
        ctypes.c_int,
        double_p,
        double_p,
        double_p,
        double_p,
        double_p,
        double_p,
        double_p,
        double_p,
        double_p,
        ctypes.POINTER(ctypes.c_int),
    ]
    function.restype = None

    for orbit_type in range(1, 6):
        for projection_number in range(1, 9):
            expected_x, expected_y, expected_los = _expected_orbit_projection(
                samples,
                orbit_type,
                projection_number,
                omega,
                theta,
                phi,
            )
            projected_x.fill(np.nan)
            projected_y.fill(np.nan)
            los_velocity.fill(np.nan)
            status.value = -999
            function(
                ctypes.c_int(orbit_type),
                ctypes.c_int(projection_number),
                ctypes.c_double(omega),
                ctypes.c_double(theta),
                ctypes.c_double(phi),
                ctypes.c_int(samples.shape[0]),
                state_x.ctypes.data_as(double_p),
                state_y.ctypes.data_as(double_p),
                state_z.ctypes.data_as(double_p),
                state_vx.ctypes.data_as(double_p),
                state_vy.ctypes.data_as(double_p),
                state_vz.ctypes.data_as(double_p),
                projected_x.ctypes.data_as(double_p),
                projected_y.ctypes.data_as(double_p),
                los_velocity.ctypes.data_as(double_p),
                ctypes.byref(status),
            )
            assert status.value == 0
            np.testing.assert_allclose(projected_x, expected_x, rtol=0.0, atol=1e-14)
            np.testing.assert_allclose(projected_y, expected_y, rtol=0.0, atol=1e-14)
            np.testing.assert_allclose(los_velocity, expected_los, rtol=0.0, atol=1e-14)


@pytest.mark.orblib_cpp
@pytest.mark.parametrize(("orbit_type", "omega"), [(3, 0.0), (2, 1.5e-16)])
def test_orblib_cpp_accumulates_qgrid_like_fortran(orbit_type, omega):
    n_radius = 4
    n_theta = 4
    n_phi = 4
    rlogmin = -1.0
    rlogmax = 1.0
    sigobs_km = np.ascontiguousarray([0.3, 1.5], dtype=np.float64)
    samples = np.ascontiguousarray(
        [
            [0.9, 0.3, 0.8, 10.0, -2.0, 4.0],
            [-1.1, -0.7, -0.9, -5.0, 3.0, -6.0],
            [2.0, 0.4, -1.3, 7.0, -11.0, 13.0],
            [-0.6, -0.5, 1.4, -17.0, 19.0, -23.0],
        ],
        dtype=np.float64,
    )
    expected_radius, expected_theta, expected_phi = _expected_qgrid_boundaries(
        rlogmin,
        rlogmax,
        n_radius,
        n_theta,
        n_phi,
        sigobs_km,
    )

    radius = np.empty(n_radius + 1, dtype=np.float64)
    theta = np.empty(n_theta + 1, dtype=np.float64)
    phi = np.empty(n_phi + 1, dtype=np.float64)
    status = ctypes.c_int(-999)
    library = ctypes.CDLL(str(ORBLIB_CPP_SHARED_LIBRARY))
    double_p = ctypes.POINTER(ctypes.c_double)
    boundary_function = library.orblib_cpp_api_qgrid_boundaries
    boundary_function.argtypes = [
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_double,
        ctypes.c_double,
        ctypes.c_int,
        double_p,
        double_p,
        double_p,
        double_p,
        ctypes.POINTER(ctypes.c_int),
    ]
    boundary_function.restype = None
    boundary_function(
        ctypes.c_int(n_radius),
        ctypes.c_int(n_theta),
        ctypes.c_int(n_phi),
        ctypes.c_double(rlogmin),
        ctypes.c_double(rlogmax),
        ctypes.c_int(sigobs_km.size),
        sigobs_km.ctypes.data_as(double_p),
        radius.ctypes.data_as(double_p),
        theta.ctypes.data_as(double_p),
        phi.ctypes.data_as(double_p),
        ctypes.byref(status),
    )

    assert status.value == 0
    np.testing.assert_allclose(radius, expected_radius, rtol=0.0, atol=2e-15)
    np.testing.assert_allclose(theta, expected_theta, rtol=0.0, atol=2e-15)
    np.testing.assert_allclose(phi, expected_phi, rtol=0.0, atol=2e-15)

    expected_raw = _expected_qgrid_raw(samples, orbit_type, omega, radius, theta, phi)
    expected_normalized = _expected_qgrid_normalized(expected_raw, n_radius, n_theta, n_phi)
    assert expected_raw[_qgrid_index(0, 0, 0, 0, n_phi, n_theta)] == 0.0
    if omega == 0.0:
        assert np.sum(expected_raw[0::16]) == samples.shape[0]
    else:
        assert np.sum(expected_raw[0::16]) == 2 * samples.shape[0]

    qgrid = np.zeros(16 * n_phi * n_theta * n_radius, dtype=np.float64)
    state_x = np.ascontiguousarray(samples[:, 0], dtype=np.float64)
    state_y = np.ascontiguousarray(samples[:, 1], dtype=np.float64)
    state_z = np.ascontiguousarray(samples[:, 2], dtype=np.float64)
    state_vx = np.ascontiguousarray(samples[:, 3], dtype=np.float64)
    state_vy = np.ascontiguousarray(samples[:, 4], dtype=np.float64)
    state_vz = np.ascontiguousarray(samples[:, 5], dtype=np.float64)
    accumulate_function = library.orblib_cpp_api_accumulate_qgrid
    accumulate_function.argtypes = [
        ctypes.c_int,
        ctypes.c_double,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_int,
        double_p,
        double_p,
        double_p,
        ctypes.c_int,
        double_p,
        double_p,
        double_p,
        double_p,
        double_p,
        double_p,
        double_p,
        ctypes.POINTER(ctypes.c_int),
    ]
    accumulate_function.restype = None
    status.value = -999
    accumulate_function(
        ctypes.c_int(orbit_type),
        ctypes.c_double(omega),
        ctypes.c_int(n_radius),
        ctypes.c_int(n_theta),
        ctypes.c_int(n_phi),
        radius.ctypes.data_as(double_p),
        theta.ctypes.data_as(double_p),
        phi.ctypes.data_as(double_p),
        ctypes.c_int(samples.shape[0]),
        state_x.ctypes.data_as(double_p),
        state_y.ctypes.data_as(double_p),
        state_z.ctypes.data_as(double_p),
        state_vx.ctypes.data_as(double_p),
        state_vy.ctypes.data_as(double_p),
        state_vz.ctypes.data_as(double_p),
        qgrid.ctypes.data_as(double_p),
        ctypes.byref(status),
    )

    assert status.value == 0
    np.testing.assert_allclose(qgrid, expected_raw, rtol=0.0, atol=1e-14)

    normalize_function = library.orblib_cpp_api_normalize_qgrid
    normalize_function.argtypes = [
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_int,
        double_p,
        ctypes.POINTER(ctypes.c_int),
    ]
    normalize_function.restype = None
    status.value = -999
    normalize_function(
        ctypes.c_int(n_radius),
        ctypes.c_int(n_theta),
        ctypes.c_int(n_phi),
        qgrid.ctypes.data_as(double_p),
        ctypes.byref(status),
    )

    assert status.value == 0
    np.testing.assert_allclose(qgrid, expected_normalized, rtol=0.0, atol=1e-14)


@pytest.mark.orblib_cpp
def test_orblib_cpp_writes_qgrid_file_readable_by_scipy_fortranfile(tmp_path):
    orbit_count = 2
    energy_count = 1
    i2_count = 1
    i3_count = 2
    dithering = 2
    dither_count = dithering**3
    not_regularizable_count = 3
    n_radius = 2
    n_theta = 2
    n_phi = 3
    radius = np.ascontiguousarray([0.0, 1.5, 12.0], dtype=np.float64)
    theta = np.ascontiguousarray([0.0, 0.25 * np.pi, 0.5 * np.pi], dtype=np.float64)
    phi = np.ascontiguousarray([0.0, 0.2, 0.7, 0.5 * np.pi], dtype=np.float64)
    orbit_types = np.ascontiguousarray(
        np.arange(1, orbit_count * dither_count + 1, dtype=np.int32),
    )
    values_per_orbit = 16 * n_phi * n_theta * n_radius
    qgrids = np.ascontiguousarray(
        np.arange(orbit_count * values_per_orbit, dtype=np.float64) / 11.0,
    )
    output_path = tmp_path / "orblib_qgrid.dat"

    status = ctypes.c_int(-999)
    library = ctypes.CDLL(str(ORBLIB_CPP_SHARED_LIBRARY))
    double_p = ctypes.POINTER(ctypes.c_double)
    int_p = ctypes.POINTER(ctypes.c_int)
    function = library.orblib_cpp_api_write_qgrid_file
    function.argtypes = [
        ctypes.c_char_p,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_int,
        double_p,
        double_p,
        double_p,
        int_p,
        double_p,
        ctypes.POINTER(ctypes.c_int),
    ]
    function.restype = None
    function(
        str(output_path).encode(),
        ctypes.c_int(orbit_count),
        ctypes.c_int(energy_count),
        ctypes.c_int(i2_count),
        ctypes.c_int(i3_count),
        ctypes.c_int(dithering),
        ctypes.c_int(not_regularizable_count),
        ctypes.c_int(n_radius),
        ctypes.c_int(n_theta),
        ctypes.c_int(n_phi),
        radius.ctypes.data_as(double_p),
        theta.ctypes.data_as(double_p),
        phi.ctypes.data_as(double_p),
        orbit_types.ctypes.data_as(int_p),
        qgrids.ctypes.data_as(double_p),
        ctypes.byref(status),
    )

    assert status.value == 0
    reader = scipy.io.FortranFile(output_path, "r")
    try:
        np.testing.assert_array_equal(
            reader.read_ints(np.int32),
            np.array([orbit_count, energy_count, i2_count, i3_count, dithering], dtype=np.int32),
        )
        np.testing.assert_array_equal(
            reader.read_ints(np.int32),
            np.array([16, n_phi, n_theta, n_radius], dtype=np.int32),
        )
        np.testing.assert_array_equal(reader.read_reals(float), radius)
        np.testing.assert_array_equal(reader.read_reals(float), theta)
        np.testing.assert_array_equal(reader.read_reals(float), phi)
        expected_orbit_headers = [
            np.array([1, 1, 1, 1, not_regularizable_count], dtype=np.int32),
            np.array([2, 1, 1, 2, not_regularizable_count], dtype=np.int32),
        ]
        for orbit_index, expected_header in enumerate(expected_orbit_headers):
            np.testing.assert_array_equal(reader.read_ints(np.int32), expected_header)
            begin = orbit_index * dither_count
            end = begin + dither_count
            np.testing.assert_array_equal(reader.read_ints(np.int32), orbit_types[begin:end])
            qgrid_begin = orbit_index * values_per_orbit
            qgrid_end = qgrid_begin + values_per_orbit
            np.testing.assert_array_equal(reader.read_reals(float), qgrids[qgrid_begin:qgrid_end])
    finally:
        reader.close()


@pytest.mark.orblib_cpp
@pytest.mark.parametrize(
    ("weights", "sigmas", "sigma_scale"),
    [
        ([1.0], [0.05], 10.0),
        ([1.0], [0.35], 10.0),
        ([0.2, 0.7, -0.1], [0.1, 0.4, 0.9], 10.0),
    ],
)
def test_orblib_cpp_applies_psf_like_fortran(weights, sigmas, sigma_scale):
    projected = np.ascontiguousarray(
        [
            [1.5, -2.0],
            [-4.0, 2.25],
            [2.75, 3.25],
            [0.5, -0.75],
            [7.0, 8.0],
            [-1.25, 4.5],
            [3.5, -6.0],
        ],
        dtype=np.float64,
    )
    weights = np.ascontiguousarray(weights, dtype=np.float64)
    sigmas = np.ascontiguousarray(sigmas, dtype=np.float64)
    seed = -4242
    expected = _expected_psf_application(projected, weights, sigmas, sigma_scale, seed)

    convolved_x = np.empty(projected.shape[0], dtype=np.float64)
    convolved_y = np.empty(projected.shape[0], dtype=np.float64)
    status = ctypes.c_int(-999)
    library = ctypes.CDLL(str(ORBLIB_CPP_SHARED_LIBRARY))
    function = library.orblib_cpp_api_apply_psf
    double_p = ctypes.POINTER(ctypes.c_double)
    function.argtypes = [
        ctypes.c_int,
        double_p,
        double_p,
        ctypes.c_double,
        ctypes.c_int,
        double_p,
        double_p,
        ctypes.c_int,
        double_p,
        double_p,
        ctypes.POINTER(ctypes.c_int),
    ]
    function.restype = None

    function(
        ctypes.c_int(sigmas.size),
        weights.ctypes.data_as(double_p),
        sigmas.ctypes.data_as(double_p),
        ctypes.c_double(sigma_scale),
        ctypes.c_int(projected.shape[0]),
        np.ascontiguousarray(projected[:, 0], dtype=np.float64).ctypes.data_as(double_p),
        np.ascontiguousarray(projected[:, 1], dtype=np.float64).ctypes.data_as(double_p),
        ctypes.c_int(seed),
        convolved_x.ctypes.data_as(double_p),
        convolved_y.ctypes.data_as(double_p),
        ctypes.byref(status),
    )

    assert status.value == 0
    actual = np.column_stack([convolved_x, convolved_y])
    np.testing.assert_allclose(actual, expected, rtol=0.0, atol=2e-6)


@pytest.mark.orblib_cpp
def test_orblib_cpp_maps_boxed_aperture_pixels_like_fortran():
    begin = np.array([2.0, -3.0], dtype=np.float64)
    size = np.array([10.0, 8.0], dtype=np.float64)
    rotation_degrees = 27.0
    bins_x = 5
    bins_y = 4
    psi_radians = np.deg2rad(18.0)
    coordinate_scale = 3.0
    local_points = np.ascontiguousarray(
        [
            [0.1, 0.1],
            [5.999, 0.5],
            [6.001, 0.5],
            [29.9, 0.5],
            [0.5, 6.001],
            [17.9, 18.1],
            [29.9, 23.9],
            [0.0, 1.0],
            [30.0, 1.0],
            [1.0, 0.0],
            [1.0, 24.0],
            [-0.1, 1.0],
            [1.0, -0.1],
            [30.1, 1.0],
            [1.0, 24.1],
        ],
        dtype=np.float64,
    )
    projected = _projected_from_boxed_aperture_local(
        local_points,
        begin,
        rotation_degrees,
        psi_radians,
        coordinate_scale,
    )
    expected = _expected_boxed_aperture_pixels(
        projected,
        begin,
        size,
        rotation_degrees,
        bins_x,
        bins_y,
        psi_radians,
        coordinate_scale,
    )
    np.testing.assert_array_equal(
        expected,
        np.array([1, 1, 2, 5, 6, 18, 20, 0, 0, 0, 0, 0, 0, 0, 0], dtype=np.int32),
    )

    projected_x = np.ascontiguousarray(projected[:, 0], dtype=np.float64)
    projected_y = np.ascontiguousarray(projected[:, 1], dtype=np.float64)
    pixels = np.full(projected.shape[0], -1, dtype=np.int32)
    status = ctypes.c_int(-999)
    library = ctypes.CDLL(str(ORBLIB_CPP_SHARED_LIBRARY))
    function = library.orblib_cpp_api_find_boxed_aperture_pixels
    double_p = ctypes.POINTER(ctypes.c_double)
    int_p = ctypes.POINTER(ctypes.c_int)
    function.argtypes = [
        ctypes.c_double,
        ctypes.c_double,
        ctypes.c_double,
        ctypes.c_double,
        ctypes.c_double,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_double,
        ctypes.c_double,
        ctypes.c_int,
        double_p,
        double_p,
        int_p,
        ctypes.POINTER(ctypes.c_int),
    ]
    function.restype = None

    function(
        ctypes.c_double(begin[0]),
        ctypes.c_double(begin[1]),
        ctypes.c_double(size[0]),
        ctypes.c_double(size[1]),
        ctypes.c_double(rotation_degrees),
        ctypes.c_int(bins_x),
        ctypes.c_int(bins_y),
        ctypes.c_double(psi_radians),
        ctypes.c_double(coordinate_scale),
        ctypes.c_int(projected.shape[0]),
        projected_x.ctypes.data_as(double_p),
        projected_y.ctypes.data_as(double_p),
        pixels.ctypes.data_as(int_p),
        ctypes.byref(status),
    )

    assert status.value == 0
    np.testing.assert_array_equal(pixels, expected)


@pytest.mark.orblib_cpp
def test_orblib_cpp_accumulates_losvd_histogram_like_fortran():
    histogram_width = 20.0
    histogram_center = 5.0
    bin_count = 5
    los_velocity = np.ascontiguousarray(
        [
            -20.0,
            -5.0,
            -4.999,
            -1.0,
            -0.999,
            2.999,
            3.0,
            6.999,
            7.0,
            10.999,
            11.0,
            14.999,
            15.0,
            50.0,
        ],
        dtype=np.float64,
    )
    expected_velocity_bins = _expected_losvd_velocity_bins(
        los_velocity,
        histogram_width,
        histogram_center,
        bin_count,
    )
    np.testing.assert_array_equal(
        expected_velocity_bins,
        np.array([1, 1, 1, 2, 2, 2, 3, 3, 4, 4, 5, 5, 5, 5], dtype=np.int32),
    )

    velocity_bins = np.full(los_velocity.size, -1, dtype=np.int32)
    status = ctypes.c_int(-999)
    library = ctypes.CDLL(str(ORBLIB_CPP_SHARED_LIBRARY))
    double_p = ctypes.POINTER(ctypes.c_double)
    int_p = ctypes.POINTER(ctypes.c_int)

    velocity_function = library.orblib_cpp_api_losvd_velocity_bins
    velocity_function.argtypes = [
        ctypes.c_double,
        ctypes.c_double,
        ctypes.c_int,
        ctypes.c_int,
        double_p,
        int_p,
        ctypes.POINTER(ctypes.c_int),
    ]
    velocity_function.restype = None
    velocity_function(
        ctypes.c_double(histogram_width),
        ctypes.c_double(histogram_center),
        ctypes.c_int(bin_count),
        ctypes.c_int(los_velocity.size),
        los_velocity.ctypes.data_as(double_p),
        velocity_bins.ctypes.data_as(int_p),
        ctypes.byref(status),
    )

    assert status.value == 0
    np.testing.assert_array_equal(velocity_bins, expected_velocity_bins)

    aperture_pixels = np.ascontiguousarray(
        [1, 2, 0, 3, 2, 4, 5, 5, 1, 0, 4, 2, 3, 5],
        dtype=np.int32,
    )
    aperture_pixel_count = 5
    expected_histogram = _expected_losvd_histogram(
        aperture_pixels,
        expected_velocity_bins,
        aperture_pixel_count,
        bin_count,
    )
    np.testing.assert_array_equal(
        expected_histogram,
        np.array(
            [
                [1.0, 0.0, 0.0, 1.0, 0.0],
                [1.0, 1.0, 0.0, 0.0, 1.0],
                [0.0, 1.0, 0.0, 0.0, 1.0],
                [0.0, 1.0, 0.0, 0.0, 1.0],
                [0.0, 0.0, 2.0, 0.0, 1.0],
            ],
            dtype=np.float64,
        ),
    )

    histogram = np.zeros((aperture_pixel_count, bin_count), dtype=np.float64)
    stored_count = ctypes.c_double(3.5)
    accumulate_function = library.orblib_cpp_api_accumulate_losvd_histogram
    accumulate_function.argtypes = [
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_int,
        int_p,
        int_p,
        ctypes.c_int,
        double_p,
        ctypes.POINTER(ctypes.c_double),
        ctypes.POINTER(ctypes.c_int),
    ]
    accumulate_function.restype = None
    status.value = -999
    accumulate_function(
        ctypes.c_int(aperture_pixel_count),
        ctypes.c_int(bin_count),
        ctypes.c_int(aperture_pixels.size),
        aperture_pixels.ctypes.data_as(int_p),
        velocity_bins.ctypes.data_as(int_p),
        ctypes.c_int(aperture_pixels.size),
        histogram.ctypes.data_as(double_p),
        ctypes.byref(stored_count),
        ctypes.byref(status),
    )

    assert status.value == 0
    assert stored_count.value == pytest.approx(3.5 + aperture_pixels.size)
    np.testing.assert_array_equal(histogram, expected_histogram)


@pytest.mark.orblib_cpp
def test_orblib_cpp_prepares_sparse_losvd_rows_like_fortran():
    source_histogram = np.ascontiguousarray(
        [
            [0.0, 2.0, 0.0, 0.0, 1.0],
            [1.0, 0.0, 3.0, 0.0, 0.0],
            [0.0, 0.0, 0.0, 0.0, 0.0],
            [4.0, 0.0, 0.0, 5.0, 0.0],
            [0.0, 6.0, 0.0, 0.0, 0.0],
            [7.0, 0.0, 0.0, 0.0, 8.0],
        ],
        dtype=np.float64,
    )
    bin_order = np.ascontiguousarray([1, 2, 0, 2, 3, 1], dtype=np.int32)
    target_pixel_count = 3
    velocity_bin_count = source_histogram.shape[1]
    stored_count = 20.0
    expected_collapsed = _expected_collapsed_losvd_histogram(
        source_histogram,
        bin_order,
        target_pixel_count,
    )
    expected_normalized = expected_collapsed / stored_count
    expected_begin, expected_end = _expected_sparse_losvd_ranges(expected_normalized)
    np.testing.assert_array_equal(
        expected_collapsed,
        np.array(
            [
                [7.0, 2.0, 0.0, 0.0, 9.0],
                [5.0, 0.0, 3.0, 5.0, 0.0],
                [0.0, 6.0, 0.0, 0.0, 0.0],
            ],
            dtype=np.float64,
        ),
    )
    np.testing.assert_array_equal(expected_begin, np.array([-2, -2, -1], dtype=np.int32))
    np.testing.assert_array_equal(expected_end, np.array([2, 1, -1], dtype=np.int32))

    library = ctypes.CDLL(str(ORBLIB_CPP_SHARED_LIBRARY))
    double_p = ctypes.POINTER(ctypes.c_double)
    int_p = ctypes.POINTER(ctypes.c_int)
    status = ctypes.c_int(-999)

    collapsed = np.full((target_pixel_count, velocity_bin_count), np.nan, dtype=np.float64)
    collapse_function = library.orblib_cpp_api_collapse_losvd_binning
    collapse_function.argtypes = [
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_int,
        int_p,
        double_p,
        double_p,
        ctypes.POINTER(ctypes.c_int),
    ]
    collapse_function.restype = None
    collapse_function(
        ctypes.c_int(source_histogram.shape[0]),
        ctypes.c_int(velocity_bin_count),
        ctypes.c_int(target_pixel_count),
        bin_order.ctypes.data_as(int_p),
        source_histogram.ctypes.data_as(double_p),
        collapsed.ctypes.data_as(double_p),
        ctypes.byref(status),
    )

    assert status.value == 0
    np.testing.assert_array_equal(collapsed, expected_collapsed)

    normalize_function = library.orblib_cpp_api_normalize_losvd_histogram
    normalize_function.argtypes = [
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_double,
        double_p,
        ctypes.POINTER(ctypes.c_int),
    ]
    normalize_function.restype = None
    status.value = -999
    normalize_function(
        ctypes.c_int(target_pixel_count),
        ctypes.c_int(velocity_bin_count),
        ctypes.c_double(stored_count),
        collapsed.ctypes.data_as(double_p),
        ctypes.byref(status),
    )

    assert status.value == 0
    np.testing.assert_allclose(collapsed, expected_normalized, rtol=0.0, atol=1e-15)

    begin_offsets = np.full(target_pixel_count, 999, dtype=np.int32)
    end_offsets = np.full(target_pixel_count, 999, dtype=np.int32)
    sparse_function = library.orblib_cpp_api_sparse_losvd_ranges
    sparse_function.argtypes = [
        ctypes.c_int,
        ctypes.c_int,
        double_p,
        int_p,
        int_p,
        ctypes.POINTER(ctypes.c_int),
    ]
    sparse_function.restype = None
    status.value = -999
    sparse_function(
        ctypes.c_int(target_pixel_count),
        ctypes.c_int(velocity_bin_count),
        collapsed.ctypes.data_as(double_p),
        begin_offsets.ctypes.data_as(int_p),
        end_offsets.ctypes.data_as(int_p),
        ctypes.byref(status),
    )

    assert status.value == 0
    np.testing.assert_array_equal(begin_offsets, expected_begin)
    np.testing.assert_array_equal(end_offsets, expected_end)

    empty_histogram = np.zeros((1, velocity_bin_count), dtype=np.float64)
    expected_empty_begin, expected_empty_end = _expected_sparse_losvd_ranges(empty_histogram)
    status.value = -999
    sparse_function(
        ctypes.c_int(1),
        ctypes.c_int(velocity_bin_count),
        empty_histogram.ctypes.data_as(double_p),
        begin_offsets[:1].ctypes.data_as(int_p),
        end_offsets[:1].ctypes.data_as(int_p),
        ctypes.byref(status),
    )

    assert status.value == 0
    np.testing.assert_array_equal(begin_offsets[:1], expected_empty_begin)
    np.testing.assert_array_equal(end_offsets[:1], expected_empty_end)


@pytest.mark.orblib_cpp
def test_orblib_cpp_writes_losvd_histogram_file_readable_by_scipy_fortranfile(tmp_path):
    orbit_count = 2
    aperture_count = 3
    velocity_bin_count = 5
    velocity_bin_width = 4.5
    histograms = np.ascontiguousarray(
        [
            [0.0, 0.2, 0.0, 0.0, 0.1],
            [0.3, 0.0, 0.0, 0.4, 0.0],
            [0.0, 0.0, 0.0, 0.0, 0.0],
            [0.0, 0.0, 0.5, 0.0, 0.0],
            [0.6, 0.0, 0.7, 0.0, 0.8],
            [0.0, 0.9, 0.0, 1.0, 0.0],
        ],
        dtype=np.float64,
    )
    begin_offsets, end_offsets = _expected_sparse_losvd_ranges(histograms)
    output_path = tmp_path / "orblib_losvd_hist.dat"

    status = ctypes.c_int(-999)
    library = ctypes.CDLL(str(ORBLIB_CPP_SHARED_LIBRARY))
    double_p = ctypes.POINTER(ctypes.c_double)
    int_p = ctypes.POINTER(ctypes.c_int)
    function = library.orblib_cpp_api_write_losvd_histogram_file
    function.argtypes = [
        ctypes.c_char_p,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_double,
        int_p,
        int_p,
        double_p,
        ctypes.POINTER(ctypes.c_int),
    ]
    function.restype = None
    function(
        str(output_path).encode(),
        ctypes.c_int(orbit_count),
        ctypes.c_int(aperture_count),
        ctypes.c_int(velocity_bin_count),
        ctypes.c_double(velocity_bin_width),
        begin_offsets.ctypes.data_as(int_p),
        end_offsets.ctypes.data_as(int_p),
        histograms.ctypes.data_as(double_p),
        ctypes.byref(status),
    )

    assert status.value == 0
    reader = scipy.io.FortranFile(output_path, "r")
    try:
        header_apertures, header_half_bins, header_bin_width = reader.read_record(
            np.int32,
            np.int32,
            float,
        )
        np.testing.assert_array_equal(header_apertures, np.array([aperture_count], dtype=np.int32))
        np.testing.assert_array_equal(
            header_half_bins,
            np.array([velocity_bin_count // 2], dtype=np.int32),
        )
        np.testing.assert_array_equal(header_bin_width, np.array([velocity_bin_width], dtype=np.float64))
        for row_index, row in enumerate(histograms):
            row_begin, row_end = reader.read_ints(np.int32)
            assert row_begin == begin_offsets[row_index]
            assert row_end == end_offsets[row_index]
            if row_begin <= row_end:
                first_bin = row_begin + velocity_bin_count // 2
                last_bin = row_end + velocity_bin_count // 2
                np.testing.assert_array_equal(
                    reader.read_reals(float),
                    row[first_bin:last_bin + 1],
                )
    finally:
        reader.close()


@pytest.mark.orblib_cpp
def test_orblib_cpp_writes_population_mass_file_readable_by_scipy_fortranfile(tmp_path):
    orbit_count = 3
    aperture_counts = np.ascontiguousarray([2, 4], dtype=np.int32)
    population_count = aperture_counts.size
    total_apertures = int(np.sum(aperture_counts))
    masses = np.ascontiguousarray(
        np.arange(1, orbit_count * total_apertures + 1, dtype=np.float64).reshape(
            orbit_count,
            total_apertures,
        ),
    )
    output_path = tmp_path / "orblib_pops.dat"

    status = ctypes.c_int(-999)
    library = ctypes.CDLL(str(ORBLIB_CPP_SHARED_LIBRARY))
    double_p = ctypes.POINTER(ctypes.c_double)
    int_p = ctypes.POINTER(ctypes.c_int)
    function = library.orblib_cpp_api_write_population_mass_file
    function.argtypes = [
        ctypes.c_char_p,
        ctypes.c_int,
        ctypes.c_int,
        int_p,
        double_p,
        ctypes.POINTER(ctypes.c_int),
    ]
    function.restype = None
    function(
        str(output_path).encode(),
        ctypes.c_int(orbit_count),
        ctypes.c_int(population_count),
        aperture_counts.ctypes.data_as(int_p),
        masses.ctypes.data_as(double_p),
        ctypes.byref(status),
    )

    assert status.value == 0
    reader = scipy.io.FortranFile(output_path, "r")
    try:
        for orbit_index in range(orbit_count):
            offset = 0
            for aperture_count in aperture_counts:
                expected = masses[orbit_index, offset:offset + aperture_count]
                np.testing.assert_array_equal(reader.read_reals(float), expected)
                offset += aperture_count
    finally:
        reader.close()


@pytest.mark.orblib_cpp
def test_orblib_cpp_writes_orbit_class_file_like_fortran_reader(tmp_path):
    orbit_count = 3
    dither_count = 4
    moments = np.ascontiguousarray(
        np.arange(1, orbit_count * dither_count * 5 + 1, dtype=np.float64),
    )
    output_path = tmp_path / "orblib.dat_orbclass.out"

    status = ctypes.c_int(-999)
    library = ctypes.CDLL(str(ORBLIB_CPP_SHARED_LIBRARY))
    double_p = ctypes.POINTER(ctypes.c_double)
    function = library.orblib_cpp_api_write_orbit_class_file
    function.argtypes = [
        ctypes.c_char_p,
        ctypes.c_int,
        ctypes.c_int,
        double_p,
        ctypes.POINTER(ctypes.c_int),
    ]
    function.restype = None
    function(
        str(output_path).encode(),
        ctypes.c_int(orbit_count),
        ctypes.c_int(dither_count),
        moments.ctypes.data_as(double_p),
        ctypes.byref(status),
    )

    assert status.value == 0
    tokens = []
    for line in output_path.read_text().splitlines():
        tokens.extend(float(value) for value in line.split())
        assert len(line.split()) <= 25
    data = np.array(tokens, dtype=np.float64)
    assert data.size == 5 * dither_count * orbit_count
    actual = data.reshape((5, dither_count, orbit_count), order="F")
    expected = moments.reshape((5, dither_count, orbit_count), order="F")
    np.testing.assert_array_equal(actual, expected)


@pytest.mark.orblib_cpp
@pytest.mark.parametrize("energy_offset", [-40.0, 40.0])
def test_orblib_cpp_orbitstart_calculates_start_state_like_fortran(energy_offset):
    surf_pc = np.array([0.0], dtype=np.float64)
    sigobs_arcsec = np.array([0.49416], dtype=np.float64)
    qobs = np.array([0.89541], dtype=np.float64)
    psi_obs = np.zeros_like(qobs)
    theta = 82.444308859
    psi = 90.021481540
    phi = 84.245110877
    distance = 39.9
    upsilon = 1.0
    black_hole_mass = 2.0e9
    black_hole_softening_arcsec = 0.02
    dark_halo_profile_type = 0
    dark_halo_parameters = np.ascontiguousarray([], dtype=np.float64)
    start_radius = 1.2e13
    start_theta = 0.73
    expected_setup = _expected_triaxial_mge_setup(
        surf_pc,
        sigobs_arcsec,
        qobs,
        psi_obs,
        distance,
        theta,
        phi,
        psi,
        upsilon,
    )
    position = np.array(
        [[start_radius * np.sin(start_theta), 0.0, start_radius * np.cos(start_theta)]],
        dtype=np.float64,
    )
    potential, _ = _expected_potential_stack_evaluation(
        expected_setup,
        position,
        black_hole_mass,
        black_hole_softening_arcsec,
        dark_halo_profile_type,
        dark_halo_parameters,
    )
    energy = potential[0] + energy_offset
    vy = 2.0 * (potential[0] - energy)
    if vy >= 1.0e-300:
        vy = np.sqrt(vy)
    if vy < 0.0 or np.isnan(vy):
        vy = np.sqrt(2.0 * potential[0] * 1.0e-12)
    expected_state = np.array(
        [position[0, 0], 0.0, position[0, 2], 0.0, vy, 0.0],
        dtype=np.float64,
    )

    state = np.empty(6, dtype=np.float64)
    status = ctypes.c_int(-999)
    library = ctypes.CDLL(str(ORBLIB_CPP_SHARED_LIBRARY))
    double_p = ctypes.POINTER(ctypes.c_double)
    function = library.orblib_cpp_api_orbitstart_calc_start_state
    function.argtypes = [
        ctypes.c_int,
        double_p,
        double_p,
        double_p,
        double_p,
        ctypes.c_double,
        ctypes.c_double,
        ctypes.c_double,
        ctypes.c_double,
        ctypes.c_double,
        ctypes.c_double,
        ctypes.c_double,
        ctypes.c_int,
        ctypes.c_int,
        double_p,
        ctypes.c_double,
        ctypes.c_double,
        ctypes.c_double,
        double_p,
        ctypes.POINTER(ctypes.c_int),
    ]
    function.restype = None
    function(
        ctypes.c_int(surf_pc.size),
        surf_pc.ctypes.data_as(double_p),
        sigobs_arcsec.ctypes.data_as(double_p),
        qobs.ctypes.data_as(double_p),
        psi_obs.ctypes.data_as(double_p),
        ctypes.c_double(distance),
        ctypes.c_double(theta),
        ctypes.c_double(phi),
        ctypes.c_double(psi),
        ctypes.c_double(upsilon),
        ctypes.c_double(black_hole_mass),
        ctypes.c_double(black_hole_softening_arcsec),
        ctypes.c_int(dark_halo_profile_type),
        ctypes.c_int(dark_halo_parameters.size),
        None,
        ctypes.c_double(start_radius),
        ctypes.c_double(start_theta),
        ctypes.c_double(energy),
        state.ctypes.data_as(double_p),
        ctypes.byref(status),
    )

    assert status.value == 0
    np.testing.assert_allclose(state, expected_state, rtol=0.0, atol=1e-10)


@pytest.mark.orblib_cpp
def test_orblib_cpp_orbitstart_finds_equivalent_radius_like_fortran():
    surf_pc = np.array([0.0], dtype=np.float64)
    sigobs_arcsec = np.array([0.49416], dtype=np.float64)
    qobs = np.array([0.89541], dtype=np.float64)
    psi_obs = np.zeros_like(qobs)
    theta = 82.444308859
    psi = 90.021481540
    phi = 84.245110877
    distance = 39.9
    upsilon = 1.0
    black_hole_mass = 2.0e9
    black_hole_softening_arcsec = 0.02
    dark_halo_profile_type = 0
    dark_halo_parameters = np.ascontiguousarray([], dtype=np.float64)
    request_radius = 1.0e13
    expected_radius = 0.77 * request_radius
    start_theta = 0.9
    start_phi = 0.4
    expected_setup = _expected_triaxial_mge_setup(
        surf_pc,
        sigobs_arcsec,
        qobs,
        psi_obs,
        distance,
        theta,
        phi,
        psi,
        upsilon,
    )
    point = np.array(
        [
            [
                expected_radius * np.sin(start_theta) * np.cos(start_phi),
                expected_radius * np.sin(start_theta) * np.sin(start_phi),
                expected_radius * np.cos(start_theta),
            ],
        ],
        dtype=np.float64,
    )
    potential, _ = _expected_potential_stack_evaluation(
        expected_setup,
        point,
        black_hole_mass,
        black_hole_softening_arcsec,
        dark_halo_profile_type,
        dark_halo_parameters,
    )

    def potential_at_radius(radius_value):
        radius_point = np.array(
            [
                [
                    radius_value * np.sin(start_theta) * np.cos(start_phi),
                    radius_value * np.sin(start_theta) * np.sin(start_phi),
                    radius_value * np.cos(start_theta),
                ],
            ],
            dtype=np.float64,
        )
        radius_potential, _ = _expected_potential_stack_evaluation(
            expected_setup,
            radius_point,
            black_hole_mass,
            black_hole_softening_arcsec,
            dark_halo_profile_type,
            dark_halo_parameters,
        )
        return radius_potential[0]

    min_radius = 0.01 * request_radius
    max_radius = 1.1 * request_radius
    expected_bisection_radius = np.nan
    expected_iterations = -1
    for iteration in range(60001):
        expected_bisection_radius = 0.5 * (min_radius + max_radius)
        midpoint_potential = potential_at_radius(expected_bisection_radius)
        if abs((potential[0] - midpoint_potential) / potential[0]) < 1.0e-7:
            expected_iterations = iteration
            break
        if midpoint_potential > potential[0]:
            min_radius = expected_bisection_radius
        else:
            max_radius = expected_bisection_radius
    assert expected_iterations > 0

    radius = ctypes.c_double(np.nan)
    iterations = ctypes.c_int(-1)
    status = ctypes.c_int(-999)
    library = ctypes.CDLL(str(ORBLIB_CPP_SHARED_LIBRARY))
    double_p = ctypes.POINTER(ctypes.c_double)
    function = library.orblib_cpp_api_orbitstart_find_equivalent_radius
    function.argtypes = [
        ctypes.c_int,
        double_p,
        double_p,
        double_p,
        double_p,
        ctypes.c_double,
        ctypes.c_double,
        ctypes.c_double,
        ctypes.c_double,
        ctypes.c_double,
        ctypes.c_double,
        ctypes.c_double,
        ctypes.c_int,
        ctypes.c_int,
        double_p,
        ctypes.c_double,
        ctypes.c_double,
        ctypes.c_double,
        ctypes.c_double,
        ctypes.POINTER(ctypes.c_double),
        ctypes.POINTER(ctypes.c_int),
        ctypes.POINTER(ctypes.c_int),
    ]
    function.restype = None
    function(
        ctypes.c_int(surf_pc.size),
        surf_pc.ctypes.data_as(double_p),
        sigobs_arcsec.ctypes.data_as(double_p),
        qobs.ctypes.data_as(double_p),
        psi_obs.ctypes.data_as(double_p),
        ctypes.c_double(distance),
        ctypes.c_double(theta),
        ctypes.c_double(phi),
        ctypes.c_double(psi),
        ctypes.c_double(upsilon),
        ctypes.c_double(black_hole_mass),
        ctypes.c_double(black_hole_softening_arcsec),
        ctypes.c_int(dark_halo_profile_type),
        ctypes.c_int(dark_halo_parameters.size),
        None,
        ctypes.c_double(request_radius),
        ctypes.c_double(potential[0]),
        ctypes.c_double(start_theta),
        ctypes.c_double(start_phi),
        ctypes.byref(radius),
        ctypes.byref(iterations),
        ctypes.byref(status),
    )

    assert status.value == 0
    assert iterations.value == expected_iterations
    assert radius.value == pytest.approx(expected_bisection_radius, rel=0.0, abs=1e-6)


@pytest.mark.orblib_cpp
def test_orblib_cpp_orbitstart_box_record_matches_fortran_grid_formula():
    surf_pc = np.array([0.0], dtype=np.float64)
    sigobs_arcsec = np.array([0.49416], dtype=np.float64)
    qobs = np.array([0.89541], dtype=np.float64)
    psi_obs = np.zeros_like(qobs)
    theta = 82.444308859
    psi = 90.021481540
    phi = 84.245110877
    distance = 39.9
    upsilon = 1.0
    black_hole_mass = 2.0e9
    black_hole_softening_arcsec = 0.02
    dark_halo_profile_type = 0
    dark_halo_parameters = np.ascontiguousarray([], dtype=np.float64)
    request_radius = 1.0e13
    target_radius = 0.73 * request_radius
    i2_count = 5
    i3_count = 4
    i2_index = 2
    i3_index = 1
    circular_radius = request_radius
    circular_period = 6.25e5
    circular_velocity = 217.5
    start_theta = 0.5 * np.pi * (i2_index + 0.5) / i2_count
    start_phi = 0.5 * np.pi * (i3_index + 0.5) / i3_count
    expected_setup = _expected_triaxial_mge_setup(
        surf_pc,
        sigobs_arcsec,
        qobs,
        psi_obs,
        distance,
        theta,
        phi,
        psi,
        upsilon,
    )

    def potential_at_radius(radius_value):
        radius_point = np.array(
            [
                [
                    radius_value * np.sin(start_theta) * np.cos(start_phi),
                    radius_value * np.sin(start_theta) * np.sin(start_phi),
                    radius_value * np.cos(start_theta),
                ],
            ],
            dtype=np.float64,
        )
        radius_potential, _ = _expected_potential_stack_evaluation(
            expected_setup,
            radius_point,
            black_hole_mass,
            black_hole_softening_arcsec,
            dark_halo_profile_type,
            dark_halo_parameters,
        )
        return radius_potential[0]

    energy = potential_at_radius(target_radius)
    min_radius = 0.01 * request_radius
    max_radius = 1.1 * request_radius
    expected_radius = np.nan
    expected_iterations = -1
    for iteration in range(60001):
        expected_radius = 0.5 * (min_radius + max_radius)
        midpoint_potential = potential_at_radius(expected_radius)
        if abs((energy - midpoint_potential) / energy) < 1.0e-7:
            expected_iterations = iteration
            break
        if midpoint_potential > energy:
            min_radius = expected_radius
        else:
            max_radius = expected_radius
    assert expected_iterations > 0
    expected_record = np.array(
        [
            expected_radius * np.sin(start_theta) * np.cos(start_phi),
            expected_radius * np.sin(start_theta) * np.sin(start_phi),
            expected_radius * np.cos(start_theta),
            0.0,
            0.0,
            0.0,
            circular_radius,
            circular_period,
            circular_velocity,
        ],
        dtype=np.float64,
    )

    record = np.empty(9, dtype=np.float64)
    iterations = ctypes.c_int(-1)
    status = ctypes.c_int(-999)
    library = ctypes.CDLL(str(ORBLIB_CPP_SHARED_LIBRARY))
    double_p = ctypes.POINTER(ctypes.c_double)
    function = library.orblib_cpp_api_orbitstart_box_start_record
    function.argtypes = [
        ctypes.c_int,
        double_p,
        double_p,
        double_p,
        double_p,
        ctypes.c_double,
        ctypes.c_double,
        ctypes.c_double,
        ctypes.c_double,
        ctypes.c_double,
        ctypes.c_double,
        ctypes.c_double,
        ctypes.c_int,
        ctypes.c_int,
        double_p,
        ctypes.c_double,
        ctypes.c_double,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_double,
        ctypes.c_double,
        ctypes.c_double,
        double_p,
        ctypes.POINTER(ctypes.c_int),
        ctypes.POINTER(ctypes.c_int),
    ]
    function.restype = None
    function(
        ctypes.c_int(surf_pc.size),
        surf_pc.ctypes.data_as(double_p),
        sigobs_arcsec.ctypes.data_as(double_p),
        qobs.ctypes.data_as(double_p),
        psi_obs.ctypes.data_as(double_p),
        ctypes.c_double(distance),
        ctypes.c_double(theta),
        ctypes.c_double(phi),
        ctypes.c_double(psi),
        ctypes.c_double(upsilon),
        ctypes.c_double(black_hole_mass),
        ctypes.c_double(black_hole_softening_arcsec),
        ctypes.c_int(dark_halo_profile_type),
        ctypes.c_int(dark_halo_parameters.size),
        None,
        ctypes.c_double(request_radius),
        ctypes.c_double(energy),
        ctypes.c_int(i2_index),
        ctypes.c_int(i3_index),
        ctypes.c_int(i2_count),
        ctypes.c_int(i3_count),
        ctypes.c_double(circular_radius),
        ctypes.c_double(circular_period),
        ctypes.c_double(circular_velocity),
        record.ctypes.data_as(double_p),
        ctypes.byref(iterations),
        ctypes.byref(status),
    )

    assert status.value == 0
    assert iterations.value == expected_iterations
    np.testing.assert_allclose(record, expected_record, rtol=0.0, atol=2e-3)


@pytest.mark.orblib_cpp
def test_orblib_cpp_orbitstart_box_records_match_fortran_loop_order():
    surf_pc = np.array([0.0], dtype=np.float64)
    sigobs_arcsec = np.array([0.49416], dtype=np.float64)
    qobs = np.array([0.89541], dtype=np.float64)
    psi_obs = np.zeros_like(qobs)
    theta = 82.444308859
    psi = 90.021481540
    phi = 84.245110877
    distance = 39.9
    upsilon = 1.0
    black_hole_mass = 2.0e9
    black_hole_softening_arcsec = 0.02
    dark_halo_profile_type = 0
    dark_halo_parameters = np.ascontiguousarray([], dtype=np.float64)
    i2_count = 3
    i3_count = 2
    circular_radii = np.ascontiguousarray([1.0e13, 1.35e13], dtype=np.float64)
    circular_periods = np.ascontiguousarray([6.25e5, 7.5e5], dtype=np.float64)
    circular_velocities = np.ascontiguousarray([217.5, 246.0], dtype=np.float64)
    target_radii = np.ascontiguousarray([0.72e13, 0.93e13], dtype=np.float64)
    expected_setup = _expected_triaxial_mge_setup(
        surf_pc,
        sigobs_arcsec,
        qobs,
        psi_obs,
        distance,
        theta,
        phi,
        psi,
        upsilon,
    )

    def potential_at(radius_value, start_theta, start_phi):
        point = np.array(
            [
                [
                    radius_value * np.sin(start_theta) * np.cos(start_phi),
                    radius_value * np.sin(start_theta) * np.sin(start_phi),
                    radius_value * np.cos(start_theta),
                ],
            ],
            dtype=np.float64,
        )
        potential, _ = _expected_potential_stack_evaluation(
            expected_setup,
            point,
            black_hole_mass,
            black_hole_softening_arcsec,
            dark_halo_profile_type,
            dark_halo_parameters,
        )
        return potential[0]

    energies = np.ascontiguousarray(
        [
            potential_at(target_radii[0], 0.5 * np.pi / i2_count, 0.5 * np.pi / i3_count),
            potential_at(target_radii[1], 0.5 * np.pi / i2_count, 0.5 * np.pi / i3_count),
        ],
        dtype=np.float64,
    )
    energy_count = energies.size
    expected_records = np.empty((energy_count, i2_count, i3_count, 9), dtype=np.float64)
    expected_iterations = np.empty((energy_count, i2_count, i3_count), dtype=np.int32)
    for energy_index in range(energy_count):
        for i2_index in range(i2_count):
            for i3_index in range(i3_count):
                start_theta = 0.5 * np.pi * (i2_index + 0.5) / i2_count
                start_phi = 0.5 * np.pi * (i3_index + 0.5) / i3_count
                min_radius = 0.01 * circular_radii[energy_index]
                max_radius = 1.1 * circular_radii[energy_index]
                expected_radius = np.nan
                iteration_count = -1
                for iteration in range(60001):
                    expected_radius = 0.5 * (min_radius + max_radius)
                    midpoint_potential = potential_at(expected_radius, start_theta, start_phi)
                    if abs((energies[energy_index] - midpoint_potential) / energies[energy_index]) < 1.0e-7:
                        iteration_count = iteration
                        break
                    if midpoint_potential > energies[energy_index]:
                        min_radius = expected_radius
                    else:
                        max_radius = expected_radius
                assert iteration_count > 0
                expected_iterations[energy_index, i2_index, i3_index] = iteration_count
                expected_records[energy_index, i2_index, i3_index] = np.array(
                    [
                        expected_radius * np.sin(start_theta) * np.cos(start_phi),
                        expected_radius * np.sin(start_theta) * np.sin(start_phi),
                        expected_radius * np.cos(start_theta),
                        0.0,
                        0.0,
                        0.0,
                        circular_radii[energy_index],
                        circular_periods[energy_index],
                        circular_velocities[energy_index],
                    ],
                    dtype=np.float64,
                )

    records = np.empty_like(expected_records)
    noreg_flags = np.empty((energy_count, i2_count, i3_count), dtype=np.int32)
    iterations = np.empty_like(expected_iterations)
    status = ctypes.c_int(-999)
    library = ctypes.CDLL(str(ORBLIB_CPP_SHARED_LIBRARY))
    double_p = ctypes.POINTER(ctypes.c_double)
    int_p = ctypes.POINTER(ctypes.c_int)
    function = library.orblib_cpp_api_orbitstart_box_start_records
    function.argtypes = [
        ctypes.c_int,
        double_p,
        double_p,
        double_p,
        double_p,
        ctypes.c_double,
        ctypes.c_double,
        ctypes.c_double,
        ctypes.c_double,
        ctypes.c_double,
        ctypes.c_double,
        ctypes.c_double,
        ctypes.c_int,
        ctypes.c_int,
        double_p,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_int,
        double_p,
        double_p,
        double_p,
        double_p,
        double_p,
        int_p,
        int_p,
        ctypes.POINTER(ctypes.c_int),
    ]
    function.restype = None
    function(
        ctypes.c_int(surf_pc.size),
        surf_pc.ctypes.data_as(double_p),
        sigobs_arcsec.ctypes.data_as(double_p),
        qobs.ctypes.data_as(double_p),
        psi_obs.ctypes.data_as(double_p),
        ctypes.c_double(distance),
        ctypes.c_double(theta),
        ctypes.c_double(phi),
        ctypes.c_double(psi),
        ctypes.c_double(upsilon),
        ctypes.c_double(black_hole_mass),
        ctypes.c_double(black_hole_softening_arcsec),
        ctypes.c_int(dark_halo_profile_type),
        ctypes.c_int(dark_halo_parameters.size),
        None,
        ctypes.c_int(energy_count),
        ctypes.c_int(i2_count),
        ctypes.c_int(i3_count),
        energies.ctypes.data_as(double_p),
        circular_periods.ctypes.data_as(double_p),
        circular_radii.ctypes.data_as(double_p),
        circular_velocities.ctypes.data_as(double_p),
        records.ctypes.data_as(double_p),
        noreg_flags.ctypes.data_as(int_p),
        iterations.ctypes.data_as(int_p),
        ctypes.byref(status),
    )

    assert status.value == 0
    np.testing.assert_array_equal(noreg_flags, np.zeros_like(noreg_flags))
    np.testing.assert_array_equal(iterations, expected_iterations)
    np.testing.assert_allclose(records, expected_records, rtol=0.0, atol=2e-3)


@pytest.mark.orblib_cpp
def test_orblib_cpp_orbitstart_unregularized_grid_matches_fortran_loop_order():
    outer_boundaries = np.ascontiguousarray(
        [
            [10.0, 10.0, 10.0, 10.0],
            [20.0, 20.0, 20.0, 20.0],
            [30.0, 30.0, 30.0, 30.0],
        ],
        dtype=np.float64,
    )
    middle_boundaries = np.ascontiguousarray(
        [
            [10.0, 10.0, 9.99, 10.0],
            [19.0, 20.0, 19.0, 20.0],
            [30.0, 30.0, 30.0, 29.0],
        ],
        dtype=np.float64,
    )
    irregular = np.ascontiguousarray([0, 1, 0], dtype=np.int32)
    expected = np.zeros_like(middle_boundaries, dtype=np.int32)
    for energy_index in range(outer_boundaries.shape[0]):
        noreg = 0
        for i2_index in range(outer_boundaries.shape[1] - 1, -1, -1):
            if (
                abs(
                    middle_boundaries[energy_index, i2_index]
                    - outer_boundaries[energy_index, i2_index]
                )
                / outer_boundaries[energy_index, i2_index]
                > 1.0e-5
                and irregular[energy_index] == 0
            ):
                noreg = 1
            expected[energy_index, i2_index] = noreg

    actual = np.empty_like(expected)
    status = ctypes.c_int(-999)
    library = ctypes.CDLL(str(ORBLIB_CPP_SHARED_LIBRARY))
    double_p = ctypes.POINTER(ctypes.c_double)
    int_p = ctypes.POINTER(ctypes.c_int)
    function = library.orblib_cpp_api_orbitstart_unregularized_grid
    function.argtypes = [
        ctypes.c_int,
        ctypes.c_int,
        double_p,
        double_p,
        int_p,
        int_p,
        ctypes.POINTER(ctypes.c_int),
    ]
    function.restype = None
    function(
        ctypes.c_int(outer_boundaries.shape[0]),
        ctypes.c_int(outer_boundaries.shape[1]),
        outer_boundaries.ctypes.data_as(double_p),
        middle_boundaries.ctypes.data_as(double_p),
        irregular.ctypes.data_as(int_p),
        actual.ctypes.data_as(int_p),
        ctypes.byref(status),
    )

    assert status.value == 0
    np.testing.assert_array_equal(actual, expected)


@pytest.mark.orblib_cpp
def test_orblib_cpp_orbitstart_tube_schedule_matches_fortran_sampling_flags():
    inner_boundaries = np.ascontiguousarray(
        [[1.0, 2.0], [3.0, 4.0], [5.0, 6.0]],
        dtype=np.float64,
    )
    middle_boundaries = np.ascontiguousarray(
        [[11.0, 12.0], [13.0, 14.0], [15.0, 16.0]],
        dtype=np.float64,
    )
    outer_boundaries = np.ascontiguousarray(
        [[21.0, 22.0], [23.0, 24.0], [25.0, 26.0]],
        dtype=np.float64,
    )
    irregular = np.ascontiguousarray([0, 1, 0], dtype=np.int32)
    noreg_grid = np.ascontiguousarray(
        [[0, 1], [1, 0], [1, 1]],
        dtype=np.int32,
    )
    energy_count, i2_count = inner_boundaries.shape
    i3_count = 3
    expected_radii = np.empty((energy_count, i2_count, i3_count), dtype=np.float64)
    expected_flags = np.empty((energy_count, i2_count, i3_count), dtype=np.int32)
    max_irregular = int(np.max(irregular))
    for energy_index in range(energy_count):
        for i2_index in range(i2_count):
            inner = inner_boundaries[energy_index, i2_index]
            middle = middle_boundaries[energy_index, i2_index]
            if irregular[energy_index] == 1:
                inner = 0.0
                middle = outer_boundaries[energy_index, i2_index]
            for i3_index in range(i3_count):
                expected_radii[energy_index, i2_index, i3_index] = inner + (
                    middle - inner
                ) * (i3_index + 1.0 - 0.9) / (i3_count - 0.8)
                noreg = 0
                if i3_index == i3_count - 1 and noreg_grid[energy_index, i2_index] == 1:
                    noreg = 1
                if max_irregular == energy_index + 1:
                    noreg = 1
                expected_flags[energy_index, i2_index, i3_index] = noreg

    actual_radii = np.empty_like(expected_radii)
    actual_flags = np.empty_like(expected_flags)
    status = ctypes.c_int(-999)
    library = ctypes.CDLL(str(ORBLIB_CPP_SHARED_LIBRARY))
    double_p = ctypes.POINTER(ctypes.c_double)
    int_p = ctypes.POINTER(ctypes.c_int)
    function = library.orblib_cpp_api_orbitstart_tube_schedule
    function.argtypes = [
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_int,
        double_p,
        double_p,
        double_p,
        int_p,
        int_p,
        double_p,
        int_p,
        ctypes.POINTER(ctypes.c_int),
    ]
    function.restype = None
    function(
        ctypes.c_int(energy_count),
        ctypes.c_int(i2_count),
        ctypes.c_int(i3_count),
        inner_boundaries.ctypes.data_as(double_p),
        middle_boundaries.ctypes.data_as(double_p),
        outer_boundaries.ctypes.data_as(double_p),
        irregular.ctypes.data_as(int_p),
        noreg_grid.ctypes.data_as(int_p),
        actual_radii.ctypes.data_as(double_p),
        actual_flags.ctypes.data_as(int_p),
        ctypes.byref(status),
    )

    assert status.value == 0
    np.testing.assert_allclose(actual_radii, expected_radii, rtol=0.0, atol=1e-14)
    np.testing.assert_array_equal(actual_flags, expected_flags)


@pytest.mark.orblib_cpp
def test_orblib_cpp_orbitstart_tube_records_match_fortran_loop_and_retrograde():
    surf_pc = np.array([0.0], dtype=np.float64)
    sigobs_arcsec = np.array([0.49416], dtype=np.float64)
    qobs = np.array([0.89541], dtype=np.float64)
    psi_obs = np.zeros_like(qobs)
    theta = 82.444308859
    psi = 90.021481540
    phi = 84.245110877
    distance = 39.9
    upsilon = 1.0
    black_hole_mass = 2.0e9
    black_hole_softening_arcsec = 0.02
    dark_halo_profile_type = 0
    dark_halo_parameters = np.ascontiguousarray([], dtype=np.float64)
    inner_boundaries = np.ascontiguousarray(
        [[0.75e13, 0.9e13], [1.0e13, 1.15e13]],
        dtype=np.float64,
    )
    middle_boundaries = np.ascontiguousarray(
        [[1.15e13, 1.3e13], [1.4e13, 1.55e13]],
        dtype=np.float64,
    )
    outer_boundaries = np.ascontiguousarray(
        [[1.6e13, 1.8e13], [1.9e13, 2.1e13]],
        dtype=np.float64,
    )
    irregular = np.ascontiguousarray([0, 1], dtype=np.int32)
    noreg_grid = np.ascontiguousarray([[0, 1], [1, 0]], dtype=np.int32)
    theta_values = np.ascontiguousarray([0.42, 1.03], dtype=np.float64)
    energies = np.ascontiguousarray([20.0, 35.0], dtype=np.float64)
    circular_periods = np.ascontiguousarray([6.25e5, 7.5e5], dtype=np.float64)
    circular_radii = np.ascontiguousarray([1.25e13, 1.55e13], dtype=np.float64)
    circular_velocities = np.ascontiguousarray([217.5, 246.0], dtype=np.float64)
    energy_count, i2_count = inner_boundaries.shape
    i3_count = 3
    expected_setup = _expected_triaxial_mge_setup(
        surf_pc,
        sigobs_arcsec,
        qobs,
        psi_obs,
        distance,
        theta,
        phi,
        psi,
        upsilon,
    )
    expected_records = np.empty((energy_count, i2_count, i3_count, 9), dtype=np.float64)
    expected_flags = np.empty((energy_count, i2_count, i3_count), dtype=np.int32)
    max_irregular = int(np.max(irregular))
    for energy_index in range(energy_count):
        for i2_index in range(i2_count):
            inner = inner_boundaries[energy_index, i2_index]
            middle = middle_boundaries[energy_index, i2_index]
            if irregular[energy_index] == 1:
                inner = 0.0
                middle = outer_boundaries[energy_index, i2_index]
            for i3_index in range(i3_count):
                start_radius = inner + (middle - inner) * (
                    i3_index + 1.0 - 0.9
                ) / (i3_count - 0.8)
                start_theta = theta_values[i2_index]
                position = np.array(
                    [[start_radius * np.sin(start_theta), 0.0, start_radius * np.cos(start_theta)]],
                    dtype=np.float64,
                )
                potential, _ = _expected_potential_stack_evaluation(
                    expected_setup,
                    position,
                    black_hole_mass,
                    black_hole_softening_arcsec,
                    dark_halo_profile_type,
                    dark_halo_parameters,
                )
                vy = 2.0 * (potential[0] - energies[energy_index])
                if vy >= 1.0e-300:
                    vy = np.sqrt(vy)
                if vy < 0.0 or np.isnan(vy):
                    vy = np.sqrt(2.0 * potential[0] * 1.0e-12)
                expected_records[energy_index, i2_index, i3_index] = np.array(
                    [
                        position[0, 0],
                        0.0,
                        position[0, 2],
                        0.0,
                        vy,
                        0.0,
                        circular_radii[energy_index],
                        circular_periods[energy_index],
                        circular_velocities[energy_index],
                    ],
                    dtype=np.float64,
                )
                noreg = 0
                if i3_index == i3_count - 1 and noreg_grid[energy_index, i2_index] == 1:
                    noreg = 1
                if max_irregular == energy_index + 1:
                    noreg = 1
                expected_flags[energy_index, i2_index, i3_index] = noreg
    expected_retrograde = expected_records.copy()
    expected_retrograde[..., 4] *= -1.0

    records = np.empty_like(expected_records)
    flags = np.empty_like(expected_flags)
    retrograde_records = np.empty_like(expected_records)
    retrograde_flags = np.empty_like(expected_flags)
    status = ctypes.c_int(-999)
    library = ctypes.CDLL(str(ORBLIB_CPP_SHARED_LIBRARY))
    double_p = ctypes.POINTER(ctypes.c_double)
    int_p = ctypes.POINTER(ctypes.c_int)
    function = library.orblib_cpp_api_orbitstart_tube_start_records
    function.argtypes = [
        ctypes.c_int,
        double_p,
        double_p,
        double_p,
        double_p,
        ctypes.c_double,
        ctypes.c_double,
        ctypes.c_double,
        ctypes.c_double,
        ctypes.c_double,
        ctypes.c_double,
        ctypes.c_double,
        ctypes.c_int,
        ctypes.c_int,
        double_p,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_int,
        double_p,
        double_p,
        double_p,
        int_p,
        int_p,
        double_p,
        double_p,
        double_p,
        double_p,
        double_p,
        double_p,
        int_p,
        ctypes.c_int,
        double_p,
        int_p,
        ctypes.POINTER(ctypes.c_int),
    ]
    function.restype = None
    function(
        ctypes.c_int(surf_pc.size),
        surf_pc.ctypes.data_as(double_p),
        sigobs_arcsec.ctypes.data_as(double_p),
        qobs.ctypes.data_as(double_p),
        psi_obs.ctypes.data_as(double_p),
        ctypes.c_double(distance),
        ctypes.c_double(theta),
        ctypes.c_double(phi),
        ctypes.c_double(psi),
        ctypes.c_double(upsilon),
        ctypes.c_double(black_hole_mass),
        ctypes.c_double(black_hole_softening_arcsec),
        ctypes.c_int(dark_halo_profile_type),
        ctypes.c_int(dark_halo_parameters.size),
        None,
        ctypes.c_int(energy_count),
        ctypes.c_int(i2_count),
        ctypes.c_int(i3_count),
        inner_boundaries.ctypes.data_as(double_p),
        middle_boundaries.ctypes.data_as(double_p),
        outer_boundaries.ctypes.data_as(double_p),
        irregular.ctypes.data_as(int_p),
        noreg_grid.ctypes.data_as(int_p),
        theta_values.ctypes.data_as(double_p),
        energies.ctypes.data_as(double_p),
        circular_periods.ctypes.data_as(double_p),
        circular_radii.ctypes.data_as(double_p),
        circular_velocities.ctypes.data_as(double_p),
        records.ctypes.data_as(double_p),
        flags.ctypes.data_as(int_p),
        ctypes.c_int(1),
        retrograde_records.ctypes.data_as(double_p),
        retrograde_flags.ctypes.data_as(int_p),
        ctypes.byref(status),
    )

    assert status.value == 0
    np.testing.assert_allclose(records, expected_records, rtol=0.0, atol=2e-3)
    np.testing.assert_array_equal(flags, expected_flags)
    np.testing.assert_allclose(retrograde_records, expected_retrograde, rtol=0.0, atol=2e-3)
    np.testing.assert_array_equal(retrograde_flags, expected_flags)


@pytest.mark.orblib_cpp
def test_orblib_cpp_orbitstart_tube_orbit_width_matches_python_dop853_crossings():
    surf_pc = np.array([0.0], dtype=np.float64)
    sigobs_arcsec = np.array([0.49416], dtype=np.float64)
    qobs = np.array([0.89541], dtype=np.float64)
    psi_obs = np.zeros_like(qobs)
    theta = 82.444308859
    psi = 90.021481540
    phi = 84.245110877
    distance = 39.9
    upsilon = 1.0
    black_hole_mass = 2.0e9
    black_hole_softening_arcsec = 0.0
    dark_halo_profile_type = 0
    dark_halo_parameters = np.ascontiguousarray([], dtype=np.float64)
    n_radius = 4
    n_theta = 4
    n_phi = 4
    rlogmin = 18.0
    rlogmax = 19.0
    radius = 1.0e13
    start_theta = 0.73
    plane = 2
    integrator_accuracy = 1.0e-10
    crossing_capacity = 6
    expected_setup = _expected_triaxial_mge_setup(
        surf_pc,
        sigobs_arcsec,
        qobs,
        psi_obs,
        distance,
        theta,
        phi,
        psi,
        upsilon,
    )
    position = np.array(
        [[radius * np.sin(start_theta), 0.0, radius * np.cos(start_theta)]],
        dtype=np.float64,
    )
    potential, _ = _expected_potential_stack_evaluation(
        expected_setup,
        position,
        black_hole_mass,
        black_hole_softening_arcsec,
        dark_halo_profile_type,
        dark_halo_parameters,
    )
    energy = 0.45 * potential[0]
    initial_state = np.array(
        [
            position[0, 0],
            0.0,
            position[0, 2],
            0.0,
            np.sqrt(2.0 * (potential[0] - energy)),
            0.0,
        ],
        dtype=np.float64,
    )
    circular_velocity = np.sqrt(GRAV_CONST_KM * black_hole_mass / radius)
    circular_period = 2.0 * np.pi * radius / circular_velocity
    plane_index = plane - 1

    def rhs(_, state):
        pos = state[:3]
        softened_radius_squared = np.dot(pos, pos)
        acceleration = (
            -GRAV_CONST_KM
            * black_hole_mass
            * pos
            / (softened_radius_squared * np.sqrt(softened_radius_squared))
        )
        derivative = np.empty(6, dtype=np.float64)
        derivative[:3] = state[3:]
        derivative[3:] = acceleration
        return derivative

    solver = scipy.integrate.DOP853(
        rhs,
        0.0,
        initial_state,
        500.0 * crossing_capacity * circular_period,
        rtol=integrator_accuracy,
        atol=1.0e-8,
    )
    previous_plane_value = initial_state[plane_index]
    expected_positions = []
    for _ in range(100000):
        if solver.status != "running" or len(expected_positions) >= crossing_capacity:
            break
        x_old = solver.t
        solver.step()
        x = solver.t
        dense = solver.dense_output()
        current_plane_value = solver.y[plane_index]
        if current_plane_value * previous_plane_value < 0.0:
            if current_plane_value > 0.0:
                x_max = x
                x_min = x_old
            else:
                x_max = x_old
                x_min = x
            x_mid = 0.5 * (x_min + x_max)
            bisection_count = 0
            while True:
                x_mid = 0.5 * (x_min + x_max)
                y_mid = dense(x_mid)[plane_index]
                bisection_count += 1
                if abs(y_mid) < radius * 1.0e-4 or bisection_count > 40:
                    break
                if y_mid < 0.0:
                    x_min = x_mid
                else:
                    x_max = x_mid
            if bisection_count < 40:
                expected_positions.append(dense(x_mid)[:3])
        previous_plane_value = current_plane_value
    expected_positions = np.asarray(expected_positions, dtype=np.float64)
    assert expected_positions.shape == (crossing_capacity, 3)
    expected_projected = np.sqrt(expected_positions[:, 0] ** 2 + expected_positions[:, 2] ** 2)
    expected_width = np.max(expected_projected) - np.min(expected_projected)

    crossing_positions = np.empty((crossing_capacity, 3), dtype=np.float64)
    width = ctypes.c_double(np.nan)
    crossing_count = ctypes.c_int(-1)
    solver_status = ctypes.c_int(-1)
    function_evaluations = ctypes.c_int(-1)
    status = ctypes.c_int(-999)
    library = ctypes.CDLL(str(ORBLIB_CPP_SHARED_LIBRARY))
    double_p = ctypes.POINTER(ctypes.c_double)
    function = library.orblib_cpp_api_orbitstart_tube_orbit_width
    function.argtypes = [
        ctypes.c_int,
        double_p,
        double_p,
        double_p,
        double_p,
        ctypes.c_double,
        ctypes.c_double,
        ctypes.c_double,
        ctypes.c_double,
        ctypes.c_double,
        ctypes.c_double,
        ctypes.c_double,
        ctypes.c_int,
        ctypes.c_int,
        double_p,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_double,
        ctypes.c_double,
        ctypes.c_double,
        ctypes.c_double,
        ctypes.c_double,
        ctypes.c_double,
        ctypes.c_int,
        ctypes.c_double,
        ctypes.c_int,
        double_p,
        ctypes.POINTER(ctypes.c_double),
        ctypes.POINTER(ctypes.c_int),
        ctypes.POINTER(ctypes.c_int),
        ctypes.POINTER(ctypes.c_int),
        ctypes.POINTER(ctypes.c_int),
    ]
    function.restype = None
    function(
        ctypes.c_int(surf_pc.size),
        surf_pc.ctypes.data_as(double_p),
        sigobs_arcsec.ctypes.data_as(double_p),
        qobs.ctypes.data_as(double_p),
        psi_obs.ctypes.data_as(double_p),
        ctypes.c_double(distance),
        ctypes.c_double(theta),
        ctypes.c_double(phi),
        ctypes.c_double(psi),
        ctypes.c_double(upsilon),
        ctypes.c_double(black_hole_mass),
        ctypes.c_double(black_hole_softening_arcsec),
        ctypes.c_int(dark_halo_profile_type),
        ctypes.c_int(dark_halo_parameters.size),
        None,
        ctypes.c_int(n_radius),
        ctypes.c_int(n_theta),
        ctypes.c_int(n_phi),
        ctypes.c_double(rlogmin),
        ctypes.c_double(rlogmax),
        ctypes.c_double(radius),
        ctypes.c_double(start_theta),
        ctypes.c_double(energy),
        ctypes.c_double(circular_period),
        ctypes.c_int(plane),
        ctypes.c_double(integrator_accuracy),
        ctypes.c_int(crossing_capacity),
        crossing_positions.ctypes.data_as(double_p),
        ctypes.byref(width),
        ctypes.byref(crossing_count),
        ctypes.byref(solver_status),
        ctypes.byref(function_evaluations),
        ctypes.byref(status),
    )

    assert status.value == 0
    assert crossing_count.value == crossing_capacity
    assert solver_status.value == 2
    assert function_evaluations.value > 0
    np.testing.assert_allclose(crossing_positions[:, [0, 2]], expected_positions[:, [0, 2]], rtol=2e-5, atol=2e8)
    assert np.max(np.abs(crossing_positions[:, plane_index])) < radius * 2.0e-4
    assert width.value == pytest.approx(expected_width, rel=2e-5, abs=2e8)


@pytest.mark.orblib_cpp
def test_orblib_cpp_orbitstart_find_tube_radius_matches_fortran_golden_section():
    surf_pc = np.array([0.0], dtype=np.float64)
    sigobs_arcsec = np.array([0.49416], dtype=np.float64)
    qobs = np.array([0.89541], dtype=np.float64)
    psi_obs = np.zeros_like(qobs)
    theta = 82.444308859
    psi = 90.021481540
    phi = 84.245110877
    distance = 39.9
    upsilon = 1.0
    black_hole_mass = 2.0e9
    black_hole_softening_arcsec = 0.0
    dark_halo_profile_type = 0
    dark_halo_parameters = np.ascontiguousarray([], dtype=np.float64)
    n_radius = 4
    n_theta = 4
    n_phi = 4
    rlogmin = 18.0
    rlogmax = 19.0
    middle_radius = 1.0e13
    inner_radius = 0.975e13
    outer_radius = 1.025e13
    start_theta = 0.73
    plane = 2
    integrator_accuracy = 1.0e-10
    crossing_capacity = 6
    expected_setup = _expected_triaxial_mge_setup(
        surf_pc,
        sigobs_arcsec,
        qobs,
        psi_obs,
        distance,
        theta,
        phi,
        psi,
        upsilon,
    )
    position = np.array(
        [[middle_radius * np.sin(start_theta), 0.0, middle_radius * np.cos(start_theta)]],
        dtype=np.float64,
    )
    potential, _ = _expected_potential_stack_evaluation(
        expected_setup,
        position,
        black_hole_mass,
        black_hole_softening_arcsec,
        dark_halo_profile_type,
        dark_halo_parameters,
    )
    energy = 0.45 * potential[0]
    circular_velocity = np.sqrt(GRAV_CONST_KM * black_hole_mass / middle_radius)
    circular_period = 2.0 * np.pi * middle_radius / circular_velocity

    library = ctypes.CDLL(str(ORBLIB_CPP_SHARED_LIBRARY))
    double_p = ctypes.POINTER(ctypes.c_double)
    width_function = library.orblib_cpp_api_orbitstart_tube_orbit_width
    width_function.argtypes = [
        ctypes.c_int,
        double_p,
        double_p,
        double_p,
        double_p,
        ctypes.c_double,
        ctypes.c_double,
        ctypes.c_double,
        ctypes.c_double,
        ctypes.c_double,
        ctypes.c_double,
        ctypes.c_double,
        ctypes.c_int,
        ctypes.c_int,
        double_p,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_double,
        ctypes.c_double,
        ctypes.c_double,
        ctypes.c_double,
        ctypes.c_double,
        ctypes.c_double,
        ctypes.c_int,
        ctypes.c_double,
        ctypes.c_int,
        double_p,
        ctypes.POINTER(ctypes.c_double),
        ctypes.POINTER(ctypes.c_int),
        ctypes.POINTER(ctypes.c_int),
        ctypes.POINTER(ctypes.c_int),
        ctypes.POINTER(ctypes.c_int),
    ]
    width_function.restype = None

    def call_width(trial_radius):
        crossing_positions = np.empty((crossing_capacity, 3), dtype=np.float64)
        width = ctypes.c_double(np.nan)
        crossing_count = ctypes.c_int(-1)
        solver_status = ctypes.c_int(-1)
        function_evaluations = ctypes.c_int(-1)
        status = ctypes.c_int(-999)
        width_function(
            ctypes.c_int(surf_pc.size),
            surf_pc.ctypes.data_as(double_p),
            sigobs_arcsec.ctypes.data_as(double_p),
            qobs.ctypes.data_as(double_p),
            psi_obs.ctypes.data_as(double_p),
            ctypes.c_double(distance),
            ctypes.c_double(theta),
            ctypes.c_double(phi),
            ctypes.c_double(psi),
            ctypes.c_double(upsilon),
            ctypes.c_double(black_hole_mass),
            ctypes.c_double(black_hole_softening_arcsec),
            ctypes.c_int(dark_halo_profile_type),
            ctypes.c_int(dark_halo_parameters.size),
            None,
            ctypes.c_int(n_radius),
            ctypes.c_int(n_theta),
            ctypes.c_int(n_phi),
            ctypes.c_double(rlogmin),
            ctypes.c_double(rlogmax),
            ctypes.c_double(trial_radius),
            ctypes.c_double(start_theta),
            ctypes.c_double(energy),
            ctypes.c_double(circular_period),
            ctypes.c_int(plane),
            ctypes.c_double(integrator_accuracy),
            ctypes.c_int(crossing_capacity),
            crossing_positions.ctypes.data_as(double_p),
            ctypes.byref(width),
            ctypes.byref(crossing_count),
            ctypes.byref(solver_status),
            ctypes.byref(function_evaluations),
            ctypes.byref(status),
        )
        assert status.value == 0
        assert crossing_count.value == crossing_capacity
        assert solver_status.value == 2
        assert function_evaluations.value > 0
        return width.value

    golden = 0.61803399
    r0 = inner_radius
    r3 = outer_radius
    if abs(outer_radius - middle_radius) > abs(middle_radius - inner_radius):
        r1 = middle_radius
        r2 = middle_radius + (1.0 - golden) * (outer_radius - middle_radius)
    else:
        r2 = middle_radius
        r1 = middle_radius - (1.0 - golden) * (middle_radius - inner_radius)
    t1 = call_width(r1)
    t2 = call_width(r2)
    expected_evaluations = 2
    while abs(r3 - r0) >= 1.0e-4 * (abs(r1) + abs(r2)):
        if t2 < t1:
            r0 = r1
            r1 = r2
            r2 = golden * r1 + (1.0 - golden) * r3
            t1 = t2
            t2 = call_width(r2)
        else:
            r3 = r2
            r2 = r1
            r1 = golden * r2 + (1.0 - golden) * r0
            t2 = t1
            t1 = call_width(r1)
        expected_evaluations += 1
    if t1 < t2:
        expected_radius = r1
        expected_width = t1
    else:
        expected_radius = r2
        expected_width = t2

    radius = ctypes.c_double(np.nan)
    width = ctypes.c_double(np.nan)
    width_evaluations = ctypes.c_int(-1)
    crossing_count = ctypes.c_int(-1)
    solver_status = ctypes.c_int(-1)
    function_evaluations = ctypes.c_int(-1)
    status = ctypes.c_int(-999)
    function = library.orblib_cpp_api_orbitstart_find_tube_radius
    function.argtypes = [
        ctypes.c_int,
        double_p,
        double_p,
        double_p,
        double_p,
        ctypes.c_double,
        ctypes.c_double,
        ctypes.c_double,
        ctypes.c_double,
        ctypes.c_double,
        ctypes.c_double,
        ctypes.c_double,
        ctypes.c_int,
        ctypes.c_int,
        double_p,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_double,
        ctypes.c_double,
        ctypes.c_double,
        ctypes.c_double,
        ctypes.c_double,
        ctypes.c_double,
        ctypes.c_double,
        ctypes.c_double,
        ctypes.c_int,
        ctypes.c_double,
        ctypes.c_int,
        ctypes.POINTER(ctypes.c_double),
        ctypes.POINTER(ctypes.c_double),
        ctypes.POINTER(ctypes.c_int),
        ctypes.POINTER(ctypes.c_int),
        ctypes.POINTER(ctypes.c_int),
        ctypes.POINTER(ctypes.c_int),
        ctypes.POINTER(ctypes.c_int),
    ]
    function.restype = None
    function(
        ctypes.c_int(surf_pc.size),
        surf_pc.ctypes.data_as(double_p),
        sigobs_arcsec.ctypes.data_as(double_p),
        qobs.ctypes.data_as(double_p),
        psi_obs.ctypes.data_as(double_p),
        ctypes.c_double(distance),
        ctypes.c_double(theta),
        ctypes.c_double(phi),
        ctypes.c_double(psi),
        ctypes.c_double(upsilon),
        ctypes.c_double(black_hole_mass),
        ctypes.c_double(black_hole_softening_arcsec),
        ctypes.c_int(dark_halo_profile_type),
        ctypes.c_int(dark_halo_parameters.size),
        None,
        ctypes.c_int(n_radius),
        ctypes.c_int(n_theta),
        ctypes.c_int(n_phi),
        ctypes.c_double(rlogmin),
        ctypes.c_double(rlogmax),
        ctypes.c_double(inner_radius),
        ctypes.c_double(middle_radius),
        ctypes.c_double(outer_radius),
        ctypes.c_double(start_theta),
        ctypes.c_double(energy),
        ctypes.c_double(circular_period),
        ctypes.c_int(plane),
        ctypes.c_double(integrator_accuracy),
        ctypes.c_int(crossing_capacity),
        ctypes.byref(radius),
        ctypes.byref(width),
        ctypes.byref(width_evaluations),
        ctypes.byref(crossing_count),
        ctypes.byref(solver_status),
        ctypes.byref(function_evaluations),
        ctypes.byref(status),
    )

    assert status.value == 0
    assert width_evaluations.value == expected_evaluations
    assert crossing_count.value == crossing_capacity
    assert solver_status.value == 2
    assert function_evaluations.value > 0
    assert radius.value == pytest.approx(expected_radius, rel=1e-12, abs=1e-3)
    assert width.value == pytest.approx(expected_width, rel=1e-12, abs=1e3)


@pytest.mark.orblib_cpp
def test_orblib_cpp_orbitstart_find_type_matches_fortran_sampling_classifier():
    surf_pc = np.array([0.0], dtype=np.float64)
    sigobs_arcsec = np.array([0.49416], dtype=np.float64)
    qobs = np.array([0.89541], dtype=np.float64)
    psi_obs = np.zeros_like(qobs)
    theta = 82.444308859
    psi = 90.021481540
    phi = 84.245110877
    distance = 39.9
    upsilon = 1.0
    black_hole_mass = 2.0e9
    black_hole_softening_arcsec = 0.0
    dark_halo_profile_type = 0
    dark_halo_parameters = np.ascontiguousarray([], dtype=np.float64)
    n_radius = 4
    n_theta = 4
    n_phi = 4
    rlogmin = 18.0
    rlogmax = 19.0
    radius = 1.0e13
    start_theta = 0.73
    integrator_accuracy = 1.0e-10
    sample_count = 512
    expected_setup = _expected_triaxial_mge_setup(
        surf_pc,
        sigobs_arcsec,
        qobs,
        psi_obs,
        distance,
        theta,
        phi,
        psi,
        upsilon,
    )
    position = np.array(
        [[radius * np.sin(start_theta), 0.0, radius * np.cos(start_theta)]],
        dtype=np.float64,
    )
    potential, _ = _expected_potential_stack_evaluation(
        expected_setup,
        position,
        black_hole_mass,
        black_hole_softening_arcsec,
        dark_halo_profile_type,
        dark_halo_parameters,
    )
    energy = 0.45 * potential[0]
    initial_state = np.array(
        [
            position[0, 0],
            0.0,
            position[0, 2],
            0.0,
            np.sqrt(2.0 * (potential[0] - energy)),
            0.0,
        ],
        dtype=np.float64,
    )
    circular_velocity = np.sqrt(GRAV_CONST_KM * black_hole_mass / radius)
    circular_period = 2.0 * np.pi * radius / circular_velocity
    end_time = 100.0 * circular_period
    sample_step = end_time / (sample_count + 4.0)
    sample_times = sample_step * np.arange(1, sample_count + 1, dtype=np.float64)

    def rhs(_, state):
        position = state[:3]
        radius_squared = np.dot(position, position)
        acceleration = (
            -GRAV_CONST_KM
            * black_hole_mass
            * position
            / (radius_squared * np.sqrt(radius_squared))
        )
        derivative = np.empty(6, dtype=np.float64)
        derivative[:3] = state[3:]
        derivative[3:] = acceleration
        return derivative

    expected = scipy.integrate.solve_ivp(
        rhs,
        (0.0, end_time),
        initial_state,
        method="DOP853",
        rtol=integrator_accuracy,
        atol=1.0e-8,
        dense_output=True,
    )
    assert expected.success
    expected_samples = expected.sol(sample_times).T
    expected_type, _, _ = _expected_orbit_classification(expected_samples)

    orbit_type = ctypes.c_int(-1)
    samples_collected = ctypes.c_int(-1)
    solver_status = ctypes.c_int(-1)
    function_evaluations = ctypes.c_int(-1)
    status = ctypes.c_int(-999)
    library = ctypes.CDLL(str(ORBLIB_CPP_SHARED_LIBRARY))
    double_p = ctypes.POINTER(ctypes.c_double)
    function = library.orblib_cpp_api_orbitstart_find_type
    function.argtypes = [
        ctypes.c_int,
        double_p,
        double_p,
        double_p,
        double_p,
        ctypes.c_double,
        ctypes.c_double,
        ctypes.c_double,
        ctypes.c_double,
        ctypes.c_double,
        ctypes.c_double,
        ctypes.c_double,
        ctypes.c_int,
        ctypes.c_int,
        double_p,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_double,
        ctypes.c_double,
        ctypes.c_double,
        ctypes.c_double,
        ctypes.c_double,
        ctypes.c_double,
        ctypes.c_double,
        ctypes.c_int,
        ctypes.POINTER(ctypes.c_int),
        ctypes.POINTER(ctypes.c_int),
        ctypes.POINTER(ctypes.c_int),
        ctypes.POINTER(ctypes.c_int),
        ctypes.POINTER(ctypes.c_int),
    ]
    function.restype = None
    function(
        ctypes.c_int(surf_pc.size),
        surf_pc.ctypes.data_as(double_p),
        sigobs_arcsec.ctypes.data_as(double_p),
        qobs.ctypes.data_as(double_p),
        psi_obs.ctypes.data_as(double_p),
        ctypes.c_double(distance),
        ctypes.c_double(theta),
        ctypes.c_double(phi),
        ctypes.c_double(psi),
        ctypes.c_double(upsilon),
        ctypes.c_double(black_hole_mass),
        ctypes.c_double(black_hole_softening_arcsec),
        ctypes.c_int(dark_halo_profile_type),
        ctypes.c_int(dark_halo_parameters.size),
        None,
        ctypes.c_int(n_radius),
        ctypes.c_int(n_theta),
        ctypes.c_int(n_phi),
        ctypes.c_double(rlogmin),
        ctypes.c_double(rlogmax),
        ctypes.c_double(radius),
        ctypes.c_double(start_theta),
        ctypes.c_double(energy),
        ctypes.c_double(circular_period),
        ctypes.c_double(integrator_accuracy),
        ctypes.c_int(sample_count),
        ctypes.byref(orbit_type),
        ctypes.byref(samples_collected),
        ctypes.byref(solver_status),
        ctypes.byref(function_evaluations),
        ctypes.byref(status),
    )

    assert status.value == 0
    assert solver_status.value == 1
    assert samples_collected.value == sample_count
    assert function_evaluations.value > 0
    assert orbit_type.value == expected_type


@pytest.mark.orblib_cpp
def test_orblib_cpp_orbitstart_inner_boundaries_match_fortran_loop_order():
    surf_pc = np.array([0.0], dtype=np.float64)
    sigobs_arcsec = np.array([0.49416], dtype=np.float64)
    qobs = np.array([0.89541], dtype=np.float64)
    psi_obs = np.zeros_like(qobs)
    theta = 82.444308859
    psi = 90.021481540
    phi = 84.245110877
    distance = 39.9
    upsilon = 1.0
    black_hole_mass = 2.0e9
    black_hole_softening_arcsec = 0.0
    dark_halo_profile_type = 0
    dark_halo_parameters = np.ascontiguousarray([], dtype=np.float64)
    n_radius = 4
    n_theta = 4
    n_phi = 4
    rlogmin = 18.0
    rlogmax = 19.0
    theta_values = np.ascontiguousarray([0.35, 0.55, 0.73, 0.95], dtype=np.float64)
    outer_boundaries = np.ascontiguousarray(
        [[0.95e13, 1.0e13, 1.05e13, 1.10e13]],
        dtype=np.float64,
    )
    expected_setup = _expected_triaxial_mge_setup(
        surf_pc,
        sigobs_arcsec,
        qobs,
        psi_obs,
        distance,
        theta,
        phi,
        psi,
        upsilon,
    )
    reference_radius = 1.0e13
    reference_position = np.array(
        [[reference_radius * np.sin(theta_values[2]), 0.0, reference_radius * np.cos(theta_values[2])]],
        dtype=np.float64,
    )
    potential, _ = _expected_potential_stack_evaluation(
        expected_setup,
        reference_position,
        black_hole_mass,
        black_hole_softening_arcsec,
        dark_halo_profile_type,
        dark_halo_parameters,
    )
    energies = np.ascontiguousarray([0.45 * potential[0]], dtype=np.float64)
    circular_velocity = np.sqrt(GRAV_CONST_KM * black_hole_mass / reference_radius)
    circular_periods = np.ascontiguousarray(
        [2.0 * np.pi * reference_radius / circular_velocity],
        dtype=np.float64,
    )
    integrator_accuracy = 1.0e-7
    crossing_capacity = 2
    type_sample_count = 32

    library = ctypes.CDLL(str(ORBLIB_CPP_SHARED_LIBRARY))
    double_p = ctypes.POINTER(ctypes.c_double)
    tube_function = library.orblib_cpp_api_orbitstart_find_tube_radius
    tube_function.argtypes = [
        ctypes.c_int,
        double_p,
        double_p,
        double_p,
        double_p,
        ctypes.c_double,
        ctypes.c_double,
        ctypes.c_double,
        ctypes.c_double,
        ctypes.c_double,
        ctypes.c_double,
        ctypes.c_double,
        ctypes.c_int,
        ctypes.c_int,
        double_p,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_double,
        ctypes.c_double,
        ctypes.c_double,
        ctypes.c_double,
        ctypes.c_double,
        ctypes.c_double,
        ctypes.c_double,
        ctypes.c_double,
        ctypes.c_int,
        ctypes.c_double,
        ctypes.c_int,
        ctypes.POINTER(ctypes.c_double),
        ctypes.POINTER(ctypes.c_double),
        ctypes.POINTER(ctypes.c_int),
        ctypes.POINTER(ctypes.c_int),
        ctypes.POINTER(ctypes.c_int),
        ctypes.POINTER(ctypes.c_int),
        ctypes.POINTER(ctypes.c_int),
    ]
    tube_function.restype = None
    type_function = library.orblib_cpp_api_orbitstart_find_type
    type_function.argtypes = [
        ctypes.c_int,
        double_p,
        double_p,
        double_p,
        double_p,
        ctypes.c_double,
        ctypes.c_double,
        ctypes.c_double,
        ctypes.c_double,
        ctypes.c_double,
        ctypes.c_double,
        ctypes.c_double,
        ctypes.c_int,
        ctypes.c_int,
        double_p,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_double,
        ctypes.c_double,
        ctypes.c_double,
        ctypes.c_double,
        ctypes.c_double,
        ctypes.c_double,
        ctypes.c_double,
        ctypes.c_int,
        ctypes.POINTER(ctypes.c_int),
        ctypes.POINTER(ctypes.c_int),
        ctypes.POINTER(ctypes.c_int),
        ctypes.POINTER(ctypes.c_int),
        ctypes.POINTER(ctypes.c_int),
    ]
    type_function.restype = None

    def call_find_tube(inner_radius, middle_radius, outer_radius, start_theta):
        radius = ctypes.c_double(np.nan)
        width = ctypes.c_double(np.nan)
        width_evaluations = ctypes.c_int(-1)
        crossing_count = ctypes.c_int(-1)
        solver_status = ctypes.c_int(-1)
        function_evaluations = ctypes.c_int(-1)
        status = ctypes.c_int(-999)
        tube_function(
            ctypes.c_int(surf_pc.size),
            surf_pc.ctypes.data_as(double_p),
            sigobs_arcsec.ctypes.data_as(double_p),
            qobs.ctypes.data_as(double_p),
            psi_obs.ctypes.data_as(double_p),
            ctypes.c_double(distance),
            ctypes.c_double(theta),
            ctypes.c_double(phi),
            ctypes.c_double(psi),
            ctypes.c_double(upsilon),
            ctypes.c_double(black_hole_mass),
            ctypes.c_double(black_hole_softening_arcsec),
            ctypes.c_int(dark_halo_profile_type),
            ctypes.c_int(dark_halo_parameters.size),
            None,
            ctypes.c_int(n_radius),
            ctypes.c_int(n_theta),
            ctypes.c_int(n_phi),
            ctypes.c_double(rlogmin),
            ctypes.c_double(rlogmax),
            ctypes.c_double(inner_radius),
            ctypes.c_double(middle_radius),
            ctypes.c_double(outer_radius),
            ctypes.c_double(start_theta),
            ctypes.c_double(energies[0]),
            ctypes.c_double(circular_periods[0]),
            ctypes.c_int(2),
            ctypes.c_double(integrator_accuracy),
            ctypes.c_int(crossing_capacity),
            ctypes.byref(radius),
            ctypes.byref(width),
            ctypes.byref(width_evaluations),
            ctypes.byref(crossing_count),
            ctypes.byref(solver_status),
            ctypes.byref(function_evaluations),
            ctypes.byref(status),
        )
        assert status.value == 0
        assert crossing_count.value == crossing_capacity
        return radius.value, width_evaluations.value

    def call_find_type(radius, start_theta):
        orbit_type = ctypes.c_int(-1)
        samples_collected = ctypes.c_int(-1)
        solver_status = ctypes.c_int(-1)
        function_evaluations = ctypes.c_int(-1)
        status = ctypes.c_int(-999)
        type_function(
            ctypes.c_int(surf_pc.size),
            surf_pc.ctypes.data_as(double_p),
            sigobs_arcsec.ctypes.data_as(double_p),
            qobs.ctypes.data_as(double_p),
            psi_obs.ctypes.data_as(double_p),
            ctypes.c_double(distance),
            ctypes.c_double(theta),
            ctypes.c_double(phi),
            ctypes.c_double(psi),
            ctypes.c_double(upsilon),
            ctypes.c_double(black_hole_mass),
            ctypes.c_double(black_hole_softening_arcsec),
            ctypes.c_int(dark_halo_profile_type),
            ctypes.c_int(dark_halo_parameters.size),
            None,
            ctypes.c_int(n_radius),
            ctypes.c_int(n_theta),
            ctypes.c_int(n_phi),
            ctypes.c_double(rlogmin),
            ctypes.c_double(rlogmax),
            ctypes.c_double(radius),
            ctypes.c_double(start_theta),
            ctypes.c_double(energies[0]),
            ctypes.c_double(circular_periods[0]),
            ctypes.c_double(integrator_accuracy),
            ctypes.c_int(type_sample_count),
            ctypes.byref(orbit_type),
            ctypes.byref(samples_collected),
            ctypes.byref(solver_status),
            ctypes.byref(function_evaluations),
            ctypes.byref(status),
        )
        assert status.value == 0
        assert samples_collected.value == type_sample_count
        assert solver_status.value == 1
        return orbit_type.value, function_evaluations.value

    expected_inner = np.zeros_like(outer_boundaries)
    expected_types = np.full(outer_boundaries.shape, 5, dtype=np.int32)
    expected_irregular = np.zeros(outer_boundaries.shape[0], dtype=np.int32)
    expected_width_evaluations = 0
    expected_type_evaluations = 0
    for energy_index in range(outer_boundaries.shape[0]):
        found_x_tubes = 0
        i2_index = outer_boundaries.shape[1] - 1
        inner = outer_boundaries[energy_index, i2_index] * 0.11
        outer = outer_boundaries[energy_index, i2_index] * 0.89
        middle = outer_boundaries[energy_index, i2_index] * 0.50
        if energy_index > 0:
            middle = (
                expected_inner[energy_index - 1, i2_index]
                / outer_boundaries[energy_index - 1, i2_index]
                * outer_boundaries[energy_index, i2_index]
            )
        middle = max(min(middle, outer_boundaries[energy_index, i2_index] * 0.88), outer_boundaries[energy_index, i2_index] * 0.12)
        radius, evaluations = call_find_tube(inner, middle, outer, theta_values[i2_index])
        expected_inner[energy_index, i2_index] = radius
        expected_width_evaluations += evaluations
        orbit_type, evaluations = call_find_type(radius, theta_values[i2_index])
        expected_types[energy_index, i2_index] = orbit_type
        expected_type_evaluations += evaluations

        i2_index = outer_boundaries.shape[1] - 2
        middle = expected_inner[energy_index, i2_index + 1]
        middle = max(min(expected_inner[energy_index, i2_index + 1], outer_boundaries[energy_index, i2_index] * 0.99), outer_boundaries[energy_index, i2_index] * 0.02)
        inner = max(middle - outer_boundaries[energy_index, i2_index] * 0.10, outer_boundaries[energy_index, i2_index] * 0.01)
        outer = min(middle + outer_boundaries[energy_index, i2_index] * 0.10, outer_boundaries[energy_index, i2_index])
        radius, evaluations = call_find_tube(inner, middle, outer, theta_values[i2_index])
        expected_inner[energy_index, i2_index] = radius
        expected_width_evaluations += evaluations
        orbit_type, evaluations = call_find_type(radius, theta_values[i2_index])
        expected_types[energy_index, i2_index] = orbit_type
        expected_type_evaluations += evaluations

        for i2_index in range(outer_boundaries.shape[1] - 3, -1, -1):
            middle = expected_inner[energy_index, i2_index + 1]
            middle = min(max(middle, outer_boundaries[energy_index, i2_index] * 0.11), outer_boundaries[energy_index, i2_index] * 0.99)
            inner = max(
                middle - outer_boundaries[energy_index, -1] * 0.08,
                outer_boundaries[energy_index, i2_index] * 0.10,
            )
            outer = min(
                middle + outer_boundaries[energy_index, -1] * 0.08,
                outer_boundaries[energy_index, i2_index],
            )
            radius, evaluations = call_find_tube(inner, middle, outer, theta_values[i2_index])
            expected_inner[energy_index, i2_index] = radius
            expected_width_evaluations += evaluations
            if abs(radius - inner) < radius * 1.0e-2 or abs(radius - outer) < radius * 1.0e-2:
                expected_irregular[energy_index] = 1
            orbit_type, evaluations = call_find_type(radius, theta_values[i2_index])
            expected_types[energy_index, i2_index] = orbit_type
            expected_type_evaluations += evaluations
            if orbit_type == 1:
                found_x_tubes = 1
        if found_x_tubes == 0:
            expected_irregular[energy_index] = 1

    inner_boundaries = np.empty_like(outer_boundaries)
    irregular = np.empty(outer_boundaries.shape[0], dtype=np.int32)
    orbit_types = np.empty(outer_boundaries.shape, dtype=np.int32)
    width_evaluations = ctypes.c_int(-1)
    type_function_evaluations = ctypes.c_int(-1)
    status = ctypes.c_int(-999)
    function = library.orblib_cpp_api_orbitstart_inner_boundaries
    function.argtypes = [
        ctypes.c_int,
        double_p,
        double_p,
        double_p,
        double_p,
        ctypes.c_double,
        ctypes.c_double,
        ctypes.c_double,
        ctypes.c_double,
        ctypes.c_double,
        ctypes.c_double,
        ctypes.c_double,
        ctypes.c_int,
        ctypes.c_int,
        double_p,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_double,
        ctypes.c_double,
        ctypes.c_int,
        ctypes.c_int,
        double_p,
        double_p,
        double_p,
        double_p,
        ctypes.c_double,
        ctypes.c_int,
        ctypes.c_int,
        double_p,
        ctypes.POINTER(ctypes.c_int),
        ctypes.POINTER(ctypes.c_int),
        ctypes.POINTER(ctypes.c_int),
        ctypes.POINTER(ctypes.c_int),
        ctypes.POINTER(ctypes.c_int),
    ]
    function.restype = None
    function(
        ctypes.c_int(surf_pc.size),
        surf_pc.ctypes.data_as(double_p),
        sigobs_arcsec.ctypes.data_as(double_p),
        qobs.ctypes.data_as(double_p),
        psi_obs.ctypes.data_as(double_p),
        ctypes.c_double(distance),
        ctypes.c_double(theta),
        ctypes.c_double(phi),
        ctypes.c_double(psi),
        ctypes.c_double(upsilon),
        ctypes.c_double(black_hole_mass),
        ctypes.c_double(black_hole_softening_arcsec),
        ctypes.c_int(dark_halo_profile_type),
        ctypes.c_int(dark_halo_parameters.size),
        None,
        ctypes.c_int(n_radius),
        ctypes.c_int(n_theta),
        ctypes.c_int(n_phi),
        ctypes.c_double(rlogmin),
        ctypes.c_double(rlogmax),
        ctypes.c_int(outer_boundaries.shape[0]),
        ctypes.c_int(outer_boundaries.shape[1]),
        outer_boundaries.ctypes.data_as(double_p),
        energies.ctypes.data_as(double_p),
        circular_periods.ctypes.data_as(double_p),
        theta_values.ctypes.data_as(double_p),
        ctypes.c_double(integrator_accuracy),
        ctypes.c_int(crossing_capacity),
        ctypes.c_int(type_sample_count),
        inner_boundaries.ctypes.data_as(double_p),
        irregular.ctypes.data_as(ctypes.POINTER(ctypes.c_int)),
        orbit_types.ctypes.data_as(ctypes.POINTER(ctypes.c_int)),
        ctypes.byref(width_evaluations),
        ctypes.byref(type_function_evaluations),
        ctypes.byref(status),
    )

    assert status.value == 0
    np.testing.assert_allclose(inner_boundaries, expected_inner, rtol=1e-12, atol=1e-2)
    np.testing.assert_array_equal(irregular, expected_irregular)
    np.testing.assert_array_equal(orbit_types, expected_types)
    assert width_evaluations.value == expected_width_evaluations
    assert type_function_evaluations.value == expected_type_evaluations


@pytest.mark.orblib_cpp
def test_orblib_cpp_orbitstart_prepare_grid_matches_fortran_setup_order():
    surf_pc = np.array([0.0], dtype=np.float64)
    sigobs_arcsec = np.array([0.49416], dtype=np.float64)
    qobs = np.array([0.89541], dtype=np.float64)
    psi_obs = np.zeros_like(qobs)
    theta = 82.444308859
    psi = 90.021481540
    phi = 84.245110877
    distance = 39.9
    upsilon = 1.0
    black_hole_mass = 2.0e9
    black_hole_softening_arcsec = 0.0
    dark_halo_profile_type = 0
    dark_halo_parameters = np.ascontiguousarray([], dtype=np.float64)
    n_radius = 4
    n_theta = 4
    n_phi = 4
    rlogmin = 13.0
    rlogmax = 13.1
    energy_count = 2
    i2_count = 4
    integrator_accuracy = 1.0e-7
    crossing_capacity = 2
    type_sample_count = 16

    expected_radii = np.ascontiguousarray(
        10.0 ** (
            rlogmin
            + (rlogmax - rlogmin) * np.arange(energy_count, dtype=np.float64)
            / (energy_count - 1)
        ),
        dtype=np.float64,
    )
    expected_theta = np.ascontiguousarray(
        0.5 * np.pi * (np.arange(i2_count, dtype=np.float64) + 0.5) / i2_count,
        dtype=np.float64,
    )
    expected_energies = np.ascontiguousarray(
        GRAV_CONST_KM * black_hole_mass / expected_radii,
        dtype=np.float64,
    )
    initial_velocity = np.sqrt(2.0 * GRAV_CONST_KM * black_hole_mass / expected_radii)
    initial_periods = np.ascontiguousarray(
        2.0 * np.pi * expected_radii * 0.5 / initial_velocity,
        dtype=np.float64,
    )

    def find_req_black_hole(request_radius, energy):
        min_radius = 0.01 * request_radius
        max_radius = 1.1 * request_radius
        radius = np.nan
        for iteration in range(60001):
            radius = 0.5 * (min_radius + max_radius)
            potential = GRAV_CONST_KM * black_hole_mass / radius
            if abs((energy - potential) / energy) < 1.0e-7:
                return radius, iteration
            if potential > energy:
                min_radius = radius
            else:
                max_radius = radius
        raise AssertionError("findReq mirror did not converge")

    expected_outer = np.empty((energy_count, i2_count), dtype=np.float64)
    expected_equivalent_iterations = 0
    for energy_index in range(energy_count):
        for i2_index in range(i2_count):
            radius, iterations = find_req_black_hole(
                expected_radii[energy_index],
                expected_energies[energy_index],
            )
            expected_outer[energy_index, i2_index] = radius
            expected_equivalent_iterations += iterations
    expected_outer = np.ascontiguousarray(expected_outer)

    library = ctypes.CDLL(str(ORBLIB_CPP_SHARED_LIBRARY))
    double_p = ctypes.POINTER(ctypes.c_double)
    int_p = ctypes.POINTER(ctypes.c_int)

    inner_function = library.orblib_cpp_api_orbitstart_inner_boundaries
    inner_function.argtypes = [
        ctypes.c_int,
        double_p,
        double_p,
        double_p,
        double_p,
        ctypes.c_double,
        ctypes.c_double,
        ctypes.c_double,
        ctypes.c_double,
        ctypes.c_double,
        ctypes.c_double,
        ctypes.c_double,
        ctypes.c_int,
        ctypes.c_int,
        double_p,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_double,
        ctypes.c_double,
        ctypes.c_int,
        ctypes.c_int,
        double_p,
        double_p,
        double_p,
        double_p,
        ctypes.c_double,
        ctypes.c_int,
        ctypes.c_int,
        double_p,
        int_p,
        int_p,
        int_p,
        int_p,
        int_p,
    ]
    inner_function.restype = None
    expected_inner = np.empty_like(expected_outer)
    expected_irregular = np.empty(energy_count, dtype=np.int32)
    expected_types = np.empty_like(expected_outer, dtype=np.int32)
    expected_width_evaluations = ctypes.c_int(-1)
    expected_type_evaluations = ctypes.c_int(-1)
    status = ctypes.c_int(-999)
    inner_function(
        ctypes.c_int(surf_pc.size),
        surf_pc.ctypes.data_as(double_p),
        sigobs_arcsec.ctypes.data_as(double_p),
        qobs.ctypes.data_as(double_p),
        psi_obs.ctypes.data_as(double_p),
        ctypes.c_double(distance),
        ctypes.c_double(theta),
        ctypes.c_double(phi),
        ctypes.c_double(psi),
        ctypes.c_double(upsilon),
        ctypes.c_double(black_hole_mass),
        ctypes.c_double(black_hole_softening_arcsec),
        ctypes.c_int(dark_halo_profile_type),
        ctypes.c_int(dark_halo_parameters.size),
        None,
        ctypes.c_int(n_radius),
        ctypes.c_int(n_theta),
        ctypes.c_int(n_phi),
        ctypes.c_double(rlogmin),
        ctypes.c_double(rlogmax),
        ctypes.c_int(energy_count),
        ctypes.c_int(i2_count),
        expected_outer.ctypes.data_as(double_p),
        expected_energies.ctypes.data_as(double_p),
        initial_periods.ctypes.data_as(double_p),
        expected_theta.ctypes.data_as(double_p),
        ctypes.c_double(integrator_accuracy),
        ctypes.c_int(crossing_capacity),
        ctypes.c_int(type_sample_count),
        expected_inner.ctypes.data_as(double_p),
        expected_irregular.ctypes.data_as(int_p),
        expected_types.ctypes.data_as(int_p),
        ctypes.byref(expected_width_evaluations),
        ctypes.byref(expected_type_evaluations),
        ctypes.byref(status),
    )
    assert status.value == 0

    circular_radii = np.empty(energy_count, dtype=np.float64)
    circular_velocities = np.empty(energy_count, dtype=np.float64)
    circular_periods = np.empty(energy_count, dtype=np.float64)
    energies = np.empty(energy_count, dtype=np.float64)
    theta_values = np.empty(i2_count, dtype=np.float64)
    outer_boundaries = np.empty((energy_count, i2_count), dtype=np.float64)
    inner_boundaries = np.empty_like(outer_boundaries)
    irregular = np.empty(energy_count, dtype=np.int32)
    inner_orbit_types = np.empty_like(outer_boundaries, dtype=np.int32)
    equivalent_radius_iterations = ctypes.c_int(-1)
    inner_width_evaluations = ctypes.c_int(-1)
    inner_type_evaluations = ctypes.c_int(-1)
    status = ctypes.c_int(-999)
    function = library.orblib_cpp_api_orbitstart_prepare_grid
    function.argtypes = [
        ctypes.c_int,
        double_p,
        double_p,
        double_p,
        double_p,
        ctypes.c_double,
        ctypes.c_double,
        ctypes.c_double,
        ctypes.c_double,
        ctypes.c_double,
        ctypes.c_double,
        ctypes.c_double,
        ctypes.c_int,
        ctypes.c_int,
        double_p,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_double,
        ctypes.c_double,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_double,
        ctypes.c_int,
        ctypes.c_int,
        double_p,
        double_p,
        double_p,
        double_p,
        double_p,
        double_p,
        double_p,
        int_p,
        int_p,
        int_p,
        int_p,
        int_p,
        int_p,
    ]
    function.restype = None
    function(
        ctypes.c_int(surf_pc.size),
        surf_pc.ctypes.data_as(double_p),
        sigobs_arcsec.ctypes.data_as(double_p),
        qobs.ctypes.data_as(double_p),
        psi_obs.ctypes.data_as(double_p),
        ctypes.c_double(distance),
        ctypes.c_double(theta),
        ctypes.c_double(phi),
        ctypes.c_double(psi),
        ctypes.c_double(upsilon),
        ctypes.c_double(black_hole_mass),
        ctypes.c_double(black_hole_softening_arcsec),
        ctypes.c_int(dark_halo_profile_type),
        ctypes.c_int(dark_halo_parameters.size),
        None,
        ctypes.c_int(n_radius),
        ctypes.c_int(n_theta),
        ctypes.c_int(n_phi),
        ctypes.c_double(rlogmin),
        ctypes.c_double(rlogmax),
        ctypes.c_int(energy_count),
        ctypes.c_int(i2_count),
        ctypes.c_double(integrator_accuracy),
        ctypes.c_int(crossing_capacity),
        ctypes.c_int(type_sample_count),
        circular_radii.ctypes.data_as(double_p),
        circular_velocities.ctypes.data_as(double_p),
        circular_periods.ctypes.data_as(double_p),
        energies.ctypes.data_as(double_p),
        theta_values.ctypes.data_as(double_p),
        outer_boundaries.ctypes.data_as(double_p),
        inner_boundaries.ctypes.data_as(double_p),
        irregular.ctypes.data_as(int_p),
        inner_orbit_types.ctypes.data_as(int_p),
        ctypes.byref(equivalent_radius_iterations),
        ctypes.byref(inner_width_evaluations),
        ctypes.byref(inner_type_evaluations),
        ctypes.byref(status),
    )

    short_axis_inner = expected_inner[:, -1]
    expected_final_velocities = np.sqrt(GRAV_CONST_KM * black_hole_mass / short_axis_inner)
    expected_final_periods = 2.0 * np.pi * short_axis_inner / expected_final_velocities
    assert status.value == 0
    np.testing.assert_allclose(circular_radii, expected_radii, rtol=1e-15, atol=1e-2)
    np.testing.assert_allclose(energies, expected_energies, rtol=1e-15, atol=1e-12)
    np.testing.assert_allclose(theta_values, expected_theta, rtol=0.0, atol=1e-15)
    np.testing.assert_allclose(outer_boundaries, expected_outer, rtol=0.0, atol=1e-3)
    np.testing.assert_allclose(inner_boundaries, expected_inner, rtol=1e-12, atol=1e-2)
    np.testing.assert_array_equal(irregular, expected_irregular)
    np.testing.assert_array_equal(inner_orbit_types, expected_types)
    np.testing.assert_allclose(circular_velocities, expected_final_velocities, rtol=1e-10, atol=1e-8)
    np.testing.assert_allclose(circular_periods, expected_final_periods, rtol=1e-10, atol=1e-3)
    assert equivalent_radius_iterations.value == expected_equivalent_iterations
    assert inner_width_evaluations.value == expected_width_evaluations.value
    assert inner_type_evaluations.value == expected_type_evaluations.value


@pytest.mark.orblib_cpp
def test_orblib_cpp_orbitstart_builds_start_arrays_like_runorbitstart():
    surf_pc = np.array([0.0], dtype=np.float64)
    sigobs_arcsec = np.array([0.49416], dtype=np.float64)
    qobs = np.array([0.89541], dtype=np.float64)
    psi_obs = np.zeros_like(qobs)
    theta = 82.444308859
    psi = 90.021481540
    phi = 84.245110877
    distance = 39.9
    upsilon = 1.0
    black_hole_mass = 2.0e9
    black_hole_softening_arcsec = 0.0
    dark_halo_profile_type = 0
    dark_halo_parameters = np.ascontiguousarray([], dtype=np.float64)
    n_radius = 4
    n_theta = 4
    n_phi = 4
    rlogmin = 13.0
    rlogmax = 13.1
    energy_count = 2
    i2_count = 4
    i3_count = 2
    orbit_dithering = 2
    omega = 1.25
    integrator_accuracy = 1.0e-7
    crossing_capacity = 2
    type_sample_count = 16

    total_records = energy_count * i2_count * i3_count
    circular_radii = np.empty(energy_count, dtype=np.float64)
    circular_velocities = np.empty(energy_count, dtype=np.float64)
    circular_periods = np.empty(energy_count, dtype=np.float64)
    energies = np.empty(energy_count, dtype=np.float64)
    theta_values = np.empty(i2_count, dtype=np.float64)
    inner_boundaries = np.empty((energy_count, i2_count), dtype=np.float64)
    middle_boundaries = np.empty_like(inner_boundaries)
    outer_boundaries = np.empty_like(inner_boundaries)
    irregular = np.empty(energy_count, dtype=np.int32)
    inner_orbit_types = np.empty_like(inner_boundaries, dtype=np.int32)
    middle_orbit_types = np.empty_like(inner_boundaries, dtype=np.int32)
    noreg_grid = np.empty_like(inner_boundaries, dtype=np.int32)
    begin_records = np.empty((energy_count, i2_count, i3_count, 9), dtype=np.float64)
    begin_noreg = np.empty((energy_count, i2_count, i3_count), dtype=np.int32)
    beginbox_records = np.empty_like(begin_records)
    beginbox_noreg = np.empty_like(begin_noreg)
    box_iterations = np.empty_like(begin_noreg)
    used_triaxial_branch = ctypes.c_int(-1)
    rounded_irregular_energy_count = ctypes.c_int(-1)
    equivalent_radius_iterations = ctypes.c_int(-1)
    inner_width_evaluations = ctypes.c_int(-1)
    inner_type_evaluations = ctypes.c_int(-1)
    outer_width_evaluations = ctypes.c_int(-1)
    outer_type_evaluations = ctypes.c_int(-1)
    box_equivalent_radius_iterations = ctypes.c_int(-1)
    begin_record_count = ctypes.c_int(-1)
    beginbox_record_count = ctypes.c_int(-1)
    status = ctypes.c_int(-999)

    library = ctypes.CDLL(str(ORBLIB_CPP_SHARED_LIBRARY))
    double_p = ctypes.POINTER(ctypes.c_double)
    int_p = ctypes.POINTER(ctypes.c_int)
    function = library.orblib_cpp_api_orbitstart_build_start_arrays
    function.argtypes = [
        ctypes.c_int,
        double_p,
        double_p,
        double_p,
        double_p,
        ctypes.c_double,
        ctypes.c_double,
        ctypes.c_double,
        ctypes.c_double,
        ctypes.c_double,
        ctypes.c_double,
        ctypes.c_double,
        ctypes.c_int,
        ctypes.c_int,
        double_p,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_double,
        ctypes.c_double,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_double,
        ctypes.c_double,
        ctypes.c_int,
        ctypes.c_int,
        double_p,
        double_p,
        double_p,
        double_p,
        double_p,
        double_p,
        double_p,
        double_p,
        int_p,
        int_p,
        int_p,
        int_p,
        double_p,
        int_p,
        double_p,
        int_p,
        int_p,
        int_p,
        int_p,
        int_p,
        int_p,
        int_p,
        int_p,
        int_p,
        int_p,
        int_p,
        int_p,
        int_p,
    ]
    function.restype = None
    function(
        ctypes.c_int(surf_pc.size),
        surf_pc.ctypes.data_as(double_p),
        sigobs_arcsec.ctypes.data_as(double_p),
        qobs.ctypes.data_as(double_p),
        psi_obs.ctypes.data_as(double_p),
        ctypes.c_double(distance),
        ctypes.c_double(theta),
        ctypes.c_double(phi),
        ctypes.c_double(psi),
        ctypes.c_double(upsilon),
        ctypes.c_double(black_hole_mass),
        ctypes.c_double(black_hole_softening_arcsec),
        ctypes.c_int(dark_halo_profile_type),
        ctypes.c_int(dark_halo_parameters.size),
        None,
        ctypes.c_int(n_radius),
        ctypes.c_int(n_theta),
        ctypes.c_int(n_phi),
        ctypes.c_double(rlogmin),
        ctypes.c_double(rlogmax),
        ctypes.c_int(energy_count),
        ctypes.c_int(i2_count),
        ctypes.c_int(i3_count),
        ctypes.c_int(orbit_dithering),
        ctypes.c_double(omega),
        ctypes.c_double(integrator_accuracy),
        ctypes.c_int(crossing_capacity),
        ctypes.c_int(type_sample_count),
        circular_radii.ctypes.data_as(double_p),
        circular_velocities.ctypes.data_as(double_p),
        circular_periods.ctypes.data_as(double_p),
        energies.ctypes.data_as(double_p),
        theta_values.ctypes.data_as(double_p),
        inner_boundaries.ctypes.data_as(double_p),
        middle_boundaries.ctypes.data_as(double_p),
        outer_boundaries.ctypes.data_as(double_p),
        irregular.ctypes.data_as(int_p),
        inner_orbit_types.ctypes.data_as(int_p),
        middle_orbit_types.ctypes.data_as(int_p),
        noreg_grid.ctypes.data_as(int_p),
        begin_records.ctypes.data_as(double_p),
        begin_noreg.ctypes.data_as(int_p),
        beginbox_records.ctypes.data_as(double_p),
        beginbox_noreg.ctypes.data_as(int_p),
        box_iterations.ctypes.data_as(int_p),
        ctypes.byref(used_triaxial_branch),
        ctypes.byref(rounded_irregular_energy_count),
        ctypes.byref(equivalent_radius_iterations),
        ctypes.byref(inner_width_evaluations),
        ctypes.byref(inner_type_evaluations),
        ctypes.byref(outer_width_evaluations),
        ctypes.byref(outer_type_evaluations),
        ctypes.byref(box_equivalent_radius_iterations),
        ctypes.byref(begin_record_count),
        ctypes.byref(beginbox_record_count),
        ctypes.byref(status),
    )

    assert status.value == 0
    assert used_triaxial_branch.value == 1
    assert begin_record_count.value == total_records
    assert beginbox_record_count.value == total_records
    assert equivalent_radius_iterations.value > 0
    assert inner_width_evaluations.value > 0
    assert inner_type_evaluations.value > 0
    assert outer_type_evaluations.value > 0
    assert box_equivalent_radius_iterations.value == 0
    np.testing.assert_array_equal(box_iterations, np.zeros_like(box_iterations))

    last_irregular = 0
    for energy_index, flag in enumerate(irregular, start=1):
        if flag == 1:
            last_irregular = energy_index
    expected_rounded = int(
        np.floor((last_irregular - 1.0 + orbit_dithering) / orbit_dithering)
        * orbit_dithering
    )
    expected_rounded = max(0, min(expected_rounded, energy_count))
    assert rounded_irregular_energy_count.value == expected_rounded
    if expected_rounded > 0:
        np.testing.assert_array_equal(irregular[:expected_rounded], np.ones(expected_rounded, dtype=np.int32))

    expected_noreg_grid = np.zeros_like(noreg_grid)
    for energy_index in range(energy_count):
        noreg = 0
        for i2_index in range(i2_count - 1, -1, -1):
            if (
                abs(
                    middle_boundaries[energy_index, i2_index]
                    - outer_boundaries[energy_index, i2_index]
                )
                / outer_boundaries[energy_index, i2_index]
                > 1.0e-5
                and irregular[energy_index] == 0
            ):
                noreg = 1
            expected_noreg_grid[energy_index, i2_index] = noreg
    np.testing.assert_array_equal(noreg_grid, expected_noreg_grid)

    expected_setup = _expected_triaxial_mge_setup(
        surf_pc,
        sigobs_arcsec,
        qobs,
        psi_obs,
        distance,
        theta,
        phi,
        psi,
        upsilon,
    )
    expected_records = np.empty_like(begin_records)
    expected_flags = np.empty_like(begin_noreg)
    max_irregular = int(np.max(irregular))
    for energy_index in range(energy_count):
        for i2_index in range(i2_count):
            inner = inner_boundaries[energy_index, i2_index]
            middle = middle_boundaries[energy_index, i2_index]
            if irregular[energy_index] == 1:
                inner = 0.0
                middle = outer_boundaries[energy_index, i2_index]
            for i3_index in range(i3_count):
                start_radius = inner + (middle - inner) * (
                    i3_index + 1.0 - 0.9
                ) / (i3_count - 0.8)
                start_theta = theta_values[i2_index]
                position = np.array(
                    [[start_radius * np.sin(start_theta), 0.0, start_radius * np.cos(start_theta)]],
                    dtype=np.float64,
                )
                potential, _ = _expected_potential_stack_evaluation(
                    expected_setup,
                    position,
                    black_hole_mass,
                    black_hole_softening_arcsec,
                    dark_halo_profile_type,
                    dark_halo_parameters,
                )
                vy = 2.0 * (potential[0] - energies[energy_index])
                if vy >= 1.0e-300:
                    vy = np.sqrt(vy)
                if vy < 0.0 or np.isnan(vy):
                    vy = np.sqrt(2.0 * potential[0] * 1.0e-12)
                expected_records[energy_index, i2_index, i3_index] = np.array(
                    [
                        position[0, 0],
                        0.0,
                        position[0, 2],
                        0.0,
                        vy,
                        0.0,
                        circular_radii[energy_index],
                        circular_periods[energy_index],
                        circular_velocities[energy_index],
                    ],
                    dtype=np.float64,
                )
                noreg = 0
                if i3_index == i3_count - 1 and noreg_grid[energy_index, i2_index] == 1:
                    noreg = 1
                if max_irregular == energy_index + 1:
                    noreg = 1
                expected_flags[energy_index, i2_index, i3_index] = noreg

    expected_beginbox = expected_records.copy()
    expected_beginbox[..., 4] *= -1.0
    np.testing.assert_allclose(begin_records, expected_records, rtol=0.0, atol=2e-3)
    np.testing.assert_array_equal(begin_noreg, expected_flags)
    np.testing.assert_allclose(beginbox_records, expected_beginbox, rtol=0.0, atol=2e-3)
    np.testing.assert_array_equal(beginbox_noreg, expected_flags)


@pytest.mark.orblib_cpp
@pytest.mark.orblib_fortran
def test_orblib_cpp_orbitstart_start_arrays_match_active_fortran_memory_api(
    monkeypatch,
    tmp_path,
):
    assert ORBLIB_CPP_SHARED_LIBRARY.is_file()
    assert ORBLIB_FORTRAN_SHARED_LIBRARY.is_file()
    monkeypatch.chdir(tmp_path)

    surf_pc = np.array([0.0], dtype=np.float64)
    sigobs_arcsec = np.array([0.49416], dtype=np.float64)
    qobs = np.array([0.89541], dtype=np.float64)
    psi_obs = np.zeros_like(qobs)
    theta = 82.444308859
    psi = 90.021481540
    phi = 84.245110877
    distance = 39.9
    upsilon = 1.0
    black_hole_mass = 2.0e9
    black_hole_softening_arcsec = 0.0
    dark_halo_profile_type = 0
    dark_halo_parameters = np.ascontiguousarray([], dtype=np.float64)
    n_radius = 4
    n_theta = 4
    n_phi = 4
    rlogmin_km = 13.0
    rlogmax_km = 13.1
    energy_count = 2
    i2_count = 4
    i3_count = 1
    orbit_dithering = 1
    omega = 0.0
    integrator_accuracy = 1.0e-4
    crossing_capacity = 400
    type_sample_count = 5000
    total_records = energy_count * i2_count * i3_count

    conversion_factor = (
        distance * 1.0e6 * np.tan(np.pi / 648e3) * PARSEC_KM
    )
    rlogmin_arcsec = rlogmin_km - np.log10(conversion_factor)
    rlogmax_arcsec = rlogmax_km - np.log10(conversion_factor)

    double_p = ctypes.POINTER(ctypes.c_double)
    int_p = ctypes.POINTER(ctypes.c_int)

    max_rows = total_records
    fortran_begin = np.empty(max_rows * 9, dtype=np.float64)
    fortran_beginbox = np.empty(max_rows * 9, dtype=np.float64)
    fortran_begin_noreg = np.empty(max_rows, dtype=np.int32)
    fortran_beginbox_noreg = np.empty(max_rows, dtype=np.int32)
    fortran_rows = ctypes.c_int(-1)
    fortran_box_rows = ctypes.c_int(-1)
    fortran_status = ctypes.c_int(-999)

    fortran_library = ctypes.CDLL(str(ORBLIB_FORTRAN_SHARED_LIBRARY))
    fortran_function = fortran_library.orblib_api_run_orbitstart_memory
    fortran_function.argtypes = [
        ctypes.c_int,
        ctypes.c_int,
        double_p,
        double_p,
        double_p,
        double_p,
        ctypes.c_double,
        ctypes.c_double,
        ctypes.c_double,
        ctypes.c_double,
        ctypes.c_double,
        ctypes.c_double,
        ctypes.c_double,
        ctypes.c_int,
        ctypes.c_double,
        ctypes.c_double,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_int,
        double_p,
        ctypes.c_int,
        double_p,
        int_p,
        double_p,
        int_p,
        int_p,
        int_p,
        int_p,
    ]
    fortran_function.restype = None
    fortran_function(
        ctypes.c_int(123),
        ctypes.c_int(surf_pc.size),
        surf_pc.ctypes.data_as(double_p),
        sigobs_arcsec.ctypes.data_as(double_p),
        qobs.ctypes.data_as(double_p),
        psi_obs.ctypes.data_as(double_p),
        ctypes.c_double(distance),
        ctypes.c_double(theta),
        ctypes.c_double(phi),
        ctypes.c_double(psi),
        ctypes.c_double(upsilon),
        ctypes.c_double(black_hole_mass),
        ctypes.c_double(black_hole_softening_arcsec),
        ctypes.c_int(energy_count),
        ctypes.c_double(rlogmin_arcsec),
        ctypes.c_double(rlogmax_arcsec),
        ctypes.c_int(i2_count),
        ctypes.c_int(i3_count),
        ctypes.c_int(orbit_dithering),
        ctypes.c_int(n_radius),
        ctypes.c_int(n_theta),
        ctypes.c_int(n_phi),
        ctypes.c_int(dark_halo_profile_type),
        ctypes.c_int(dark_halo_parameters.size),
        None,
        ctypes.c_int(max_rows),
        fortran_begin.ctypes.data_as(double_p),
        fortran_begin_noreg.ctypes.data_as(int_p),
        fortran_beginbox.ctypes.data_as(double_p),
        fortran_beginbox_noreg.ctypes.data_as(int_p),
        ctypes.byref(fortran_rows),
        ctypes.byref(fortran_box_rows),
        ctypes.byref(fortran_status),
    )
    assert fortran_status.value == 0
    assert fortran_rows.value == total_records
    assert fortran_box_rows.value == total_records

    circular_radii = np.empty(energy_count, dtype=np.float64)
    circular_velocities = np.empty(energy_count, dtype=np.float64)
    circular_periods = np.empty(energy_count, dtype=np.float64)
    energies = np.empty(energy_count, dtype=np.float64)
    theta_values = np.empty(i2_count, dtype=np.float64)
    inner_boundaries = np.empty((energy_count, i2_count), dtype=np.float64)
    middle_boundaries = np.empty_like(inner_boundaries)
    outer_boundaries = np.empty_like(inner_boundaries)
    irregular = np.empty(energy_count, dtype=np.int32)
    inner_orbit_types = np.empty_like(inner_boundaries, dtype=np.int32)
    middle_orbit_types = np.empty_like(inner_boundaries, dtype=np.int32)
    noreg_grid = np.empty_like(inner_boundaries, dtype=np.int32)
    cpp_begin = np.empty((total_records, 9), dtype=np.float64)
    cpp_begin_noreg = np.empty(total_records, dtype=np.int32)
    cpp_beginbox = np.empty_like(cpp_begin)
    cpp_beginbox_noreg = np.empty_like(cpp_begin_noreg)
    box_iterations = np.empty(total_records, dtype=np.int32)
    used_triaxial_branch = ctypes.c_int(-1)
    rounded_irregular_energy_count = ctypes.c_int(-1)
    equivalent_radius_iterations = ctypes.c_int(-1)
    inner_width_evaluations = ctypes.c_int(-1)
    inner_type_evaluations = ctypes.c_int(-1)
    outer_width_evaluations = ctypes.c_int(-1)
    outer_type_evaluations = ctypes.c_int(-1)
    box_equivalent_radius_iterations = ctypes.c_int(-1)
    cpp_rows = ctypes.c_int(-1)
    cpp_box_rows = ctypes.c_int(-1)
    cpp_status = ctypes.c_int(-999)

    cpp_library = ctypes.CDLL(str(ORBLIB_CPP_SHARED_LIBRARY))
    cpp_function = cpp_library.orblib_cpp_api_orbitstart_build_start_arrays
    cpp_function.argtypes = [
        ctypes.c_int,
        double_p,
        double_p,
        double_p,
        double_p,
        ctypes.c_double,
        ctypes.c_double,
        ctypes.c_double,
        ctypes.c_double,
        ctypes.c_double,
        ctypes.c_double,
        ctypes.c_double,
        ctypes.c_int,
        ctypes.c_int,
        double_p,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_double,
        ctypes.c_double,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_double,
        ctypes.c_double,
        ctypes.c_int,
        ctypes.c_int,
        double_p,
        double_p,
        double_p,
        double_p,
        double_p,
        double_p,
        double_p,
        double_p,
        int_p,
        int_p,
        int_p,
        int_p,
        double_p,
        int_p,
        double_p,
        int_p,
        int_p,
        int_p,
        int_p,
        int_p,
        int_p,
        int_p,
        int_p,
        int_p,
        int_p,
        int_p,
        int_p,
        int_p,
    ]
    cpp_function.restype = None
    cpp_function(
        ctypes.c_int(surf_pc.size),
        surf_pc.ctypes.data_as(double_p),
        sigobs_arcsec.ctypes.data_as(double_p),
        qobs.ctypes.data_as(double_p),
        psi_obs.ctypes.data_as(double_p),
        ctypes.c_double(distance),
        ctypes.c_double(theta),
        ctypes.c_double(phi),
        ctypes.c_double(psi),
        ctypes.c_double(upsilon),
        ctypes.c_double(black_hole_mass),
        ctypes.c_double(black_hole_softening_arcsec),
        ctypes.c_int(dark_halo_profile_type),
        ctypes.c_int(dark_halo_parameters.size),
        None,
        ctypes.c_int(n_radius),
        ctypes.c_int(n_theta),
        ctypes.c_int(n_phi),
        ctypes.c_double(rlogmin_km),
        ctypes.c_double(rlogmax_km),
        ctypes.c_int(energy_count),
        ctypes.c_int(i2_count),
        ctypes.c_int(i3_count),
        ctypes.c_int(orbit_dithering),
        ctypes.c_double(omega),
        ctypes.c_double(integrator_accuracy),
        ctypes.c_int(crossing_capacity),
        ctypes.c_int(type_sample_count),
        circular_radii.ctypes.data_as(double_p),
        circular_velocities.ctypes.data_as(double_p),
        circular_periods.ctypes.data_as(double_p),
        energies.ctypes.data_as(double_p),
        theta_values.ctypes.data_as(double_p),
        inner_boundaries.ctypes.data_as(double_p),
        middle_boundaries.ctypes.data_as(double_p),
        outer_boundaries.ctypes.data_as(double_p),
        irregular.ctypes.data_as(int_p),
        inner_orbit_types.ctypes.data_as(int_p),
        middle_orbit_types.ctypes.data_as(int_p),
        noreg_grid.ctypes.data_as(int_p),
        cpp_begin.ctypes.data_as(double_p),
        cpp_begin_noreg.ctypes.data_as(int_p),
        cpp_beginbox.ctypes.data_as(double_p),
        cpp_beginbox_noreg.ctypes.data_as(int_p),
        box_iterations.ctypes.data_as(int_p),
        ctypes.byref(used_triaxial_branch),
        ctypes.byref(rounded_irregular_energy_count),
        ctypes.byref(equivalent_radius_iterations),
        ctypes.byref(inner_width_evaluations),
        ctypes.byref(inner_type_evaluations),
        ctypes.byref(outer_width_evaluations),
        ctypes.byref(outer_type_evaluations),
        ctypes.byref(box_equivalent_radius_iterations),
        ctypes.byref(cpp_rows),
        ctypes.byref(cpp_box_rows),
        ctypes.byref(cpp_status),
    )
    assert cpp_status.value == 0
    assert used_triaxial_branch.value == 1
    assert cpp_rows.value == total_records
    assert cpp_box_rows.value == total_records
    assert box_equivalent_radius_iterations.value > 0

    fortran_begin = fortran_begin.reshape(max_rows, 9)
    fortran_beginbox = fortran_beginbox.reshape(max_rows, 9)
    np.testing.assert_array_equal(cpp_begin_noreg, fortran_begin_noreg)
    np.testing.assert_array_equal(cpp_beginbox_noreg, fortran_beginbox_noreg)
    np.testing.assert_allclose(cpp_begin, fortran_begin, rtol=5e-12, atol=1e-6)
    np.testing.assert_allclose(cpp_beginbox, fortran_beginbox, rtol=5e-12, atol=1e-6)


@pytest.mark.orblib_cpp
def test_orblib_cpp_orbitstart_outer_boundaries_match_fortran_loop_order():
    surf_pc = np.array([0.0], dtype=np.float64)
    sigobs_arcsec = np.array([0.49416], dtype=np.float64)
    qobs = np.array([0.89541], dtype=np.float64)
    psi_obs = np.zeros_like(qobs)
    theta = 82.444308859
    psi = 90.021481540
    phi = 84.245110877
    distance = 39.9
    upsilon = 1.0
    black_hole_mass = 2.0e9
    black_hole_softening_arcsec = 0.0
    dark_halo_profile_type = 0
    dark_halo_parameters = np.ascontiguousarray([], dtype=np.float64)
    n_radius = 4
    n_theta = 4
    n_phi = 4
    rlogmin = 18.0
    rlogmax = 19.0
    theta_values = np.ascontiguousarray([0.35, 0.55, 0.73, 0.95], dtype=np.float64)
    outer_boundaries = np.ascontiguousarray(
        [[0.95e13, 1.0e13, 1.05e13, 1.10e13]],
        dtype=np.float64,
    )
    inner_boundaries = np.ascontiguousarray(outer_boundaries * 0.45, dtype=np.float64)
    irregular_input = np.ascontiguousarray([1], dtype=np.int32)
    i3_count = 2
    expected_setup = _expected_triaxial_mge_setup(
        surf_pc,
        sigobs_arcsec,
        qobs,
        psi_obs,
        distance,
        theta,
        phi,
        psi,
        upsilon,
    )
    reference_radius = 1.0e13
    reference_position = np.array(
        [[reference_radius * np.sin(theta_values[2]), 0.0, reference_radius * np.cos(theta_values[2])]],
        dtype=np.float64,
    )
    potential, _ = _expected_potential_stack_evaluation(
        expected_setup,
        reference_position,
        black_hole_mass,
        black_hole_softening_arcsec,
        dark_halo_profile_type,
        dark_halo_parameters,
    )
    energies = np.ascontiguousarray([0.45 * potential[0]], dtype=np.float64)
    circular_velocity = np.sqrt(GRAV_CONST_KM * black_hole_mass / reference_radius)
    circular_periods = np.ascontiguousarray(
        [2.0 * np.pi * reference_radius / circular_velocity],
        dtype=np.float64,
    )
    integrator_accuracy = 1.0e-7
    crossing_capacity = 2
    type_sample_count = 32

    library = ctypes.CDLL(str(ORBLIB_CPP_SHARED_LIBRARY))
    double_p = ctypes.POINTER(ctypes.c_double)
    type_function = library.orblib_cpp_api_orbitstart_find_type
    type_function.argtypes = [
        ctypes.c_int,
        double_p,
        double_p,
        double_p,
        double_p,
        ctypes.c_double,
        ctypes.c_double,
        ctypes.c_double,
        ctypes.c_double,
        ctypes.c_double,
        ctypes.c_double,
        ctypes.c_double,
        ctypes.c_int,
        ctypes.c_int,
        double_p,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_double,
        ctypes.c_double,
        ctypes.c_double,
        ctypes.c_double,
        ctypes.c_double,
        ctypes.c_double,
        ctypes.c_double,
        ctypes.c_int,
        ctypes.POINTER(ctypes.c_int),
        ctypes.POINTER(ctypes.c_int),
        ctypes.POINTER(ctypes.c_int),
        ctypes.POINTER(ctypes.c_int),
        ctypes.POINTER(ctypes.c_int),
    ]
    type_function.restype = None
    tube_function = library.orblib_cpp_api_orbitstart_find_tube_radius
    tube_function.argtypes = [
        ctypes.c_int,
        double_p,
        double_p,
        double_p,
        double_p,
        ctypes.c_double,
        ctypes.c_double,
        ctypes.c_double,
        ctypes.c_double,
        ctypes.c_double,
        ctypes.c_double,
        ctypes.c_double,
        ctypes.c_int,
        ctypes.c_int,
        double_p,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_double,
        ctypes.c_double,
        ctypes.c_double,
        ctypes.c_double,
        ctypes.c_double,
        ctypes.c_double,
        ctypes.c_double,
        ctypes.c_double,
        ctypes.c_int,
        ctypes.c_double,
        ctypes.c_int,
        ctypes.POINTER(ctypes.c_double),
        ctypes.POINTER(ctypes.c_double),
        ctypes.POINTER(ctypes.c_int),
        ctypes.POINTER(ctypes.c_int),
        ctypes.POINTER(ctypes.c_int),
        ctypes.POINTER(ctypes.c_int),
        ctypes.POINTER(ctypes.c_int),
    ]
    tube_function.restype = None

    def call_find_type(radius, start_theta):
        orbit_type = ctypes.c_int(-1)
        samples_collected = ctypes.c_int(-1)
        solver_status = ctypes.c_int(-1)
        function_evaluations = ctypes.c_int(-1)
        status = ctypes.c_int(-999)
        type_function(
            ctypes.c_int(surf_pc.size),
            surf_pc.ctypes.data_as(double_p),
            sigobs_arcsec.ctypes.data_as(double_p),
            qobs.ctypes.data_as(double_p),
            psi_obs.ctypes.data_as(double_p),
            ctypes.c_double(distance),
            ctypes.c_double(theta),
            ctypes.c_double(phi),
            ctypes.c_double(psi),
            ctypes.c_double(upsilon),
            ctypes.c_double(black_hole_mass),
            ctypes.c_double(black_hole_softening_arcsec),
            ctypes.c_int(dark_halo_profile_type),
            ctypes.c_int(dark_halo_parameters.size),
            None,
            ctypes.c_int(n_radius),
            ctypes.c_int(n_theta),
            ctypes.c_int(n_phi),
            ctypes.c_double(rlogmin),
            ctypes.c_double(rlogmax),
            ctypes.c_double(radius),
            ctypes.c_double(start_theta),
            ctypes.c_double(energies[0]),
            ctypes.c_double(circular_periods[0]),
            ctypes.c_double(integrator_accuracy),
            ctypes.c_int(type_sample_count),
            ctypes.byref(orbit_type),
            ctypes.byref(samples_collected),
            ctypes.byref(solver_status),
            ctypes.byref(function_evaluations),
            ctypes.byref(status),
        )
        assert status.value == 0
        assert samples_collected.value == type_sample_count
        assert solver_status.value == 1
        return orbit_type.value, function_evaluations.value

    def call_find_tube(inner_radius, middle_radius, outer_radius, start_theta):
        radius = ctypes.c_double(np.nan)
        width = ctypes.c_double(np.nan)
        width_evaluations = ctypes.c_int(-1)
        crossing_count = ctypes.c_int(-1)
        solver_status = ctypes.c_int(-1)
        function_evaluations = ctypes.c_int(-1)
        status = ctypes.c_int(-999)
        tube_function(
            ctypes.c_int(surf_pc.size),
            surf_pc.ctypes.data_as(double_p),
            sigobs_arcsec.ctypes.data_as(double_p),
            qobs.ctypes.data_as(double_p),
            psi_obs.ctypes.data_as(double_p),
            ctypes.c_double(distance),
            ctypes.c_double(theta),
            ctypes.c_double(phi),
            ctypes.c_double(psi),
            ctypes.c_double(upsilon),
            ctypes.c_double(black_hole_mass),
            ctypes.c_double(black_hole_softening_arcsec),
            ctypes.c_int(dark_halo_profile_type),
            ctypes.c_int(dark_halo_parameters.size),
            None,
            ctypes.c_int(n_radius),
            ctypes.c_int(n_theta),
            ctypes.c_int(n_phi),
            ctypes.c_double(rlogmin),
            ctypes.c_double(rlogmax),
            ctypes.c_double(inner_radius),
            ctypes.c_double(middle_radius),
            ctypes.c_double(outer_radius),
            ctypes.c_double(start_theta),
            ctypes.c_double(energies[0]),
            ctypes.c_double(circular_periods[0]),
            ctypes.c_int(1),
            ctypes.c_double(integrator_accuracy),
            ctypes.c_int(crossing_capacity),
            ctypes.byref(radius),
            ctypes.byref(width),
            ctypes.byref(width_evaluations),
            ctypes.byref(crossing_count),
            ctypes.byref(solver_status),
            ctypes.byref(function_evaluations),
            ctypes.byref(status),
        )
        assert status.value == 0
        return radius.value, width_evaluations.value

    expected_middle = outer_boundaries.copy()
    expected_irregular = irregular_input.copy()
    expected_types = np.full(outer_boundaries.shape, 5, dtype=np.int32)
    expected_width_evaluations = 0
    expected_type_evaluations = 0
    for energy_index in range(outer_boundaries.shape[0]):
        notubes = 0
        i2_index = outer_boundaries.shape[1] - 1
        rel_rbi = inner_boundaries[energy_index, i2_index] / outer_boundaries[energy_index, i2_index]
        orbit_type = 5
        radius = np.nan
        k_fortran = 0
        for k_fortran in range(1, i3_count * 3 + 1):
            radius = (
                inner_boundaries[energy_index, i2_index]
                + (outer_boundaries[energy_index, i2_index] - inner_boundaries[energy_index, i2_index])
                * k_fortran
                / (i3_count * 3 + 1)
            )
            orbit_type, evaluations = call_find_type(radius, theta_values[i2_index])
            expected_types[energy_index, i2_index] = orbit_type
            expected_type_evaluations += evaluations
            if orbit_type == 3:
                rel_rbi = radius / outer_boundaries[energy_index, i2_index]
            if (orbit_type == 1 or orbit_type == 4) and k_fortran >= 2:
                break

        if orbit_type == 3 and k_fortran >= i3_count:
            expected_irregular[energy_index] = 0
            notubes = 1
        else:
            if orbit_type == 4 or orbit_type == 5:
                bp = radius / outer_boundaries[energy_index, i2_index]
                found_x_tube = False
                break_i2 = -1
                for scan_i2 in range(outer_boundaries.shape[1] - 2, -1, -1):
                    orbit_type, evaluations = call_find_type(
                        outer_boundaries[energy_index, scan_i2] * bp,
                        theta_values[scan_i2],
                    )
                    expected_types[energy_index, scan_i2] = orbit_type
                    expected_type_evaluations += evaluations
                    if orbit_type == 1:
                        found_x_tube = True
                        break_i2 = scan_i2
                        break
                i2_index = min(break_i2 + 1, outer_boundaries.shape[1] - 2) if found_x_tube else 0

        if notubes == 0 and i2_index > 0:
            expected_middle[energy_index, i2_index] = outer_boundaries[energy_index, i2_index]
            if i2_index > 1:
                max_inner = np.max(inner_boundaries[energy_index])
                for k in range(i2_index - 1, -1, -1):
                    inner = max(outer_boundaries[energy_index, k] * rel_rbi, max_inner)
                    outer = min(expected_middle[energy_index, k + 1], outer_boundaries[energy_index, k] - 1.0e-6)
                    middle = max(
                        min(
                            expected_middle[energy_index, k + 1]
                            / outer_boundaries[energy_index, k + 1]
                            * outer_boundaries[energy_index, k],
                            outer,
                        ),
                        inner,
                    )
                    search_fraction = (1.0 - rel_rbi) / i3_count * 3.0
                    inner = max(middle * (1.0 - search_fraction), inner)
                    assert inner < outer
                    if middle <= inner or middle >= outer:
                        middle = 0.5 * (inner + outer)
                    radius, evaluations = call_find_tube(inner, middle, outer, theta_values[k])
                    expected_middle[energy_index, k] = radius
                    expected_width_evaluations += evaluations
                    orbit_type, evaluations = call_find_type(radius, theta_values[k])
                    expected_types[energy_index, k] = orbit_type
                    expected_type_evaluations += evaluations

    middle_boundaries = np.empty_like(outer_boundaries)
    irregular = irregular_input.copy()
    orbit_types = np.empty(outer_boundaries.shape, dtype=np.int32)
    width_evaluations = ctypes.c_int(-1)
    type_function_evaluations = ctypes.c_int(-1)
    status = ctypes.c_int(-999)
    function = library.orblib_cpp_api_orbitstart_outer_boundaries
    function.argtypes = [
        ctypes.c_int,
        double_p,
        double_p,
        double_p,
        double_p,
        ctypes.c_double,
        ctypes.c_double,
        ctypes.c_double,
        ctypes.c_double,
        ctypes.c_double,
        ctypes.c_double,
        ctypes.c_double,
        ctypes.c_int,
        ctypes.c_int,
        double_p,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_double,
        ctypes.c_double,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_int,
        double_p,
        double_p,
        double_p,
        double_p,
        double_p,
        ctypes.c_double,
        ctypes.c_int,
        ctypes.c_int,
        double_p,
        ctypes.POINTER(ctypes.c_int),
        ctypes.POINTER(ctypes.c_int),
        ctypes.POINTER(ctypes.c_int),
        ctypes.POINTER(ctypes.c_int),
        ctypes.POINTER(ctypes.c_int),
    ]
    function.restype = None
    function(
        ctypes.c_int(surf_pc.size),
        surf_pc.ctypes.data_as(double_p),
        sigobs_arcsec.ctypes.data_as(double_p),
        qobs.ctypes.data_as(double_p),
        psi_obs.ctypes.data_as(double_p),
        ctypes.c_double(distance),
        ctypes.c_double(theta),
        ctypes.c_double(phi),
        ctypes.c_double(psi),
        ctypes.c_double(upsilon),
        ctypes.c_double(black_hole_mass),
        ctypes.c_double(black_hole_softening_arcsec),
        ctypes.c_int(dark_halo_profile_type),
        ctypes.c_int(dark_halo_parameters.size),
        None,
        ctypes.c_int(n_radius),
        ctypes.c_int(n_theta),
        ctypes.c_int(n_phi),
        ctypes.c_double(rlogmin),
        ctypes.c_double(rlogmax),
        ctypes.c_int(outer_boundaries.shape[0]),
        ctypes.c_int(outer_boundaries.shape[1]),
        ctypes.c_int(i3_count),
        inner_boundaries.ctypes.data_as(double_p),
        outer_boundaries.ctypes.data_as(double_p),
        energies.ctypes.data_as(double_p),
        circular_periods.ctypes.data_as(double_p),
        theta_values.ctypes.data_as(double_p),
        ctypes.c_double(integrator_accuracy),
        ctypes.c_int(crossing_capacity),
        ctypes.c_int(type_sample_count),
        middle_boundaries.ctypes.data_as(double_p),
        irregular.ctypes.data_as(ctypes.POINTER(ctypes.c_int)),
        orbit_types.ctypes.data_as(ctypes.POINTER(ctypes.c_int)),
        ctypes.byref(width_evaluations),
        ctypes.byref(type_function_evaluations),
        ctypes.byref(status),
    )

    assert status.value == 0
    np.testing.assert_allclose(middle_boundaries, expected_middle, rtol=1e-12, atol=1e-2)
    np.testing.assert_array_equal(irregular, expected_irregular)
    np.testing.assert_array_equal(orbit_types, expected_types)
    assert width_evaluations.value == expected_width_evaluations
    assert type_function_evaluations.value == expected_type_evaluations


@pytest.mark.orblib_cpp
@pytest.mark.parametrize("omega", [0.0, 1.5e-16])
def test_orblib_cpp_integrates_orbit_rhs_final_state_against_scipy(omega):
    surf_pc = np.array([0.0], dtype=np.float64)
    sigobs_arcsec = np.array([0.49416], dtype=np.float64)
    qobs = np.array([0.89541], dtype=np.float64)
    psi_obs = np.zeros_like(qobs)
    theta = 82.444308859
    psi = 90.021481540
    phi = 84.245110877
    distance = 39.9
    upsilon = 1.0
    black_hole_mass = 2.0e9
    black_hole_softening_arcsec = 0.02
    dark_halo_profile_type = 0
    dark_halo_parameters = np.ascontiguousarray([], dtype=np.float64)
    n_radius = 4
    n_theta = 4
    n_phi = 4
    rlogmin = 18.0
    rlogmax = 19.0
    t_start = 0.0
    t_end = 2.0e6
    rtol = 1.0e-10
    atol = 1.0e-7
    max_steps = 10000
    initial_state = np.ascontiguousarray(
        [1.0e13, -2.0e12, 5.0e12, 18.0, -11.0, 3.0],
        dtype=np.float64,
    )
    expected_setup = _expected_triaxial_mge_setup(
        surf_pc,
        sigobs_arcsec,
        qobs,
        psi_obs,
        distance,
        theta,
        phi,
        psi,
        upsilon,
    )
    black_hole_softening_km = black_hole_softening_arcsec * expected_setup["conversion_factor"]

    def rhs(_, state):
        position = state[:3]
        velocity = state[3:]
        softened_radius_squared = np.dot(position, position) + black_hole_softening_km**2
        acceleration = (
            -GRAV_CONST_KM
            * black_hole_mass
            * position
            / (softened_radius_squared * np.sqrt(softened_radius_squared))
        )
        derivative = np.empty(6, dtype=np.float64)
        if omega == 0.0:
            derivative[:3] = velocity
            derivative[3:] = acceleration
        else:
            derivative[0] = velocity[0] + omega * position[1]
            derivative[1] = velocity[1] - omega * position[0]
            derivative[2] = velocity[2]
            derivative[3] = acceleration[0] + omega * velocity[1]
            derivative[4] = acceleration[1] - omega * velocity[0]
            derivative[5] = acceleration[2]
        return derivative

    expected = scipy.integrate.solve_ivp(
        rhs,
        (t_start, t_end),
        initial_state,
        method="DOP853",
        rtol=rtol,
        atol=atol,
    )
    assert expected.success

    final_state = np.empty(6, dtype=np.float64)
    final_time = ctypes.c_double(np.nan)
    function_evaluations = ctypes.c_int(-1)
    computed_steps = ctypes.c_int(-1)
    accepted_steps = ctypes.c_int(-1)
    rejected_steps = ctypes.c_int(-1)
    inner_fallback_count = ctypes.c_int(-1)
    outer_fallback_count = ctypes.c_int(-1)
    status = ctypes.c_int(-999)
    library = ctypes.CDLL(str(ORBLIB_CPP_SHARED_LIBRARY))
    function = library.orblib_cpp_api_integrate_orbit_final_state
    double_p = ctypes.POINTER(ctypes.c_double)
    function.argtypes = [
        ctypes.c_int,
        double_p,
        double_p,
        double_p,
        double_p,
        ctypes.c_double,
        ctypes.c_double,
        ctypes.c_double,
        ctypes.c_double,
        ctypes.c_double,
        ctypes.c_double,
        ctypes.c_double,
        ctypes.c_int,
        ctypes.c_int,
        double_p,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_double,
        ctypes.c_double,
        ctypes.c_double,
        ctypes.c_double,
        ctypes.c_double,
        ctypes.c_double,
        ctypes.c_double,
        ctypes.c_int,
        double_p,
        double_p,
        ctypes.POINTER(ctypes.c_double),
        ctypes.POINTER(ctypes.c_int),
        ctypes.POINTER(ctypes.c_int),
        ctypes.POINTER(ctypes.c_int),
        ctypes.POINTER(ctypes.c_int),
        ctypes.POINTER(ctypes.c_int),
        ctypes.POINTER(ctypes.c_int),
        ctypes.POINTER(ctypes.c_int),
    ]
    function.restype = None

    function(
        ctypes.c_int(surf_pc.size),
        surf_pc.ctypes.data_as(double_p),
        sigobs_arcsec.ctypes.data_as(double_p),
        qobs.ctypes.data_as(double_p),
        psi_obs.ctypes.data_as(double_p),
        ctypes.c_double(distance),
        ctypes.c_double(theta),
        ctypes.c_double(phi),
        ctypes.c_double(psi),
        ctypes.c_double(upsilon),
        ctypes.c_double(black_hole_mass),
        ctypes.c_double(black_hole_softening_arcsec),
        ctypes.c_int(dark_halo_profile_type),
        ctypes.c_int(dark_halo_parameters.size),
        None,
        ctypes.c_int(n_radius),
        ctypes.c_int(n_theta),
        ctypes.c_int(n_phi),
        ctypes.c_double(rlogmin),
        ctypes.c_double(rlogmax),
        ctypes.c_double(omega),
        ctypes.c_double(t_start),
        ctypes.c_double(t_end),
        ctypes.c_double(rtol),
        ctypes.c_double(atol),
        ctypes.c_int(max_steps),
        initial_state.ctypes.data_as(double_p),
        final_state.ctypes.data_as(double_p),
        ctypes.byref(final_time),
        ctypes.byref(function_evaluations),
        ctypes.byref(computed_steps),
        ctypes.byref(accepted_steps),
        ctypes.byref(rejected_steps),
        ctypes.byref(inner_fallback_count),
        ctypes.byref(outer_fallback_count),
        ctypes.byref(status),
    )

    assert status.value == 1
    assert final_time.value == pytest.approx(t_end)
    assert function_evaluations.value > 0
    assert computed_steps.value >= accepted_steps.value > 0
    assert rejected_steps.value >= 0
    assert inner_fallback_count.value > 0
    assert outer_fallback_count.value == 0
    np.testing.assert_allclose(
        final_state,
        expected.y[:, -1],
        rtol=2e-10,
        atol=1e-7,
    )


@pytest.mark.orblib_cpp
@pytest.mark.parametrize("omega", [0.0, 1.5e-16])
def test_orblib_cpp_integrates_orbit_dense_samples_against_scipy(omega):
    surf_pc = np.array([0.0], dtype=np.float64)
    sigobs_arcsec = np.array([0.49416], dtype=np.float64)
    qobs = np.array([0.89541], dtype=np.float64)
    psi_obs = np.zeros_like(qobs)
    theta = 82.444308859
    psi = 90.021481540
    phi = 84.245110877
    distance = 39.9
    upsilon = 1.0
    black_hole_mass = 2.0e9
    black_hole_softening_arcsec = 0.02
    dark_halo_profile_type = 0
    dark_halo_parameters = np.ascontiguousarray([], dtype=np.float64)
    n_radius = 4
    n_theta = 4
    n_phi = 4
    rlogmin = 18.0
    rlogmax = 19.0
    t_start = 0.0
    t_end = 2.0e6
    rtol = 1.0e-10
    atol = 1.0e-7
    max_steps = 10000
    sample_times = np.ascontiguousarray(np.linspace(t_start, t_end, 7), dtype=np.float64)
    initial_state = np.ascontiguousarray(
        [1.0e13, -2.0e12, 5.0e12, 18.0, -11.0, 3.0],
        dtype=np.float64,
    )
    expected_setup = _expected_triaxial_mge_setup(
        surf_pc,
        sigobs_arcsec,
        qobs,
        psi_obs,
        distance,
        theta,
        phi,
        psi,
        upsilon,
    )
    black_hole_softening_km = black_hole_softening_arcsec * expected_setup["conversion_factor"]

    def rhs(_, state):
        position = state[:3]
        velocity = state[3:]
        softened_radius_squared = np.dot(position, position) + black_hole_softening_km**2
        acceleration = (
            -GRAV_CONST_KM
            * black_hole_mass
            * position
            / (softened_radius_squared * np.sqrt(softened_radius_squared))
        )
        derivative = np.empty(6, dtype=np.float64)
        if omega == 0.0:
            derivative[:3] = velocity
            derivative[3:] = acceleration
        else:
            derivative[0] = velocity[0] + omega * position[1]
            derivative[1] = velocity[1] - omega * position[0]
            derivative[2] = velocity[2]
            derivative[3] = acceleration[0] + omega * velocity[1]
            derivative[4] = acceleration[1] - omega * velocity[0]
            derivative[5] = acceleration[2]
        return derivative

    expected = scipy.integrate.solve_ivp(
        rhs,
        (t_start, t_end),
        initial_state,
        method="DOP853",
        rtol=rtol,
        atol=atol,
        dense_output=True,
    )
    assert expected.success
    expected_samples = expected.sol(sample_times).T

    final_state = np.empty(6, dtype=np.float64)
    sample_state_x = np.empty(sample_times.size, dtype=np.float64)
    sample_state_y = np.empty(sample_times.size, dtype=np.float64)
    sample_state_z = np.empty(sample_times.size, dtype=np.float64)
    sample_state_vx = np.empty(sample_times.size, dtype=np.float64)
    sample_state_vy = np.empty(sample_times.size, dtype=np.float64)
    sample_state_vz = np.empty(sample_times.size, dtype=np.float64)
    samples_written = ctypes.c_int(-1)
    final_time = ctypes.c_double(np.nan)
    function_evaluations = ctypes.c_int(-1)
    computed_steps = ctypes.c_int(-1)
    accepted_steps = ctypes.c_int(-1)
    rejected_steps = ctypes.c_int(-1)
    inner_fallback_count = ctypes.c_int(-1)
    outer_fallback_count = ctypes.c_int(-1)
    status = ctypes.c_int(-999)
    library = ctypes.CDLL(str(ORBLIB_CPP_SHARED_LIBRARY))
    function = library.orblib_cpp_api_integrate_orbit_samples
    double_p = ctypes.POINTER(ctypes.c_double)
    function.argtypes = [
        ctypes.c_int,
        double_p,
        double_p,
        double_p,
        double_p,
        ctypes.c_double,
        ctypes.c_double,
        ctypes.c_double,
        ctypes.c_double,
        ctypes.c_double,
        ctypes.c_double,
        ctypes.c_double,
        ctypes.c_int,
        ctypes.c_int,
        double_p,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_double,
        ctypes.c_double,
        ctypes.c_double,
        ctypes.c_double,
        ctypes.c_double,
        ctypes.c_double,
        ctypes.c_double,
        ctypes.c_int,
        double_p,
        double_p,
        ctypes.c_int,
        double_p,
        double_p,
        double_p,
        double_p,
        double_p,
        double_p,
        double_p,
        ctypes.POINTER(ctypes.c_int),
        ctypes.POINTER(ctypes.c_double),
        ctypes.POINTER(ctypes.c_int),
        ctypes.POINTER(ctypes.c_int),
        ctypes.POINTER(ctypes.c_int),
        ctypes.POINTER(ctypes.c_int),
        ctypes.POINTER(ctypes.c_int),
        ctypes.POINTER(ctypes.c_int),
        ctypes.POINTER(ctypes.c_int),
    ]
    function.restype = None

    function(
        ctypes.c_int(surf_pc.size),
        surf_pc.ctypes.data_as(double_p),
        sigobs_arcsec.ctypes.data_as(double_p),
        qobs.ctypes.data_as(double_p),
        psi_obs.ctypes.data_as(double_p),
        ctypes.c_double(distance),
        ctypes.c_double(theta),
        ctypes.c_double(phi),
        ctypes.c_double(psi),
        ctypes.c_double(upsilon),
        ctypes.c_double(black_hole_mass),
        ctypes.c_double(black_hole_softening_arcsec),
        ctypes.c_int(dark_halo_profile_type),
        ctypes.c_int(dark_halo_parameters.size),
        None,
        ctypes.c_int(n_radius),
        ctypes.c_int(n_theta),
        ctypes.c_int(n_phi),
        ctypes.c_double(rlogmin),
        ctypes.c_double(rlogmax),
        ctypes.c_double(omega),
        ctypes.c_double(t_start),
        ctypes.c_double(t_end),
        ctypes.c_double(rtol),
        ctypes.c_double(atol),
        ctypes.c_int(max_steps),
        initial_state.ctypes.data_as(double_p),
        sample_times.ctypes.data_as(double_p),
        ctypes.c_int(sample_times.size),
        final_state.ctypes.data_as(double_p),
        sample_state_x.ctypes.data_as(double_p),
        sample_state_y.ctypes.data_as(double_p),
        sample_state_z.ctypes.data_as(double_p),
        sample_state_vx.ctypes.data_as(double_p),
        sample_state_vy.ctypes.data_as(double_p),
        sample_state_vz.ctypes.data_as(double_p),
        ctypes.byref(samples_written),
        ctypes.byref(final_time),
        ctypes.byref(function_evaluations),
        ctypes.byref(computed_steps),
        ctypes.byref(accepted_steps),
        ctypes.byref(rejected_steps),
        ctypes.byref(inner_fallback_count),
        ctypes.byref(outer_fallback_count),
        ctypes.byref(status),
    )

    assert status.value == 1
    assert samples_written.value == sample_times.size
    assert final_time.value == pytest.approx(t_end)
    assert function_evaluations.value > 0
    assert computed_steps.value >= accepted_steps.value > 0
    assert rejected_steps.value >= 0
    assert inner_fallback_count.value > 0
    assert outer_fallback_count.value == 0
    actual_samples = np.column_stack(
        [
            sample_state_x,
            sample_state_y,
            sample_state_z,
            sample_state_vx,
            sample_state_vy,
            sample_state_vz,
        ],
    )
    np.testing.assert_allclose(final_state, expected.y[:, -1], rtol=2e-10, atol=1e-7)
    np.testing.assert_allclose(actual_samples, expected_samples, rtol=2e-10, atol=1e-7)


@pytest.mark.orblib_cpp
def test_orblib_cpp_dop853_harmonic_oscillator_dense_output():
    sample_x = np.linspace(0.0, 2.0 * np.pi, 17, dtype=np.float64)
    sample_y0 = np.empty_like(sample_x)
    sample_y1 = np.empty_like(sample_x)
    final_y0 = ctypes.c_double(np.nan)
    final_y1 = ctypes.c_double(np.nan)
    function_evaluations = ctypes.c_int(-1)
    computed_steps = ctypes.c_int(-1)
    accepted_steps = ctypes.c_int(-1)
    rejected_steps = ctypes.c_int(-1)
    status = ctypes.c_int(-999)
    library = ctypes.CDLL(str(ORBLIB_CPP_SHARED_LIBRARY))
    function = library.orblib_cpp_api_dop853_harmonic
    function.argtypes = [
        ctypes.c_double,
        ctypes.c_double,
        ctypes.c_double,
        ctypes.c_double,
        ctypes.c_double,
        ctypes.c_double,
        ctypes.POINTER(ctypes.c_double),
        ctypes.c_int,
        ctypes.POINTER(ctypes.c_double),
        ctypes.POINTER(ctypes.c_double),
        ctypes.POINTER(ctypes.c_double),
        ctypes.POINTER(ctypes.c_double),
        ctypes.POINTER(ctypes.c_int),
        ctypes.POINTER(ctypes.c_int),
        ctypes.POINTER(ctypes.c_int),
        ctypes.POINTER(ctypes.c_int),
        ctypes.POINTER(ctypes.c_int),
    ]
    function.restype = None

    function(
        ctypes.c_double(0.0),
        ctypes.c_double(1.0),
        ctypes.c_double(0.0),
        ctypes.c_double(2.0 * np.pi),
        ctypes.c_double(1e-12),
        ctypes.c_double(1e-12),
        sample_x.ctypes.data_as(ctypes.POINTER(ctypes.c_double)),
        ctypes.c_int(sample_x.size),
        ctypes.byref(final_y0),
        ctypes.byref(final_y1),
        sample_y0.ctypes.data_as(ctypes.POINTER(ctypes.c_double)),
        sample_y1.ctypes.data_as(ctypes.POINTER(ctypes.c_double)),
        ctypes.byref(function_evaluations),
        ctypes.byref(computed_steps),
        ctypes.byref(accepted_steps),
        ctypes.byref(rejected_steps),
        ctypes.byref(status),
    )

    assert status.value == 1
    assert function_evaluations.value > 0
    assert computed_steps.value >= accepted_steps.value > 0
    assert rejected_steps.value >= 0
    np.testing.assert_allclose(final_y0.value, 1.0, rtol=0.0, atol=5e-12)
    np.testing.assert_allclose(final_y1.value, 0.0, rtol=0.0, atol=5e-12)
    np.testing.assert_allclose(sample_y0, np.cos(sample_x), rtol=0.0, atol=5e-12)
    np.testing.assert_allclose(sample_y1, -np.sin(sample_x), rtol=0.0, atol=5e-12)
