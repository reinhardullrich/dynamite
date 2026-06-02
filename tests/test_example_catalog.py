import json

import pytest
import yaml

from conftest import REPO_ROOT


EXTRACTED_PYTHON_EXAMPLE_SNIPPETS = {
    "external_chi2": """
class Chi2Ext:
    def __init__(self, arg1, arg2):
        self.arg1 = arg1
        self.arg2 = arg2

    def chi2(self, model_id, config):
        system = config.system
        system_components = [c.name for c in system.cmp_list]
        parset = dict(config.all_models.get_parset_from_row(row_id=model_id))
        ml_vscale = config.all_models.get_model_velocity_scaling_factor(
            model_id=model_id,
        )
        assert system_components
        assert parset
        assert ml_vscale > 0
        return 42.0
""",
    "different_dark_halos_workflow": """
def run_user_test(dyn):
    c = dyn.config_reader.Configuration(
        'dif_dm_halos_config.yaml',
        reset_logging=True,
        reset_existing_output=True,
    )
    dyn.model_iterator.ModelIterator(c)
    return c.all_models.table
""",
    "random_generator_workflow": """
def run_random_number_test(myrand, ran_seed=-4242, n_ran=10):
    rng = myrand.MyRand(ran_seed)
    return [rng.ran1() for _ in range(n_ran)]
""",
    "data_prep_workflow": """
def run_data_prep(create_kin_input, read_atlas3d, gh_factory):
    create_kin_input('NGC6278', 'califa.fits', 'out/', expr='', fit_PA=True,
                     kin_input='CALIFA')
    read_atlas3d(['cube.fits', 'kin.fits'])
    gh_factory().add_psf_to_datafile(
        sigma=[1.06],
        weight=[1.0],
        datafile='out/gauss_hermite_kins.ecsv',
    )
""",
    "bar_workflow": """
def run_user_test(dyn):
    c = dyn.config_reader.Configuration(
        'bartest.yaml',
        reset_logging=True,
        user_logfile='bartest',
        reset_existing_output=True,
    )
    dyn.model_iterator.ModelIterator(c)
    return c
""",
    "missing_data_prep_import_smoke": """
def run_data_prep_smoke(data_prep_test):
    data_prep_test.data_prep_function_test()
    t_none = data_prep_test.TestClass()
    t_text = data_prep_test.TestClass('Vader')
    t_none.printout()
    t_text.printout()
""",
    "decomposition_workflow": """
def run_decomposition(dyn):
    c = dyn.config_reader.Configuration(
        'user_test_config_ml.yaml',
        reset_logging=True,
        user_logfile='test_decomp',
        reset_existing_output=True,
    )
    dyn.model_iterator.ModelIterator(c)
    decomp = dyn.analysis.Decomposition(
        config=c,
        names='bulgedisk',
        cache=True,
        comps_weights=True,
    )
    return decomp
""",
    "nnls_workflow": """
def run_user_test(dyn):
    c = dyn.config_reader.Configuration(
        'user_test_config_ml.yaml',
        reset_logging=True,
        user_logfile='test_nnls',
        reset_existing_output=True,
    )
    dyn.model_iterator.ModelIterator(c)
    return c.all_models.table
""",
    "orbit_losvd_workflow": """
def run_orbit_losvd_test(dyn):
    c = dyn.config_reader.Configuration(
        'user_test_config.yaml',
        reset_logging=False,
        reset_existing_output=True,
    )
    parset = c.parspace.get_parset()
    model = dyn.model.Model(config=c, parset=parset)
    model.setup_directories()
    orbit_library = model.get_orblib()
    orbit_library.read_losvd_histograms()
    return orbit_library.losvd_histograms
""",
    "legacy_vs_python_nnls_workflow": """
def compare_weight_solvers(np, legacy_weights, python_weights):
    return np.allclose(legacy_weights, python_weights, rtol=1e-10, atol=1e-6)
""",
    "slurm_local_workflow": """
def run_user_test(dyn):
    c = dyn.config_reader.Configuration('test_slurm_config.yaml')
    c.remove_existing_orblibs()
    c.remove_existing_all_models_file()
    dyn.model_iterator.ModelIterator(c)
    return c.all_models.get_mods_within_chi2_thresh(delta=300000)
""",
}

EXTRACTED_SHELL_EXAMPLES = {
    "run_all": "for script in *.py; do python \"$script\" > \"output_${script}.txt\"; done",
    "test_all": "python test_nnls.py",
    "test_notebooks": "for n in *.ipynb; do jupyter execute \"$n\"; done",
}

