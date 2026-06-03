import bz2
from contextlib import contextmanager
import os
from pathlib import Path
import shutil

import numpy as np
import pytest
import yaml

from conftest import REPO_ROOT
from dynamite import orblib_api


FIXTURE_DIR = REPO_ROOT / "tests" / "fixtures" / "orblib_losvd"
OUTPUT_ROOTS = ("orblib", "orblibbox")
COMPRESSED_SUFFIXES = ("qgrid", "losvd_hist", "pops")
DONE_MARKERS = ("tube_done", "box_done", "tube_box_done")


@contextmanager
def working_directory(path):
    current = Path.cwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(current)


def copy_orblib_fixture_workspace(tmp_path, name):
    target = tmp_path / name
    shutil.copytree(
        FIXTURE_DIR,
        target,
        ignore=shutil.ignore_patterns(
            "__pycache__",
            "*.pyc",
            "*_output",
            "output_*.txt",
            "*.log",
            "interpolgrid",
        ),
    )
    return target


def configure_fast_complete_library_with_pops(config_path):
    with config_path.open() as handle:
        config = yaml.safe_load(handle)

    stars = config["system_components"]["stars"]
    stars["populations"] = {
        "pop1": {
            "datafile": "stellar_pops.ecsv",
            "aperturefile": "aperture_for_pops.dat",
            "binfile": "bins_for_pops.dat",
        }
    }

    settings = config["orblib_settings"]
    settings["random_seed"] = 4242
    settings["orbital_periods"] = 2
    settings["sampling"] = 128
    settings["starting_orbit"] = 1
    settings["number_orbits"] = -1

    with config_path.open("w") as handle:
        yaml.safe_dump(config, handle, sort_keys=False)


def register_fixture_model(config, model, parset):
    model_root = config.settings.io_settings["model_directory"]
    relative_directory = model.directory.removeprefix(model_root)
    row = []
    for column in config.all_models.table.columns.values():
        if column.name in config.parspace.par_names:
            value = parset[column.name]
        elif column.name == "time_modified":
            value = str(np.datetime64("now", "s"))
        elif column.name == "which_iter":
            value = 0
        elif column.name == "directory":
            value = relative_directory
        else:
            value = column.dtype.type(None)
        row.append(value)
    config.all_models.table.add_row(row)


def generate_orbit_library(workspace, backend):
    import dynamite as dyn

    configure_fast_complete_library_with_pops(workspace / "user_test_config.yaml")
    with working_directory(workspace):
        config = dyn.config_reader.Configuration(
            "user_test_config.yaml",
            reset_logging=False,
            reset_existing_output=True,
        )
        parset = config.parspace.get_parset()
        model = dyn.model.Model(config=config, parset=parset)
        model.setup_directories()
        register_fixture_model(config, model, parset)
        orbit_library = dyn.orblib.LegacyOrbitLibrary(
            config=config,
            mod_dir=model.directory_noml,
            parset=parset,
        )
        backend.generate_orbit_library(orbit_library)
        datfil = (Path(model.directory_noml) / "datfil").resolve()
    return datfil


def decompressed_fortran_records(path):
    data = bz2.decompress(path.read_bytes())
    records = []
    offset = 0
    while offset < len(data):
        if offset + 4 > len(data):
            raise AssertionError(f"Truncated Fortran record marker in {path}.")
        size = int.from_bytes(data[offset:offset + 4], "little", signed=True)
        offset += 4
        payload = data[offset:offset + size]
        offset += size
        if offset + 4 > len(data):
            raise AssertionError(f"Truncated Fortran record trailer in {path}.")
        trailer = int.from_bytes(data[offset:offset + 4], "little", signed=True)
        offset += 4
        if size != trailer:
            raise AssertionError(
                f"Fortran record marker mismatch in {path}: {size} != {trailer}."
            )
        records.append(payload)
    return records


def record_as_ints(record):
    assert len(record) % np.dtype(np.int32).itemsize == 0
    return np.frombuffer(record, dtype=np.int32)


def record_as_reals(record):
    assert len(record) % np.dtype(np.float64).itemsize == 0
    return np.frombuffer(record, dtype=np.float64)


