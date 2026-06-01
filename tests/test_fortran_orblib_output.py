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
    orbit_library = model.get_orblib()
    orbit_library.read_losvd_histograms()
    return orbit_library.losvd_histograms[0]


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
        rtol=2e-4,
        atol=1e-8,
    )
    assert np.mean(abs_diff) <= 5e-6
    assert np.quantile(abs_diff, 0.999) <= 2e-4
    assert np.max(abs_diff) <= 3e-3


@pytest.mark.slow
@pytest.mark.legacy_fortran
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
