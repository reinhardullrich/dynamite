from pathlib import Path
import shutil
from types import SimpleNamespace

import numpy as np
import pytest

from conftest import REPO_ROOT
from dynamite import model as dyn_model
from dynamite import orblib_api


class FakeLegacyOrbitLibrary:
    instances = []

    def __init__(self, config=None, mod_dir=None, parset=None):
        self.config = config
        self.mod_dir = mod_dir
        self.parset = parset
        self.calls = []
        self.LegacyWeightSolver = False
        FakeLegacyOrbitLibrary.instances.append(self)

    def get_orblib(self):
        self.calls.append(("get_orblib", None))

    def read_losvd_histograms(self, pops=False):
        self.calls.append(("read_losvd_histograms", pops))
        if pops:
            self.pops_projected_masses = [np.array([[9.0]])]
        else:
            self.losvd_histograms = [SimpleNamespace(y=np.ones((2, 3, 4)))]
            self.intrinsic_masses = np.ones((2, 5, 6, 7))
            self.projected_masses = [np.ones((2, 4))]
            self.n_orbs = 2

    def read_orbit_intrinsic_moments(self, cache=True):
        self.calls.append(("read_orbit_intrinsic_moments", cache))
        return np.ones((2, 3, 4, 5, 16)), [np.arange(3), np.arange(4)]

    def read_orbit_property_file(self):
        self.calls.append(("read_orbit_property_file", None))
        self.orb_properties = {"Lz": np.array([1.0])}


def reset_fake_legacy():
    FakeLegacyOrbitLibrary.instances = []