def read_qgrid(path):
    records = decompressed_fortran_records(path)
    header = record_as_ints(records[0]).copy()
    grid_sizes = record_as_ints(records[1]).copy()
    radius = record_as_reals(records[2]).copy()
    theta = record_as_reals(records[3]).copy()
    phi = record_as_reals(records[4]).copy()
    orbit_records = []
    offset = 5
    orbit_count = int(header[0])
    for _orbit_index in range(orbit_count):
        orbit_header = record_as_ints(records[offset]).copy()
        orbit_types = record_as_ints(records[offset + 1]).copy()
        qgrid = record_as_reals(records[offset + 2]).copy()
        orbit_records.append((orbit_header, orbit_types, qgrid))
        offset += 3
    for trailing_record in records[offset:]:
        if trailing_record.strip():
            raise AssertionError(f"Unexpected trailing qgrid record in {path}.")
    return {
        "header": header,
        "grid_sizes": grid_sizes,
        "radius": radius,
        "theta": theta,
        "phi": phi,
        "orbits": orbit_records,
    }


def read_losvd(path):
    records = decompressed_fortran_records(path)
    header_payload = records[0]
    assert len(header_payload) == 16
    header = (
        np.frombuffer(header_payload[:4], dtype=np.int32).copy(),
        np.frombuffer(header_payload[4:8], dtype=np.int32).copy(),
        np.frombuffer(header_payload[8:], dtype=np.float64).copy(),
    )
    rows = []
    offset = 1
    while offset < len(records):
        row_range = record_as_ints(records[offset]).copy()
        assert row_range.shape == (2,)
        offset += 1
        if row_range[0] <= row_range[1]:
            values = record_as_reals(records[offset]).copy()
            offset += 1
        else:
            values = np.array([], dtype=np.float64)
        rows.append((row_range, values))
    return header, rows


def read_pops(path):
    return [record_as_reals(record).copy() for record in decompressed_fortran_records(path)]


def read_orbclass(path):
    values = np.fromstring(path.read_text(), sep=" ")
    if values.size == 0:
        raise AssertionError(f"Empty orbclass file: {path}")
    return values


def assert_output_contract(datfil):
    for marker in DONE_MARKERS:
        assert (datfil / marker).is_file()
    for root in OUTPUT_ROOTS:
        assert (datfil / f"{root}.dat_orbclass.out").is_file()
        for suffix in COMPRESSED_SUFFIXES:
            assert (datfil / f"{root}_{suffix}.dat.bz2").is_file()
            assert not (datfil / f"{root}_{suffix}.dat").exists()
            assert not (datfil / f"{root}_{suffix}.dat.staging.bz2").exists()


def assert_float_arrays_close(actual, expected, label):
    assert actual.shape == expected.shape, label
    assert np.all(np.isfinite(actual)), label
    assert np.all(np.isfinite(expected)), label
    np.testing.assert_allclose(actual, expected, rtol=1e-12, atol=1e-12, err_msg=label)


def assert_qgrid_matches(actual_path, expected_path):
    actual = read_qgrid(actual_path)
    expected = read_qgrid(expected_path)
    np.testing.assert_array_equal(actual["header"], expected["header"])
    np.testing.assert_array_equal(actual["grid_sizes"], expected["grid_sizes"])
    assert_float_arrays_close(actual["radius"], expected["radius"], f"{actual_path} radius")
    assert_float_arrays_close(actual["theta"], expected["theta"], f"{actual_path} theta")
    assert_float_arrays_close(actual["phi"], expected["phi"], f"{actual_path} phi")
    assert len(actual["orbits"]) == len(expected["orbits"])
    for index, (actual_orbit, expected_orbit) in enumerate(
        zip(actual["orbits"], expected["orbits"], strict=True),
        start=1,
    ):
        np.testing.assert_array_equal(
            actual_orbit[0],
            expected_orbit[0],
            err_msg=f"{actual_path} orbit {index} header",
        )
        np.testing.assert_array_equal(
            actual_orbit[1],
            expected_orbit[1],
            err_msg=f"{actual_path} orbit {index} types",
        )
        assert_float_arrays_close(
            actual_orbit[2],
            expected_orbit[2],
            f"{actual_path} orbit {index} qgrid",
        )


