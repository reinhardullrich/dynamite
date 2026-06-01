import numpy as np
import pytest
from astropy import table

from conftest import copy_dev_tests_workspace, run_python_script


@pytest.mark.slow
@pytest.mark.legacy_fortran
def test_existing_orbit_losvd_workflow_runs_against_reference_fixture(tmp_path):
    workspace = copy_dev_tests_workspace(tmp_path)
    run_python_script(workspace / "test_orbit_losvds.py", cwd=workspace)

    fixture = np.load(workspace / "data" / "comparison_losvd.npz")
    output_dir = workspace / "NGC6278_output"
    assert output_dir.is_dir()
    assert fixture["y"].shape == (72, 203, 152)


@pytest.mark.slow
def test_existing_nnls_workflow_reproduces_reference_chi2_table(tmp_path):
    workspace = copy_dev_tests_workspace(tmp_path)
    run_python_script(workspace / "test_nnls.py", cwd=workspace)

    actual = table.Table.read(
        workspace / "NGC6278_output" / "all_models.ecsv",
        format="ascii.ecsv",
    )
    expected = table.Table.read(
        workspace / "data" / "chi2_compare_ml_654.dat",
        format="ascii",
    )
    assert len(actual) >= len(expected)
    for column in ("chi2", "kinchi2", "kinmapchi2"):
        np.testing.assert_allclose(
            actual[column][: len(expected)],
            expected[column],
            rtol=1e-8,
            atol=1e-5,
        )


@pytest.mark.slow
@pytest.mark.legacy_fortran
def test_existing_reimplement_nnls_workflow_compares_legacy_and_python(tmp_path):
    workspace = copy_dev_tests_workspace(tmp_path)
    run_python_script(workspace / "test_reimplement_nnls.py", cwd=workspace, timeout=1800)

    output_dir = workspace / "NGC6278_output"
    legacy = table.Table.read(output_dir / "all_models_LegacyWS.ecsv", format="ascii.ecsv")
    python = table.Table.read(output_dir / "all_models_NNLS.ecsv", format="ascii.ecsv")

    assert len(legacy) == len(python)
    for column in ("chi2", "kinchi2", "kinmapchi2"):
        np.testing.assert_allclose(
            python[column],
            legacy[column],
            rtol=1e-8,
            atol=1e-5,
        )


@pytest.mark.slow
def test_existing_bar_workflow_runs(tmp_path):
    workspace = copy_dev_tests_workspace(tmp_path)
    run_python_script(workspace / "test_bar.py", cwd=workspace, timeout=1800)

    output_dir = workspace / "bartest_output"
    assert output_dir.is_dir()
    results = table.Table.read(output_dir / "all_models.ecsv", format="ascii.ecsv")
    assert len(results) > 0
    for column in ("chi2", "kinchi2", "kinmapchi2"):
        assert np.all(np.isfinite(results[column]))


@pytest.mark.slow
@pytest.mark.legacy_fortran
def test_existing_different_dark_halos_workflow_runs(tmp_path):
    workspace = copy_dev_tests_workspace(tmp_path)
    run_python_script(workspace / "dif_dm_halos.py", cwd=workspace, timeout=1800)

    output_dir = workspace / "NGC6278_output"
    assert output_dir.is_dir()
    results = table.Table.read(output_dir / "all_models.ecsv", format="ascii.ecsv")
    assert len(results) > 0


@pytest.mark.slow
@pytest.mark.legacy_fortran
def test_existing_slurm_local_workflow_runs(tmp_path):
    workspace = copy_dev_tests_workspace(tmp_path)
    run_python_script(workspace / "test_slurm.py", cwd=workspace, timeout=1800)

    output_dir = workspace / "NGC6278_output"
    assert output_dir.is_dir()
    results = table.Table.read(output_dir / "all_models.ecsv", format="ascii.ecsv")
    assert len(results) > 0
