import shutil

import numpy as np
import pytest
import yaml

from conftest import REPO_ROOT


FIXTURE_DIR = REPO_ROOT / "tests" / "fixtures" / "orblib_losvd"


def copy_orblib_fixture_workspace(tmp_path):
    target = tmp_path / "orblib_losvd"
    shutil.copytree(
        FIXTURE_DIR,
        target,
        ignore=shutil.ignore_patterns(
            "__pycache__",
            "*.pyc",
            "*_output",
            "output_*.txt",
            "*.log",
        ),
    )
    return target


def set_orbit_random_seed(config_path, seed):
    with config_path.open() as handle:
        config = yaml.safe_load(handle)
    config["orblib_settings"]["random_seed"] = seed
    with config_path.open("w") as handle:
        yaml.safe_dump(config, handle, sort_keys=False)


def set_weight_solver(config_path, solver_type, nnls_solver):
    with config_path.open() as handle:
        config = yaml.safe_load(handle)
    config["weight_solver_settings"]["type"] = solver_type
    config["weight_solver_settings"]["nnls_solver"] = nnls_solver
    with config_path.open("w") as handle:
        yaml.safe_dump(config, handle, sort_keys=False)


def generate_losvd_histogram(workspace, monkeypatch):
    import dynamite as dyn

    monkeypatch.chdir(workspace)
    config = dyn.config_reader.Configuration(
        "user_test_config.yaml",
        reset_logging=False,
        reset_existing_output=True,
    )
    parset = config.parspace.get_parset()
    model = dyn.model.Model(config=config, parset=parset)
    model.setup_directories()
    register_fixture_model(config, model, parset)
    orbit_library = model.get_orblib()
    orbit_library.read_losvd_histograms()
    return orbit_library.losvd_histograms[0]


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


def assert_losvd_matches_reference(actual, reference_path):
    reference = np.load(reference_path)
    expected_xedg = reference["xedg"]
    expected_y = reference["y"]

    np.testing.assert_array_equal(actual.xedg, expected_xedg)
    assert actual.y.shape == expected_y.shape
    assert np.all(np.isfinite(actual.y))
    assert np.all(actual.y >= 0.0)

    abs_diff = np.abs(actual.y - expected_y)
    np.testing.assert_allclose(
        np.sum(actual.y),
        np.sum(expected_y),
        rtol=5e-4,
        atol=1e-8,
    )
    assert np.mean(abs_diff) <= 5e-6
    assert np.quantile(abs_diff, 0.999) <= 2e-4
    assert np.max(abs_diff) <= 3e-3


def test_configuration_rejects_archived_legacy_weight_solver(tmp_path, monkeypatch):
    import dynamite as dyn

    workspace = copy_orblib_fixture_workspace(tmp_path)
    set_weight_solver(
        workspace / "user_test_config.yaml",
        solver_type="LegacyWeightSolver",
        nnls_solver=1,
    )

    monkeypatch.chdir(workspace)
    with pytest.raises(ValueError, match="LegacyWeightSolver is archived"):
        dyn.config_reader.Configuration(
            "user_test_config.yaml",
            reset_logging=False,
            reset_existing_output=True,
        )


@pytest.mark.slow
@pytest.mark.orblib_fortran
def test_fortran_orblib_losvd_output_matches_reference_fixture(tmp_path, monkeypatch):
    workspace = copy_orblib_fixture_workspace(tmp_path)
    set_orbit_random_seed(workspace / "user_test_config.yaml", seed=4242)

    actual = generate_losvd_histogram(workspace, monkeypatch)

    output_dir = workspace / "NGC6278_output"
    assert output_dir.is_dir()
    assert_losvd_matches_reference(
        actual,
        workspace / "data" / "comparison_losvd.npz",
    )
