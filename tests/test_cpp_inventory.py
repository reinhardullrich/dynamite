import ctypes

import numpy as np
import pytest
import scipy.integrate
import scipy.special

from conftest import ORBLIB_CPP_DIR, ORBLIB_CPP_SHARED_LIBRARY
from dynamite import orblib_api
from dynamite.myrand import MyRand


CPP_SOURCES = [
    "Makefile",
    "include/dop853.hpp",
    "include/elliptic_integrals.hpp",
    "include/interpolated_potential.hpp",
    "include/orbit_integrator.hpp",
    "include/orbit_rhs.hpp",
    "include/potential.hpp",
    "include/ran1.hpp",
    "include/triaxial_mge.hpp",
    "source/dop853.cpp",
    "source/elliptic_integrals.cpp",
    "source/interpolated_potential.cpp",
    "source/orbit_integrator.cpp",
    "source/orbit_rhs.cpp",
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
