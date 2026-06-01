import json
import py_compile
import subprocess
from pathlib import Path

import pytest
import yaml

from conftest import DEV_TESTS_DIR, REPO_ROOT


DEV_TEST_PYTHON_EXAMPLES = [
    "chi2_ext.py",
    "dif_dm_halos.py",
    "myrantest.py",
    "run_dataprep.py",
    "test_bar.py",
    "test_dataprep.py",
    "test_decomp.py",
    "test_nnls.py",
    "test_orbit_losvds.py",
    "test_reimplement_nnls.py",
    "test_slurm.py",
]

DEV_TEST_SHELL_EXAMPLES = [
    "run_all.sh",
    "test_all.sh",
    "test_notebooks.sh",
]

YAML_EXAMPLE_CONFIGS = [
    "dev_tests/bartest.yaml",
    "dev_tests/bayes_losvd/IC0719_dynamite_config.yaml",
    "dev_tests/dif_dm_halos_config.yaml",
    "dev_tests/reimplement_nnls_config1.yaml",
    "dev_tests/reimplement_nnls_config2.yaml",
    "dev_tests/test_slurm_config.yaml",
    "dev_tests/user_test_config.yaml",
    "dev_tests/user_test_config_ml.yaml",
    "dev_tests/user_test_config_ml_gas.yaml",
    "dev_tests/user_test_config_specificmodels.yaml",
    "docs/tutorial_notebooks/FCC167_config.yaml",
    "docs/tutorial_notebooks/NGC4550_config.yaml",
    "docs/tutorial_notebooks/NGC6278_config.yaml",
    "docs/tutorial_notebooks/NGC6278_config_single.yaml",
]

NOTEBOOK_EXAMPLES = [
    "dev_tests/Rmax-vs-zmax-test.ipynb",
    "dev_tests/bayes_losvd/DYNMAITE_and_BAYES_LOSVD.ipynb",
    "dev_tests/orbit_densities.ipynb",
    "docs/tutorial_notebooks/1_data_prep_for_gauss_hermite.ipynb",
    "docs/tutorial_notebooks/2_quickstart.ipynb",
    "docs/tutorial_notebooks/3_model_iterations_and_plots.ipynb",
    "docs/tutorial_notebooks/4_BayesLOSVD.ipynb",
    "docs/tutorial_notebooks/5_parameter_space.ipynb",
    "docs/tutorial_notebooks/6_orbits_and_weights.ipynb",
    "docs/tutorial_notebooks/7_orbital_distributions.ipynb",
    "docs/tutorial_notebooks/8_coloring.ipynb",
]


@pytest.mark.parametrize("relative_path", DEV_TEST_PYTHON_EXAMPLES)
def test_dev_test_python_example_compiles(relative_path):
    path = DEV_TESTS_DIR / relative_path
    py_compile.compile(str(path), doraise=True)


@pytest.mark.parametrize("relative_path", DEV_TEST_SHELL_EXAMPLES)
def test_dev_test_shell_example_has_valid_bash_syntax(relative_path):
    path = DEV_TESTS_DIR / relative_path
    subprocess.run(["bash", "-n", str(path)], check=True)


@pytest.mark.parametrize("relative_path", YAML_EXAMPLE_CONFIGS)
def test_example_yaml_config_has_required_sections(relative_path):
    path = REPO_ROOT / relative_path
    with path.open() as handle:
        config = yaml.safe_load(handle)

    assert isinstance(config, dict)
    for section in (
        "system_attributes",
        "system_components",
        "system_parameters",
        "orblib_settings",
        "weight_solver_settings",
        "parameter_space_settings",
        "io_settings",
    ):
        assert section in config

    weight_solver = config["weight_solver_settings"]
    assert weight_solver["type"] in {"LegacyWeightSolver", "NNLS"}
    if weight_solver["type"] == "LegacyWeightSolver":
        assert weight_solver["nnls_solver"] == 1
    else:
        assert weight_solver["nnls_solver"] in {"scipy", "cvxopt"}

    orblib = config["orblib_settings"]
    assert orblib["nE"] > 0
    assert orblib["nI2"] >= 4
    assert orblib["nI3"] > 0

    stopping = config["parameter_space_settings"]["stopping_criteria"]
    assert stopping["n_max_mods"] > 0


@pytest.mark.parametrize("relative_path", NOTEBOOK_EXAMPLES)
def test_notebook_example_is_valid_ipynb(relative_path):
    path = REPO_ROOT / relative_path
    with path.open() as handle:
        notebook = json.load(handle)

    assert notebook["nbformat"] >= 4
    assert isinstance(notebook.get("cells"), list)
    assert notebook["cells"]


def test_external_chi2_example_returns_documented_constant():
    import importlib.util
    from types import SimpleNamespace

    module_path = DEV_TESTS_DIR / "chi2_ext.py"
    spec = importlib.util.spec_from_file_location("chi2_ext_example", module_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    class FakeAllModels:
        def get_parset_from_row(self, row_id):
            return {"ml": 5.0, "row_id": row_id}

        def get_model_velocity_scaling_factor(self, model_id):
            return 1.0

    fake_config = SimpleNamespace(
        system=SimpleNamespace(cmp_list=[SimpleNamespace(name="stars")]),
        all_models=FakeAllModels(),
        params={"system_attributes": {"name": "fake"}},
    )

    chi2_ext = module.Chi2Ext("arg1", "arg2")
    assert chi2_ext.chi2(model_id=0, config=fake_config) == 42.0

