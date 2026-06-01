import json
from pathlib import Path

import h5py
import numpy as np
import pytest
import yaml
from astropy import table
from astropy.io import fits

from conftest import DEV_TESTS_DIR
from test_example_catalog import (
    DEV_TEST_PYTHON_EXAMPLES,
    DEV_TEST_SHELL_EXAMPLES,
    NOTEBOOK_EXAMPLES,
    YAML_EXAMPLE_CONFIGS,
)


ECSV_FIXTURES = [
    "NGC6278_input/gauss_hermite_kins.ecsv",
    "NGC6278_input/gauss_hermite_kins_with_pops.ecsv",
    "NGC6278_input/mge.ecsv",
    "NGC6278_input/mge_lum.ecsv",
    "NGC6278_input/mge_pot.ecsv",
    "NGC6278_input/stellar_pops.ecsv",
    "bartest_input/bar_mge.ecsv",
    "bartest_input/disk_mge.ecsv",
    "bartest_input/kinematics.ecsv",
]

TEXT_FIXTURES = [
    "NGC6278_input/aperture.dat",
    "NGC6278_input/aperture_for_pops.dat",
    "NGC6278_input/bins.dat",
    "NGC6278_input/bins_for_pops.dat",
    "bartest_input/aperture.dat",
    "bartest_input/bins.dat",
]

TABLE_FIXTURES = [
    "data/bar_chi2_compare_ml_654.dat",
    "data/chi2_compare_ml_654.dat",
]

NUMERIC_TEXT_FIXTURES = [
    "data/randata-4242.txt",
]

NPZ_FIXTURES = [
    "data/comparison_losvd.npz",
]

FITS_FIXTURES = [
    "Data_prep/Kinematics/ATLAS3D/MS_NGC4570_r1_C2D.fits",
    "Data_prep/Kinematics/ATLAS3D/NGC4570_4moments_ATLAS3d.fits",
    "Data_prep/Kinematics/CALIFA/NGC6278.V1200.rscube_INDOUSv2_SN20_stellar_kin.fits",
]

PDF_FIXTURES = [
    "Data_prep/Kinematics/ATLAS3D/kinmaps.pdf",
    "Data_prep/Kinematics/CALIFA/kinmaps.pdf",
]

HDF5_FIXTURES = [
    "bayes_losvd/NGC0000-SP_results.hdf5",
]


def _archived_yaml_paths():
    prefix = "archive/dev_tests/"
    return [
        path.removeprefix(prefix)
        for path in YAML_EXAMPLE_CONFIGS
        if path.startswith(prefix)
    ]


def _archived_notebook_paths():
    prefix = "archive/dev_tests/"
    return [
        path.removeprefix(prefix)
        for path in NOTEBOOK_EXAMPLES
        if path.startswith(prefix)
    ]


ALL_EXPECTED_ARCHIVED_FILES = set(
    DEV_TEST_PYTHON_EXAMPLES
    + DEV_TEST_SHELL_EXAMPLES
    + _archived_yaml_paths()
    + _archived_notebook_paths()
    + ECSV_FIXTURES
    + TEXT_FIXTURES
    + TABLE_FIXTURES
    + NUMERIC_TEXT_FIXTURES
    + NPZ_FIXTURES
    + FITS_FIXTURES
    + PDF_FIXTURES
    + HDF5_FIXTURES
)


def _actual_archived_files():
    files = []
    for path in DEV_TESTS_DIR.rglob("*"):
        if path.is_file() and "__pycache__" not in path.parts:
            files.append(path.relative_to(DEV_TESTS_DIR).as_posix())
    return set(files)


def test_every_archived_dev_test_file_is_represented_by_pytest():
    actual = _actual_archived_files()
    assert actual == ALL_EXPECTED_ARCHIVED_FILES


@pytest.mark.parametrize("relative_path", ECSV_FIXTURES)
def test_archived_ecsv_fixture_is_readable(relative_path):
    fixture = table.Table.read(DEV_TESTS_DIR / relative_path, format="ascii.ecsv")
    assert len(fixture) > 0
    assert fixture.colnames


@pytest.mark.parametrize("relative_path", TEXT_FIXTURES)
def test_archived_text_fixture_is_nonempty(relative_path):
    text = (DEV_TESTS_DIR / relative_path).read_text().strip()
    assert text


@pytest.mark.parametrize("relative_path", TABLE_FIXTURES)
def test_archived_ascii_table_fixture_is_readable(relative_path):
    fixture = table.Table.read(DEV_TESTS_DIR / relative_path, format="ascii")
    assert len(fixture) > 0
    assert fixture.colnames


@pytest.mark.parametrize("relative_path", NUMERIC_TEXT_FIXTURES)
def test_archived_numeric_text_fixture_is_readable(relative_path):
    values = np.loadtxt(DEV_TESTS_DIR / relative_path)
    assert values.size > 0
    assert np.all(np.isfinite(values))


@pytest.mark.parametrize("relative_path", NPZ_FIXTURES)
def test_archived_npz_fixture_is_readable(relative_path):
    fixture = np.load(DEV_TESTS_DIR / relative_path)
    assert fixture.files
    for key in fixture.files:
        assert fixture[key].size > 0


@pytest.mark.parametrize("relative_path", FITS_FIXTURES)
def test_archived_fits_fixture_is_readable(relative_path):
    with fits.open(DEV_TESTS_DIR / relative_path) as hdul:
        assert len(hdul) > 0
        assert hdul[0].header


@pytest.mark.parametrize("relative_path", PDF_FIXTURES)
def test_archived_pdf_fixture_has_pdf_header(relative_path):
    with (DEV_TESTS_DIR / relative_path).open("rb") as handle:
        assert handle.read(5) == b"%PDF-"


@pytest.mark.parametrize("relative_path", HDF5_FIXTURES)
def test_archived_hdf5_fixture_is_readable(relative_path):
    with h5py.File(DEV_TESTS_DIR / relative_path, "r") as handle:
        assert list(handle.keys())


@pytest.mark.parametrize("relative_path", _archived_yaml_paths())
def test_archived_yaml_fixture_is_readable(relative_path):
    with (DEV_TESTS_DIR / relative_path).open() as handle:
        assert isinstance(yaml.safe_load(handle), dict)


@pytest.mark.parametrize("relative_path", _archived_notebook_paths())
def test_archived_notebook_fixture_is_readable(relative_path):
    with (DEV_TESTS_DIR / relative_path).open() as handle:
        notebook = json.load(handle)
    assert notebook["nbformat"] >= 4
    assert notebook["cells"]