def assert_losvd_matches(actual_path, expected_path):
    actual_header, actual_rows = read_losvd(actual_path)
    expected_header, expected_rows = read_losvd(expected_path)
    np.testing.assert_array_equal(actual_header[0], expected_header[0])
    np.testing.assert_array_equal(actual_header[1], expected_header[1])
    assert_float_arrays_close(actual_header[2], expected_header[2], f"{actual_path} header")
    assert len(actual_rows) == len(expected_rows)
    for index, (actual_row, expected_row) in enumerate(
        zip(actual_rows, expected_rows, strict=True),
        start=1,
    ):
        np.testing.assert_array_equal(
            actual_row[0],
            expected_row[0],
            err_msg=f"{actual_path} row {index} range",
        )
        assert_float_arrays_close(
            actual_row[1],
            expected_row[1],
            f"{actual_path} row {index} values",
        )


def assert_pops_matches(actual_path, expected_path):
    actual = read_pops(actual_path)
    expected = read_pops(expected_path)
    assert len(actual) == len(expected)
    for index, (actual_record, expected_record) in enumerate(
        zip(actual, expected, strict=True),
        start=1,
    ):
        assert_float_arrays_close(
            actual_record,
            expected_record,
            f"{actual_path} record {index}",
        )


def assert_orbclass_matches(actual_path, expected_path):
    assert_float_arrays_close(
        read_orbclass(actual_path),
        read_orbclass(expected_path),
        f"{actual_path}",
    )


@pytest.fixture(scope="module")
def generated_cpp_fortran_datfils(tmp_path_factory):
    workspace_root = tmp_path_factory.mktemp("cpp_fortran_orblib_parity")
    fortran_workspace = copy_orblib_fixture_workspace(workspace_root, "fortran")
    cpp_workspace = copy_orblib_fixture_workspace(workspace_root, "cpp")

    fortran_datfil = generate_orbit_library(
        fortran_workspace,
        orblib_api.SharedLibraryFortranOrbitBackend(isolate_fortran_calls=True),
    )
    cpp_datfil = generate_orbit_library(
        cpp_workspace,
        orblib_api.SharedLibraryCppOrbitBackend(),
    )
    return fortran_datfil, cpp_datfil


@pytest.mark.slow
@pytest.mark.orblib_cpp
@pytest.mark.orblib_fortran
def test_cpp_full_orbit_library_output_contract_matches_active_fortran(
    generated_cpp_fortran_datfils,
):
    fortran_datfil, cpp_datfil = generated_cpp_fortran_datfils

    assert_output_contract(fortran_datfil)
    assert_output_contract(cpp_datfil)


@pytest.mark.slow
@pytest.mark.orblib_cpp
@pytest.mark.orblib_fortran
@pytest.mark.xfail(
    reason=(
        "C++ full orbit-library values do not yet match active Fortran; "
        "the first observed mismatch is the qgrid radial boundary array."
    ),
    strict=True,
)
def test_cpp_full_orbit_library_values_match_active_fortran(
    generated_cpp_fortran_datfils,
):
    fortran_datfil, cpp_datfil = generated_cpp_fortran_datfils

    for root in OUTPUT_ROOTS:
        assert_qgrid_matches(
            cpp_datfil / f"{root}_qgrid.dat.bz2",
            fortran_datfil / f"{root}_qgrid.dat.bz2",
        )
        assert_losvd_matches(
            cpp_datfil / f"{root}_losvd_hist.dat.bz2",
            fortran_datfil / f"{root}_losvd_hist.dat.bz2",
        )
        assert_pops_matches(
            cpp_datfil / f"{root}_pops.dat.bz2",
            fortran_datfil / f"{root}_pops.dat.bz2",
        )
        assert_orbclass_matches(
            cpp_datfil / f"{root}.dat_orbclass.out",
            fortran_datfil / f"{root}.dat_orbclass.out",
        )