def copy_orblib_fixture_workspace(tmp_path):
    source = REPO_ROOT / "tests" / "fixtures" / "orblib_losvd"
    target = tmp_path / "orblib_losvd"
    shutil.copytree(
        source,
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


def make_fixture_orbit_library(workspace, monkeypatch):
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
    orbit_library = dyn.orblib.LegacyOrbitLibrary(
        config=config,
        mod_dir=model.directory_noml,
        parset=parset,
    )
    return model, orbit_library


def test_orbit_library_request_from_model_uses_model_context():
    model = SimpleNamespace(
        config=SimpleNamespace(name="config"),
        parset={"ml": 1.5},
        directory_noml="/tmp/model/",
    )

    request = orblib_api.OrbitLibraryRequest.from_model(
        model,
        include_populations=True,
        include_intrinsic_moments=True,
    )

    assert request.config is model.config
    assert request.parset == {"ml": 1.5}
    assert request.mod_dir == Path("/tmp/model")
    assert request.backend == "fortran_shared_library"
    assert request.include_populations is True
    assert request.include_intrinsic_moments is True


def test_shared_backend_collects_python_readable_outputs_without_generation(
    monkeypatch,
):
    reset_fake_legacy()
    monkeypatch.setattr(
        orblib_api.legacy_orblib,
        "LegacyOrbitLibrary",
        FakeLegacyOrbitLibrary,
    )
    request = orblib_api.OrbitLibraryRequest(
        config=SimpleNamespace(name="config"),
        parset={"ml": 2.0},
        mod_dir=Path("/tmp/model"),
        generate_if_missing=False,
        include_populations=True,
        include_intrinsic_moments=True,
        include_orbit_properties=True,
        cache_intrinsic_moments=False,
    )

    result = orblib_api.run_orbit_library(request)

    assert len(FakeLegacyOrbitLibrary.instances) == 1
    legacy = FakeLegacyOrbitLibrary.instances[0]
    assert legacy.config is request.config
    assert legacy.mod_dir == "/tmp/model/"
    assert legacy.parset == {"ml": 2.0}
    assert legacy.calls == [
        ("read_losvd_histograms", False),
        ("read_losvd_histograms", True),
        ("read_orbit_intrinsic_moments", False),
        ("read_orbit_property_file", None),
    ]
    assert result.backend == "fortran_shared_library"
    assert result.n_orbs == 2
    assert result.losvd_histograms[0].y.shape == (2, 3, 4)
    assert result.intrinsic_masses.shape == (2, 5, 6, 7)
    assert result.projected_masses[0].shape == (2, 4)
    assert result.pops_projected_masses[0].shape == (1, 1)
    assert result.intrinsic_moments.shape == (2, 3, 4, 5, 16)
    assert result.intrinsic_grid[0].tolist() == [0, 1, 2]
    assert result.orbit_properties["Lz"].tolist() == [1.0]


def test_shared_backend_can_read_existing_outputs_without_generation(
    monkeypatch,
):
    reset_fake_legacy()
    monkeypatch.setattr(
        orblib_api.legacy_orblib,
        "LegacyOrbitLibrary",
        FakeLegacyOrbitLibrary,
    )
    request = orblib_api.OrbitLibraryRequest(
        config=SimpleNamespace(name="config"),
        parset={},
        mod_dir=Path("/tmp/model"),
        generate_if_missing=False,
    )

    result = orblib_api.run_orbit_library(request)

    legacy = FakeLegacyOrbitLibrary.instances[0]
    assert legacy.calls == [("read_losvd_histograms", False)]
    assert result.n_orbs == 2


def test_shared_library_backend_requires_compiled_library(monkeypatch, tmp_path):
    reset_fake_legacy()
    monkeypatch.setattr(
        orblib_api.legacy_orblib,
        "LegacyOrbitLibrary",
        FakeLegacyOrbitLibrary,
    )
    request = orblib_api.OrbitLibraryRequest(
        config=SimpleNamespace(name="config"),
        parset={},
        mod_dir=tmp_path / "model",
        backend="fortran_shared_library",
        include_losvd_histograms=False,
    )
    backend = orblib_api.SharedLibraryFortranOrbitBackend(
        library_path=tmp_path / "missing.so",
    )

    with pytest.raises(FileNotFoundError, match="make -C orblib_fortran shared"):
        orblib_api.run_orbit_library(request, backend=backend)


def test_shared_library_backend_can_read_existing_outputs_without_library(
    monkeypatch,
):
    reset_fake_legacy()
    monkeypatch.setattr(
        orblib_api.legacy_orblib,
        "LegacyOrbitLibrary",
        FakeLegacyOrbitLibrary,
    )
    request = orblib_api.OrbitLibraryRequest(
        config=SimpleNamespace(name="config"),
        parset={},
        mod_dir=Path("/tmp/model"),
        generate_if_missing=False,
    )
    backend = orblib_api.SharedLibraryFortranOrbitBackend(
        library_path=Path("/does/not/exist.so"),
    )

    result = orblib_api.run_orbit_library(request, backend=backend)

    assert result.backend == "fortran_shared_library"
    assert result.n_orbs == 2
    legacy = FakeLegacyOrbitLibrary.instances[0]
    assert legacy.calls == [("read_losvd_histograms", False)]


def test_cpp_backend_can_read_existing_outputs_without_library(monkeypatch):
    reset_fake_legacy()
    monkeypatch.setattr(
        orblib_api.legacy_orblib,
        "LegacyOrbitLibrary",
        FakeLegacyOrbitLibrary,
    )
    request = orblib_api.OrbitLibraryRequest(
        config=SimpleNamespace(name="config"),
        parset={},
        mod_dir=Path("/tmp/model"),
        backend="cpp_shared_library",
        generate_if_missing=False,
    )
    backend = orblib_api.SharedLibraryCppOrbitBackend(
        library_path=Path("/does/not/exist.so"),
    )

    result = orblib_api.run_orbit_library(request, backend=backend)

    assert result.backend == "cpp_shared_library"
    assert result.n_orbs == 2
    legacy = FakeLegacyOrbitLibrary.instances[0]
    assert legacy.calls == [("read_losvd_histograms", False)]


def test_cpp_library_backend_requires_compiled_library(monkeypatch, tmp_path):
    reset_fake_legacy()
    monkeypatch.setattr(
        orblib_api.legacy_orblib,
        "LegacyOrbitLibrary",
        FakeLegacyOrbitLibrary,
    )
    request = orblib_api.OrbitLibraryRequest(
        config=SimpleNamespace(name="config"),
        parset={},
        mod_dir=tmp_path / "model",
        backend="cpp_shared_library",
        include_losvd_histograms=False,
    )
    backend = orblib_api.SharedLibraryCppOrbitBackend(
        library_path=tmp_path / "missing.so",
    )

    with pytest.raises(FileNotFoundError, match="make -C orblib_cpp shared"):
        orblib_api.run_orbit_library(request, backend=backend)


def test_model_run_orblib_api_uses_public_request(monkeypatch):
    captured = {}

    def fake_run_orbit_library(request):
        captured["request"] = request
        return "api-result"

    monkeypatch.setattr(orblib_api, "run_orbit_library", fake_run_orbit_library)
    model = dyn_model.Model.__new__(dyn_model.Model)
    model.config = SimpleNamespace(name="config")
    model.parset = {"ml": 3.0}
    model.directory_noml = "/tmp/model/"

    result = model.run_orblib_api(
        include_losvd_histograms=False,
        include_intrinsic_moments=True,
    )

    assert result == "api-result"
    request = captured["request"]
    assert request.config is model.config
    assert request.parset == {"ml": 3.0}
    assert request.mod_dir == Path("/tmp/model")
    assert request.include_losvd_histograms is False
    assert request.include_intrinsic_moments is True


def test_orbitstart_memory_inputs_extract_structured_payload(tmp_path, monkeypatch):
    workspace = copy_orblib_fixture_workspace(tmp_path)
    model, orbit_library = make_fixture_orbit_library(workspace, monkeypatch)

    inputs = orblib_api._orbitstart_memory_inputs(orbit_library)

    assert inputs["ngauss"] == 6
    assert inputs["surf_pc"].shape == (6,)
    assert inputs["sigobs_arcsec"].shape == (6,)
    assert inputs["qobs"].shape == (6,)
    assert inputs["psi_obs"].shape == (6,)
    assert inputs["nener"] == 2
    assert inputs["ni2"] == 4
    assert inputs["ni3"] == 3
    assert inputs["orbit_dithering"] == 1
    assert inputs["max_rows"] == 24
    assert inputs["dm_profile_type"] == 1
    assert inputs["n_dmparam"] == 2
    assert not (Path(model.directory_noml) / "infil" / "parameters_pot.in").exists()
    assert not (Path(model.directory_noml) / "infil" / "orbstart.in").exists()


def test_legacy_parameter_pot_precision_matches_historical_writer():
    inputs = {
        "surf_pc": np.array([1.234, 9.876], dtype=np.float64),
        "sigobs_arcsec": np.array([1.234567, 9.876543], dtype=np.float64),
        "qobs": np.array([0.987654, 0.123456], dtype=np.float64),
        "psi_obs": np.array([12.345, -67.895], dtype=np.float64),
        "theta": 82.44430885929485,
        "phi": 84.24511087677352,
        "psi": 90.02148153970481,
        "unchanged": "value",
    }

    quantized = orblib_api._legacy_parameter_pot_precision(inputs)

    assert quantized["surf_pc"].tolist() == [1.23, 9.88]
    assert quantized["sigobs_arcsec"].tolist() == [1.23457, 9.87654]
    assert quantized["qobs"].tolist() == [0.98765, 0.12346]
    assert quantized["psi_obs"].tolist() == [12.35, -67.89]
    assert quantized["theta"] == 82.444308859
    assert quantized["phi"] == 84.245110877
    assert quantized["psi"] == 90.02148154
    assert quantized["unchanged"] == "value"


def test_direct_orblib_inputs_extract_structured_payload(tmp_path, monkeypatch):
    workspace = copy_orblib_fixture_workspace(tmp_path)
    _model, orbit_library = make_fixture_orbit_library(workspace, monkeypatch)

    inputs = orblib_api._direct_orblib_inputs(orbit_library)

    assert inputs["orbital_periods"] == 200.0
    assert inputs["sampling"] == 50000
    assert inputs["starting_orbit"] == 1
    assert inputs["number_orbits"] == -1
    assert inputs["psf_count"] == 1
    assert inputs["max_psf_gauss"] == 1
    assert inputs["psf_kind"].tolist() == [1]
    assert inputs["psf_weight"].shape == (1, 1)
    assert inputs["psf_sigma"].shape == (1, 1)
    assert inputs["aperture_count"] == 1
    assert inputs["ap_begin"].shape == (1, 2)
    assert inputs["ap_size"].shape == (1, 2)
    assert inputs["ap_rot"].tolist() == [-36.0]
    assert inputs["ap_binx"].tolist() == [58]
    assert inputs["ap_biny"].tolist() == [52]
    assert inputs["ap_psf"].tolist() == [1]
    assert inputs["ap_hist_dim"].tolist() == [1]
    assert inputs["hist_width"].tolist() == [2719.8215332031]
    assert inputs["hist_center"].tolist() == [0.0]
    assert inputs["hist_bins"].tolist() == [203]
    assert inputs["max_bin_size"] == 3016
    assert inputs["bin_size"].tolist() == [3016]
    assert inputs["bin_order"].shape == (3016, 1)


@pytest.mark.orblib_cpp
def test_cpp_orbitstart_backend_reports_not_implemented_status(
    tmp_path,
    monkeypatch,
):
    workspace = copy_orblib_fixture_workspace(tmp_path)
    _model, orbit_library = make_fixture_orbit_library(workspace, monkeypatch)

    backend = orblib_api.SharedLibraryCppOrbitBackend()

    with pytest.raises(
        RuntimeError,
        match="orblib_cpp_api_run_orbitstart_memory failed with status -100",
    ):
        backend.run_orbitstart_memory(orbit_library)


@pytest.mark.slow
@pytest.mark.orblib_fortran
def test_shared_library_orbitstart_memory_avoids_orbitstart_files(
    tmp_path,
    monkeypatch,
):
    workspace = copy_orblib_fixture_workspace(tmp_path)
    model, orbit_library = make_fixture_orbit_library(workspace, monkeypatch)

    backend = orblib_api.SharedLibraryFortranOrbitBackend(
        isolate_fortran_calls=False,
    )
    result = backend.run_orbitstart_memory(orbit_library)

    assert result.begin_values.shape == (24, 9)
    assert result.beginbox_values.shape == (24, 9)
    assert result.begin_noreg.shape == (24,)
    assert result.beginbox_noreg.shape == (24,)
    assert np.all(np.isfinite(result.begin_values))
    assert np.all(np.isfinite(result.beginbox_values))
    assert not (Path(model.directory_noml) / "infil" / "orbstart.in").exists()
    assert not (Path(model.directory_noml) / "datfil" / "begin.dat").exists()
    assert not (Path(model.directory_noml) / "datfil" / "beginbox.dat").exists()
