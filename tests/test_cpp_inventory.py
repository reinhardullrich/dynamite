import ctypes

import numpy as np
import pytest
import scipy.special

from conftest import ORBLIB_CPP_DIR, ORBLIB_CPP_SHARED_LIBRARY
from dynamite import orblib_api
from dynamite.myrand import MyRand


CPP_SOURCES = [
    "Makefile",
    "include/dop853.hpp",
    "include/elliptic_integrals.hpp",
    "include/ran1.hpp",
    "include/triaxial_mge.hpp",
    "source/dop853.cpp",
    "source/elliptic_integrals.cpp",
    "source/orblib_cpp_api.cpp",
    "source/ran1.cpp",
    "source/triaxial_mge.cpp",
]


PARSEC_KM = 1.4959787068e8 * (648e3 / np.pi)
GRAV_CONST_KM = 6.67428e-11 * 1.98892e30 / 1e9


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
    return {
        "pintr": pintr,
        "qintr": qintr,
        "sigintr_km": sigintr_km,
        "density": density,
        "v0": v0,
        "triaxiality": triaxiality,
        "total_mass": total_mass,
    }


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
