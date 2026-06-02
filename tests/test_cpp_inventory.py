import ctypes

import numpy as np
import pytest

from conftest import ORBLIB_CPP_DIR, ORBLIB_CPP_SHARED_LIBRARY
from dynamite import orblib_api
from dynamite.myrand import MyRand


CPP_SOURCES = [
    "Makefile",
    "include/dop853.hpp",
    "include/ran1.hpp",
    "source/dop853.cpp",
    "source/orblib_cpp_api.cpp",
    "source/ran1.cpp",
]


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