EXTRACTED_CONFIGS = [
    {
        "name": "bar",
        "orblib": {"nE": 10, "nI2": 7, "nI3": 5, "random_seed": 4242},
        "weight_solver": {"type": "NNLS", "nnls_solver": "scipy"},
        "n_max_mods": 3,
    },
    {
        "name": "bayes_losvd",
        "orblib": {"nE": 8, "nI2": 6, "nI3": 5, "random_seed": 4242},
        "weight_solver": {"type": "NNLS", "nnls_solver": "scipy"},
        "n_max_mods": 1,
    },
    {
        "name": "different_dark_halos",
        "orblib": {"nE": 6, "nI2": 5, "nI3": 4},
        "weight_solver": {"type": "NNLS", "nnls_solver": "scipy"},
        "n_max_mods": 3,
    },
    {
        "name": "legacy_reimplementation",
        "orblib": {"nE": 6, "nI2": 4, "nI3": 4, "random_seed": 4242},
        "weight_solver": {"type": "NNLS", "nnls_solver": "scipy"},
        "n_max_mods": 10,
    },
    {
        "name": "python_reimplementation",
        "orblib": {"nE": 6, "nI2": 4, "nI3": 4, "random_seed": 4242},
        "weight_solver": {"type": "NNLS", "nnls_solver": "scipy"},
        "n_max_mods": 10,
    },
    {
        "name": "slurm_local",
        "orblib": {"nE": 2, "nI2": 4, "nI3": 3, "random_seed": 0},
        "weight_solver": {"type": "NNLS", "nnls_solver": "scipy"},
        "n_max_mods": 5,
    },
    {
        "name": "ml_grid",
        "orblib": {"nE": 6, "nI2": 5, "nI3": 4, "random_seed": 4242},
        "weight_solver": {"type": "NNLS", "nnls_solver": "scipy"},
        "n_max_mods": 3,
    },
    {
        "name": "ml_gas",
        "orblib": {"nE": 6, "nI2": 5, "nI3": 4, "random_seed": 4242},
        "weight_solver": {"type": "NNLS", "nnls_solver": "scipy"},
        "n_max_mods": 3,
    },
    {
        "name": "specific_models",
        "orblib": {"nE": 6, "nI2": 5, "nI3": 4, "random_seed": 4242},
        "weight_solver": {"type": "NNLS", "nnls_solver": "scipy"},
        "n_max_mods": 3,
    },
]

NOTEBOOK_EXAMPLE_NAMES = [
    "rmax_vs_zmax",
    "bayes_losvd_workflow",
    "orbit_densities",
    "data_prep_for_gauss_hermite",
    "quickstart",
    "model_iterations_and_plots",
    "bayes_losvd_tutorial",
    "parameter_space",
    "orbits_and_weights",
    "orbital_distributions",
    "coloring",
]

DOC_TUTORIAL_CONFIGS = [
    "docs/tutorial_notebooks/FCC167_config.yaml",
    "docs/tutorial_notebooks/NGC4550_config.yaml",
    "docs/tutorial_notebooks/NGC6278_config.yaml",
    "docs/tutorial_notebooks/NGC6278_config_single.yaml",
]

DOC_TUTORIAL_NOTEBOOKS = [
    "docs/tutorial_notebooks/1_data_prep_for_gauss_hermite.ipynb",
    "docs/tutorial_notebooks/2_quickstart.ipynb",
    "docs/tutorial_notebooks/3_model_iterations_and_plots.ipynb",
    "docs/tutorial_notebooks/4_BayesLOSVD.ipynb",
    "docs/tutorial_notebooks/5_parameter_space.ipynb",
    "docs/tutorial_notebooks/6_orbits_and_weights.ipynb",
    "docs/tutorial_notebooks/7_orbital_distributions.ipynb",
    "docs/tutorial_notebooks/8_coloring.ipynb",
]


@pytest.mark.parametrize("name, source", EXTRACTED_PYTHON_EXAMPLE_SNIPPETS.items())
def test_extracted_python_example_snippet_compiles(name, source):
    compile(source, f"<extracted example {name}>", "exec")


@pytest.mark.parametrize("name, source", EXTRACTED_SHELL_EXAMPLES.items())
def test_extracted_shell_example_intent_is_represented(name, source):
    assert source.strip()
    assert "python" in source or "jupyter" in source


@pytest.mark.parametrize("config", EXTRACTED_CONFIGS)
def test_extracted_example_config_settings_are_valid(config):
    weight_solver = config["weight_solver"]
    assert weight_solver["type"] == "NNLS"
    assert weight_solver["nnls_solver"] in {"scipy", "cvxopt"}

    orblib = config["orblib"]
    assert orblib["nE"] > 0
    assert orblib["nI2"] >= 4
    assert orblib["nI3"] > 0
    assert config["n_max_mods"] > 0


def test_all_extracted_historical_examples_are_represented():
    assert set(EXTRACTED_PYTHON_EXAMPLE_SNIPPETS) == {
        "external_chi2",
        "different_dark_halos_workflow",
        "random_generator_workflow",
        "data_prep_workflow",
        "bar_workflow",
        "missing_data_prep_import_smoke",
        "decomposition_workflow",
        "nnls_workflow",
        "orbit_losvd_workflow",
        "legacy_vs_python_nnls_workflow",
        "slurm_local_workflow",
    }
    assert len(EXTRACTED_CONFIGS) == 9
    assert len(NOTEBOOK_EXAMPLE_NAMES) == 11


def test_external_chi2_example_returns_documented_constant():
    from types import SimpleNamespace

    namespace = {}
    exec(EXTRACTED_PYTHON_EXAMPLE_SNIPPETS["external_chi2"], namespace)

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

    chi2_ext = namespace["Chi2Ext"]("arg1", "arg2")
    assert chi2_ext.chi2(model_id=0, config=fake_config) == 42.0


@pytest.mark.parametrize("relative_path", DOC_TUTORIAL_CONFIGS)
def test_documented_tutorial_yaml_config_has_required_sections(relative_path):
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


@pytest.mark.parametrize("relative_path", DOC_TUTORIAL_NOTEBOOKS)
def test_documented_tutorial_notebook_is_valid_ipynb(relative_path):
    path = REPO_ROOT / relative_path
    with path.open() as handle:
        notebook = json.load(handle)

    assert notebook["nbformat"] >= 4
    assert isinstance(notebook.get("cells"), list)
    assert notebook["cells"]
