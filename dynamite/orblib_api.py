"""Python-facing API for compiled orbit-library backends.

This module is the stable Python boundary for orbit-library generation.  Python
passes model, orbit-start, PSF, aperture, and binning data directly to the
compiled shared-library backend; the active backend does not generate Fortran
input files.
"""

from __future__ import annotations

import bz2
import ctypes
import logging
import multiprocessing as mp
import os
import queue
import shutil
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal, Mapping, Protocol

import numpy as np

from dynamite import physical_system as physys
from dynamite import orblib as legacy_orblib


BackendName = Literal["fortran_shared_library", "cpp_shared_library"]
SHARED_LIBRARY_ABI_VERSION = 2
CPP_SHARED_LIBRARY_ABI_VERSION = 1
CPP_STATUS_NOT_IMPLEMENTED = -100


def _default_shared_library_path() -> Path:
    return (
        Path(__file__).resolve().parents[1]
        / "orblib_fortran"
        / "build"
        / "lib"
        / "liborblib_fortran.so"
    )


def _default_cpp_shared_library_path() -> Path:
    return (
        Path(__file__).resolve().parents[1]
        / "orblib_cpp"
        / "build"
        / "lib"
        / "liborblib_cpp.so"
    )


@dataclass(frozen=True)
class OrbitLibraryRequest:
    """Inputs needed to generate and read an orbit library.

    Parameters
    ----------
    config
        DYNAMITE configuration object containing the physical system, orbit
        settings, and multiprocessing settings.
    parset
        Parameter set for the model being evaluated.
    mod_dir
        Model directory containing the Fortran ``datfil/`` outputs.  The direct
        shared-library backend does not create or read Fortran ``infil/``
        inputs.
    backend
        Backend implementation to use. ``fortran_shared_library`` calls the
        shared object built by ``make -C orblib_fortran shared``.
        ``cpp_shared_library`` is the experimental C++ port backend built by
        ``make -C orblib_cpp shared``.
    generate_if_missing
        If True, generate the orbit library when the model output files are
        missing.  If False, only read existing outputs.
    include_losvd_histograms
        Read LOSVD histograms and intrinsic/projected masses into the result.
    include_populations
        Read population projected masses into the result.
    include_intrinsic_moments
        Read intrinsic moment grids into the result.
    include_orbit_properties
        Read orbit classification/property tables into the result.
    cache_intrinsic_moments
        Allow the legacy reader to use its compressed intrinsic-moment cache.
    """

    config: Any
    parset: Mapping[str, Any]
    mod_dir: Path
    backend: BackendName = "fortran_shared_library"
    generate_if_missing: bool = True
    include_losvd_histograms: bool = True
    include_populations: bool = False
    include_intrinsic_moments: bool = False
    include_orbit_properties: bool = False
    cache_intrinsic_moments: bool = True

    @classmethod
    def from_model(
        cls,
        model: Any,
        *,
        backend: BackendName = "fortran_shared_library",
        generate_if_missing: bool = True,
        include_losvd_histograms: bool = True,
        include_populations: bool = False,
        include_intrinsic_moments: bool = False,
        include_orbit_properties: bool = False,
        cache_intrinsic_moments: bool = True,
    ) -> "OrbitLibraryRequest":
        """Build a request from a DYNAMITE ``Model`` instance."""

        return cls(
            config=model.config,
            parset=model.parset,
            mod_dir=Path(model.directory_noml),
            backend=backend,
            generate_if_missing=generate_if_missing,
            include_losvd_histograms=include_losvd_histograms,
            include_populations=include_populations,
            include_intrinsic_moments=include_intrinsic_moments,
            include_orbit_properties=include_orbit_properties,
            cache_intrinsic_moments=cache_intrinsic_moments,
        )


@dataclass(frozen=True)
class OrbitLibraryResult:
    """Python-readable outputs returned by an orbit-library backend."""

    backend: BackendName
    losvd_histograms: list[Any] = field(default_factory=list)
    intrinsic_masses: np.ndarray | None = None
    projected_masses: list[np.ndarray] = field(default_factory=list)
    pops_projected_masses: list[np.ndarray] = field(default_factory=list)
    intrinsic_moments: np.ndarray | None = None
    intrinsic_grid: list[np.ndarray] | None = None
    orbit_properties: Any | None = None
    n_orbs: int = 0


@dataclass(frozen=True)
class OrbitStartMemoryResult:
    """Orbit-start output returned by the direct-input shared-library ABI."""

    begin_values: np.ndarray
    begin_noreg: np.ndarray
    beginbox_values: np.ndarray
    beginbox_noreg: np.ndarray

    @property
    def rows_written(self) -> int:
        return int(self.begin_values.shape[0])

    @property
    def box_rows_written(self) -> int:
        return int(self.beginbox_values.shape[0])


class OrbitLibraryBackend(Protocol):
    """Backend interface for orbit-library generation."""

    name: BackendName

    def run(self, request: OrbitLibraryRequest) -> OrbitLibraryResult:
        """Generate/read an orbit library and return Python-readable outputs."""
        ...


class SharedLibraryFortranOrbitBackend:
    """Backend using the Fortran shared library with direct Python inputs."""

    name: BackendName = "fortran_shared_library"

    def __init__(
        self,
        library_path: Path | None = None,
        *,
        isolate_fortran_calls: bool = True,
    ):
        self.library_path = Path(library_path or _default_shared_library_path())
        self.isolate_fortran_calls = isolate_fortran_calls
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    def run(self, request: OrbitLibraryRequest) -> OrbitLibraryResult:
        orbit_library = _make_legacy_orbit_library(request)
        if request.generate_if_missing:
            self.generate_orbit_library(orbit_library)
        return _collect_legacy_outputs(orbit_library, request, self.name)

    def generate_orbit_library(self, orbit_library: Any) -> None:
        mod_dir = Path(orbit_library.mod_dir)
        done_file = mod_dir / "datfil" / "tube_box_done"
        if done_file.is_file():
            return
        if orbit_library.LegacyWeightSolver:
            raise NotImplementedError(
                "LegacyWeightSolver is archived and no longer supported by "
                "the active orbit-library API. Use NNLS instead."
            )
        self._require_library()
        (mod_dir / "datfil").mkdir(parents=True, exist_ok=True)

        orbit_start = self.run_orbitstart_memory(orbit_library)

        if orbit_library.orblibs_in_parallel:
            self.logger.info(
                "fortran_shared_library backend runs tube and box libraries "
                "sequentially; the Fortran shared library is isolated per call."
            )
        self._run_orbit_library_part_direct(
            mod_dir,
            "orblib",
            orbit_library,
            orbit_start.begin_values,
            orbit_start.begin_noreg,
        )
        self._run_orbit_library_part_direct(
            mod_dir,
            "orblibbox",
            orbit_library,
            orbit_start.beginbox_values,
            orbit_start.beginbox_noreg,
        )

        self._calculate_python_intrinsic_masses(orbit_library)
        tube_done = (mod_dir / "datfil" / "tube_done").is_file()
        box_done = (mod_dir / "datfil" / "box_done").is_file()
        if tube_done and box_done:
            done_file.touch()

    def run_orbitstart_memory(self, orbit_library: Any) -> OrbitStartMemoryResult:
        """Run orbit-start through the direct-input ABI and return arrays.

        This bypasses ``orbstart.in`` and ``parameters_pot.in`` by passing
        typed arrays/scalars to Fortran.
        """

        self._require_library()
        if self.isolate_fortran_calls:
            return _call_orbitstart_memory_in_worker(
                self.library_path,
                orbit_library,
                Path(orbit_library.mod_dir),
            )
        return _call_orbitstart_memory_function(self.library_path, orbit_library)

    def _run_orbit_library_part_direct(
        self,
        mod_dir: Path,
        fileroot: str,
        orbit_library: Any,
        begin_values: np.ndarray,
        begin_noreg: np.ndarray,
    ) -> None:
        datfil = mod_dir / "datfil"
        done_file = datfil / ("tube_done" if fileroot == "orblib" else "box_done")
        self._remove_orbit_library_outputs(datfil, fileroot)
        model_inputs = _orbitstart_memory_inputs(orbit_library)
        library_inputs = _direct_orblib_inputs(orbit_library)
        if self.isolate_fortran_calls:
            _call_orblib_direct_in_worker(
                self.library_path,
                mod_dir,
                model_inputs,
                library_inputs,
                fileroot,
                begin_values,
                begin_noreg,
            )
        else:
            with _working_directory(mod_dir):
                _call_orblib_direct_function(
                    self.library_path,
                    model_inputs,
                    library_inputs,
                    fileroot,
                    begin_values,
                    begin_noreg,
                )
        for suffix in ("qgrid", "pops", "losvd_hist"):
            self._compress_fortran_output(datfil / f"{fileroot}_{suffix}.dat")
        done_file.touch()

    def _remove_orbit_library_outputs(self, datfil: Path, fileroot: str) -> None:
        for suffix in ("qgrid", "pops", "losvd_hist"):
            for extension in (".dat", ".dat.bz2", ".dat.staging.bz2"):
                path = datfil / f"{fileroot}_{suffix}{extension}"
                if path.exists():
                    path.unlink()
        tmp_file = datfil / f"{fileroot}_qgrid.dat.tmp"
        if tmp_file.exists():
            tmp_file.unlink()
        orbclass_file = datfil / f"{fileroot}.dat_orbclass.out"
        if orbclass_file.exists():
            orbclass_file.unlink()
        done_file = datfil / ("tube_done" if fileroot == "orblib" else "box_done")
        if done_file.exists():
            done_file.unlink()
        combined_done = datfil / "tube_box_done"
        if combined_done.exists():
            combined_done.unlink()

    def _compress_fortran_output(self, path: Path) -> None:
        if not path.exists():
            return
        compressed = path.with_name(path.name + ".bz2")
        staging = path.with_name(path.name + ".staging.bz2")
        with path.open("rb") as source, bz2.open(staging, "wb") as target:
            shutil.copyfileobj(source, target)
        os.replace(staging, compressed)
        path.unlink()

    def _calculate_python_intrinsic_masses(self, orbit_library: Any) -> None:
        model = orbit_library.config.all_models.get_model_from_parset(
            orbit_library.parset,
        )
        if orbit_library.system.is_bar_disk_system():
            stars = orbit_library.system.get_unique_bar_component()
            mge = stars.mge_lum_tot
            len_mge_bulge = len(stars.mge_lum.data)
            _ = mge.get_intrinsic_masses(
                model,
                len_mge_bulge=len_mge_bulge,
                parallel=False,
            )
        else:
            stars = orbit_library.system.get_unique_triaxial_visible_component()
            mge = stars.mge_lum
            _ = mge.get_intrinsic_masses(model, parallel=False)

    def _require_library(self) -> None:
        if not self.library_path.is_file():
            raise FileNotFoundError(
                f"Fortran shared library not found: {self.library_path}. "
                "Build it with `make -C orblib_fortran shared`."
            )


class SharedLibraryCppOrbitBackend:
    """Experimental backend using the C++ shared library port."""

    name: BackendName = "cpp_shared_library"

    def __init__(self, library_path: Path | None = None):
        self.library_path = Path(library_path or _default_cpp_shared_library_path())
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    def run(self, request: OrbitLibraryRequest) -> OrbitLibraryResult:
        orbit_library = _make_legacy_orbit_library(request)
        if request.generate_if_missing:
            self.generate_orbit_library(orbit_library)
        return _collect_legacy_outputs(orbit_library, request, self.name)

    def generate_orbit_library(self, orbit_library: Any) -> None:
        mod_dir = Path(orbit_library.mod_dir)
        done_file = mod_dir / "datfil" / "tube_box_done"
        if done_file.is_file():
            return
        if orbit_library.LegacyWeightSolver:
            raise NotImplementedError(
                "LegacyWeightSolver is archived and no longer supported by "
                "the active orbit-library API. Use NNLS instead."
            )
        self._require_library()
        (mod_dir / "datfil").mkdir(parents=True, exist_ok=True)

        orbit_start = self.run_orbitstart_memory(orbit_library)

        if orbit_library.orblibs_in_parallel:
            self.logger.info(
                "cpp_shared_library backend runs tube and box libraries "
                "sequentially in the first full-generator implementation."
            )
        self._run_orbit_library_part_direct(
            mod_dir,
            "orblib",
            orbit_library,
            orbit_start.begin_values,
            orbit_start.begin_noreg,
        )
        self._run_orbit_library_part_direct(
            mod_dir,
            "orblibbox",
            orbit_library,
            orbit_start.beginbox_values,
            orbit_start.beginbox_noreg,
        )

        SharedLibraryFortranOrbitBackend._calculate_python_intrinsic_masses(
            self,
            orbit_library,
        )
        tube_done = (mod_dir / "datfil" / "tube_done").is_file()
        box_done = (mod_dir / "datfil" / "box_done").is_file()
        if tube_done and box_done:
            done_file.touch()

    def run_orbitstart_memory(self, orbit_library: Any) -> OrbitStartMemoryResult:
        self._require_library()
        return _call_orbitstart_memory_function(
            self.library_path,
            orbit_library,
            abi_function_name="orblib_cpp_api_abi_version",
            expected_abi_version=CPP_SHARED_LIBRARY_ABI_VERSION,
            backend_label="C++",
            orbitstart_function_name="orblib_cpp_api_run_orbitstart_memory",
        )

    def _run_orbit_library_part_direct(
        self,
        mod_dir: Path,
        fileroot: str,
        orbit_library: Any,
        begin_values: np.ndarray,
        begin_noreg: np.ndarray,
    ) -> None:
        datfil = mod_dir / "datfil"
        done_file = datfil / ("tube_done" if fileroot == "orblib" else "box_done")
        SharedLibraryFortranOrbitBackend._remove_orbit_library_outputs(
            self,
            datfil,
            fileroot,
        )
        model_inputs = _orbitstart_memory_inputs(orbit_library)
        library_inputs = _direct_orblib_inputs(orbit_library)
        with _working_directory(mod_dir):
            _call_orblib_direct_function(
                self.library_path,
                model_inputs,
                library_inputs,
                fileroot,
                begin_values,
                begin_noreg,
                abi_function_name="orblib_cpp_api_abi_version",
                expected_abi_version=CPP_SHARED_LIBRARY_ABI_VERSION,
                backend_label="C++",
                orblib_function_name="orblib_cpp_api_run_orblib_direct",
            )
        for suffix in ("qgrid", "pops", "losvd_hist"):
            SharedLibraryFortranOrbitBackend._compress_fortran_output(
                self,
                datfil / f"{fileroot}_{suffix}.dat",
            )
        done_file.touch()

    def _require_library(self) -> None:
        if not self.library_path.is_file():
            raise FileNotFoundError(
                f"C++ shared library not found: {self.library_path}. "
                "Build it with `make -C orblib_cpp shared`."
            )


def get_backend(name: BackendName) -> OrbitLibraryBackend:
    """Return the requested orbit-library backend."""

    if name == "fortran_shared_library":
        return SharedLibraryFortranOrbitBackend()
    if name == "cpp_shared_library":
        return SharedLibraryCppOrbitBackend()
    raise ValueError(f"Unknown orbit-library backend: {name!r}.")


def _legacy_directory_string(path: Path) -> str:
    """Return a directory string compatible with ``LegacyOrbitLibrary``."""

    value = str(path)
    if not value.endswith(os.sep):
        value += os.sep
    return value


def _make_legacy_orbit_library(request: OrbitLibraryRequest) -> Any:
    return legacy_orblib.LegacyOrbitLibrary(
        config=request.config,
        mod_dir=_legacy_directory_string(request.mod_dir),
        parset=request.parset,
    )


def _collect_legacy_outputs(
    orbit_library: Any,
    request: OrbitLibraryRequest,
    backend_name: BackendName,
) -> OrbitLibraryResult:
    losvd_histograms = []
    intrinsic_masses = None
    projected_masses = []
    pops_projected_masses = []
    intrinsic_moments = None
    intrinsic_grid = None
    orbit_properties = None
    n_orbs = 0

    if request.include_losvd_histograms:
        orbit_library.read_losvd_histograms(pops=False)
        losvd_histograms = list(orbit_library.losvd_histograms)
        intrinsic_masses = orbit_library.intrinsic_masses
        projected_masses = list(orbit_library.projected_masses)
        n_orbs = orbit_library.n_orbs

    if request.include_populations:
        orbit_library.read_losvd_histograms(pops=True)
        pops_projected_masses = list(orbit_library.pops_projected_masses)

    if request.include_intrinsic_moments:
        intrinsic_moments, intrinsic_grid = (
            orbit_library.read_orbit_intrinsic_moments(
                cache=request.cache_intrinsic_moments,
            )
        )

    if request.include_orbit_properties:
        orbit_library.read_orbit_property_file()
        orbit_properties = orbit_library.orb_properties

    return OrbitLibraryResult(
        backend=backend_name,
        losvd_histograms=losvd_histograms,
        intrinsic_masses=intrinsic_masses,
        projected_masses=projected_masses,
        pops_projected_masses=pops_projected_masses,
        intrinsic_moments=intrinsic_moments,
        intrinsic_grid=intrinsic_grid,
        orbit_properties=orbit_properties,
        n_orbs=n_orbs,
    )


@contextmanager
def _working_directory(path: Path):
    current = Path.cwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(current)


def _load_checked_shared_library(
    library_path: Path,
    *,
    abi_function_name: str = "orblib_api_abi_version",
    expected_abi_version: int = SHARED_LIBRARY_ABI_VERSION,
    backend_label: str = "Fortran",
) -> ctypes.CDLL:
    library = ctypes.CDLL(str(library_path))
    abi_version = getattr(library, abi_function_name)
    abi_version.argtypes = []
    abi_version.restype = ctypes.c_int
    version = abi_version()
    if version != expected_abi_version:
        raise RuntimeError(
            f"Unsupported {backend_label} shared-library ABI version {version}; "
            f"expected {expected_abi_version}."
        )
    return library


def _call_orblib_direct_in_worker(
    library_path: Path,
    cwd: Path,
    model_inputs: Mapping[str, Any],
    library_inputs: Mapping[str, Any],
    fileroot: str,
    begin_values: np.ndarray,
    begin_noreg: np.ndarray,
) -> None:
    context = mp.get_context()
    result_queue = context.Queue()
    process = context.Process(
        target=_orblib_direct_worker,
        args=(
            str(library_path),
            str(cwd),
            model_inputs,
            library_inputs,
            fileroot,
            begin_values,
            begin_noreg,
            result_queue,
        ),
    )
    process.start()
    process.join()
    if process.exitcode != 0:
        raise RuntimeError(
            "orblib_api_run_orblib_direct worker exited with code "
            f"{process.exitcode}."
        )
    try:
        kind, payload = result_queue.get_nowait()
    except queue.Empty as exc:
        raise RuntimeError(
            "orblib_api_run_orblib_direct worker returned no status."
        ) from exc
    if kind == "error":
        raise RuntimeError(payload)


def _orblib_direct_worker(
    library_path: str,
    cwd: str,
    model_inputs: Mapping[str, Any],
    library_inputs: Mapping[str, Any],
    fileroot: str,
    begin_values: np.ndarray,
    begin_noreg: np.ndarray,
    result_queue: Any,
) -> None:
    try:
        os.chdir(cwd)
        _call_orblib_direct_function(
            Path(library_path),
            model_inputs,
            library_inputs,
            fileroot,
            begin_values,
            begin_noreg,
        )
    except BaseException as exc:
        result_queue.put(("error", repr(exc)))
    else:
        result_queue.put(("ok", None))


def _call_orblib_direct_function(
    library_path: Path,
    model_inputs: Mapping[str, Any],
    library_inputs: Mapping[str, Any],
    fileroot: str,
    begin_values: np.ndarray,
    begin_noreg: np.ndarray,
    *,
    abi_function_name: str = "orblib_api_abi_version",
    expected_abi_version: int = SHARED_LIBRARY_ABI_VERSION,
    backend_label: str = "Fortran",
    orblib_function_name: str = "orblib_api_run_orblib_direct",
) -> None:
    begin_values_f = np.asfortranarray(begin_values, dtype=np.float64)
    begin_noreg_i = np.ascontiguousarray(begin_noreg, dtype=np.int32)
    if begin_values_f.ndim != 2 or begin_values_f.shape[1] != 9:
        raise ValueError("Direct orbit-start values must have shape (n, 9).")
    if begin_values_f.shape[0] != begin_noreg_i.shape[0]:
        raise ValueError("Direct orbit-start values and noreg flags differ.")

    library = _load_checked_shared_library(
        library_path,
        abi_function_name=abi_function_name,
        expected_abi_version=expected_abi_version,
        backend_label=backend_label,
    )
    function = getattr(library, orblib_function_name)
    double_p = ctypes.POINTER(ctypes.c_double)
    int_p = ctypes.POINTER(ctypes.c_int)
    function.argtypes = [
        ctypes.c_int,
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
        ctypes.c_double,
        ctypes.c_double,
        ctypes.c_int,
        ctypes.c_double,
        ctypes.c_double,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_int,
        double_p,
        ctypes.c_int,
        double_p,
        int_p,
        ctypes.c_double,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_double,
        ctypes.c_int,
        ctypes.c_int,
        int_p,
        double_p,
        double_p,
        ctypes.c_int,
        double_p,
        double_p,
        double_p,
        int_p,
        int_p,
        int_p,
        int_p,
        double_p,
        double_p,
        int_p,
        ctypes.c_int,
        int_p,
        int_p,
        int_p,
        ctypes.c_char_p,
        ctypes.c_char_p,
        ctypes.c_char_p,
        ctypes.c_char_p,
        ctypes.POINTER(ctypes.c_int),
    ]
    function.restype = None

    status = ctypes.c_int(-1)
    outputs = _direct_orblib_output_paths(fileroot)
    function(
        ctypes.c_int(model_inputs["random_seed"]),
        ctypes.c_int(model_inputs["ngauss"]),
        model_inputs["surf_pc"].ctypes.data_as(double_p),
        model_inputs["sigobs_arcsec"].ctypes.data_as(double_p),
        model_inputs["qobs"].ctypes.data_as(double_p),
        model_inputs["psi_obs"].ctypes.data_as(double_p),
        ctypes.c_double(model_inputs["distance"]),
        ctypes.c_double(model_inputs["theta"]),
        ctypes.c_double(model_inputs["phi"]),
        ctypes.c_double(model_inputs["psi"]),
        ctypes.c_double(model_inputs["upsilon"]),
        ctypes.c_double(model_inputs["xmbh"]),
        ctypes.c_double(model_inputs["softl_arcsec"]),
        ctypes.c_int(model_inputs["nener"]),
        ctypes.c_double(model_inputs["rlogmin"]),
        ctypes.c_double(model_inputs["rlogmax"]),
        ctypes.c_int(model_inputs["ni2"]),
        ctypes.c_int(model_inputs["ni3"]),
        ctypes.c_int(model_inputs["orbit_dithering"]),
        ctypes.c_int(model_inputs["quad_nr"]),
        ctypes.c_int(model_inputs["quad_nth"]),
        ctypes.c_int(model_inputs["quad_nph"]),
        ctypes.c_int(model_inputs["dm_profile_type"]),
        ctypes.c_int(model_inputs["n_dmparam"]),
        model_inputs["dmparam"].ctypes.data_as(double_p),
        ctypes.c_int(begin_values_f.shape[0]),
        begin_values_f.ctypes.data_as(double_p),
        begin_noreg_i.ctypes.data_as(int_p),
        ctypes.c_double(library_inputs["orbital_periods"]),
        ctypes.c_int(library_inputs["sampling"]),
        ctypes.c_int(library_inputs["starting_orbit"]),
        ctypes.c_int(library_inputs["number_orbits"]),
        ctypes.c_double(library_inputs["accuracy"]),
        ctypes.c_int(library_inputs["psf_count"]),
        ctypes.c_int(library_inputs["max_psf_gauss"]),
        library_inputs["psf_kind"].ctypes.data_as(int_p),
        library_inputs["psf_weight"].ctypes.data_as(double_p),
        library_inputs["psf_sigma"].ctypes.data_as(double_p),
        ctypes.c_int(library_inputs["aperture_count"]),
        library_inputs["ap_begin"].ctypes.data_as(double_p),
        library_inputs["ap_size"].ctypes.data_as(double_p),
        library_inputs["ap_rot"].ctypes.data_as(double_p),
        library_inputs["ap_binx"].ctypes.data_as(int_p),
        library_inputs["ap_biny"].ctypes.data_as(int_p),
        library_inputs["ap_psf"].ctypes.data_as(int_p),
        library_inputs["ap_hist_dim"].ctypes.data_as(int_p),
        library_inputs["hist_width"].ctypes.data_as(double_p),
        library_inputs["hist_center"].ctypes.data_as(double_p),
        library_inputs["hist_bins"].ctypes.data_as(int_p),
        ctypes.c_int(library_inputs["max_bin_size"]),
        library_inputs["bin_type"].ctypes.data_as(int_p),
        library_inputs["bin_size"].ctypes.data_as(int_p),
        library_inputs["bin_order"].ctypes.data_as(int_p),
        os.fsencode(outputs["qgrid"]),
        os.fsencode(outputs["pops"]),
        os.fsencode(outputs["losvd"]),
        os.fsencode(outputs["orbclass"]),
        ctypes.byref(status),
    )
    if status.value != 0:
        raise RuntimeError(
            f"{orblib_function_name} failed with status "
            f"{status.value} for {fileroot}."
        )


def _direct_orblib_output_paths(fileroot: str) -> dict[str, str]:
    return {
        "qgrid": f"datfil/{fileroot}_qgrid.dat",
        "pops": f"datfil/{fileroot}_pops.dat",
        "losvd": f"datfil/{fileroot}_losvd_hist.dat",
        "orbclass": f"datfil/{fileroot}.dat_orbclass.out",
    }


def _direct_orblib_inputs(orbit_library: Any) -> dict[str, Any]:
    if orbit_library.system.is_bar_disk_system():
        raise NotImplementedError(
            "The direct-input orbit-library ABI currently supports only the "
            "non-bar triaxial path."
        )

    stars = orbit_library.system.get_unique_triaxial_visible_component()
    settings = orbit_library.settings
    kin_sets = list(stars.kinematic_data)
    pop_sets = [p for p in stars.population_data if p.kin_aper is None]
    psf_sets = kin_sets + pop_sets
    if not psf_sets:
        raise ValueError("At least one kinematic or population PSF is required.")

    psf_kind = np.ascontiguousarray(
        [len(data_set.PSF["sigma"]) for data_set in psf_sets],
        dtype=np.int32,
    )
    max_psf_gauss = int(psf_kind.max())
    psf_weight = np.zeros((max_psf_gauss, len(psf_sets)), dtype=np.float64, order="F")
    psf_sigma = np.zeros((max_psf_gauss, len(psf_sets)), dtype=np.float64, order="F")
    for i, data_set in enumerate(psf_sets):
        weights = np.asarray(data_set.PSF["weight"], dtype=np.float64)
        sigmas = np.asarray(data_set.PSF["sigma"], dtype=np.float64)
        if weights.shape != sigmas.shape:
            raise ValueError(f"PSF weight/sigma length mismatch for {data_set.name}.")
        psf_weight[: weights.size, i] = weights
        psf_sigma[: sigmas.size, i] = sigmas

    aperture_sets = kin_sets + pop_sets
    aperture_count = len(aperture_sets)
    ap_begin = np.zeros((aperture_count, 2), dtype=np.float64, order="F")
    ap_size = np.zeros((aperture_count, 2), dtype=np.float64, order="F")
    ap_rot = np.zeros(aperture_count, dtype=np.float64)
    ap_binx = np.zeros(aperture_count, dtype=np.int32)
    ap_biny = np.zeros(aperture_count, dtype=np.int32)
    ap_psf = np.zeros(aperture_count, dtype=np.int32)
    ap_hist_dim = np.zeros(aperture_count, dtype=np.int32)
    bin_type = np.ones(aperture_count, dtype=np.int32)
    bin_sizes: list[int] = []
    bin_orders: list[np.ndarray] = []

    input_dir = Path(orbit_library.in_dir)
    for i, data_set in enumerate(aperture_sets):
        aperture = _read_boxed_aperture(input_dir / data_set.aperturefile)
        ap_begin[i, :] = aperture["begin"]
        ap_size[i, :] = aperture["size"]
        ap_rot[i] = aperture["rotation"]
        ap_binx[i] = aperture["binx"]
        ap_biny[i] = aperture["biny"]
        if i < len(kin_sets):
            ap_psf[i] = i + 1
            ap_hist_dim[i] = 1
        else:
            ap_psf[i] = i + 1
            ap_hist_dim[i] = 0
        bin_order = _read_binning_order(input_dir / data_set.binfile)
        bin_sizes.append(int(bin_order.size))
        bin_orders.append(bin_order)

    max_bin_size = max(bin_sizes)
    bin_size = np.ascontiguousarray(bin_sizes, dtype=np.int32)
    bin_order = np.zeros((max_bin_size, aperture_count), dtype=np.int32, order="F")
    for i, order in enumerate(bin_orders):
        bin_order[: order.size, i] = order

    hist_width = np.zeros(len(psf_sets), dtype=np.float64)
    hist_center = np.zeros(len(psf_sets), dtype=np.float64)
    hist_bins = np.zeros(len(psf_sets), dtype=np.int32)
    for i, kin_i in enumerate(kin_sets):
        hist_width[i] = float(kin_i.hist_width)
        hist_center[i] = float(kin_i.hist_center)
        hist_bins[i] = int(kin_i.hist_bins)
    for offset, _pop_i in enumerate(pop_sets, start=len(kin_sets)):
        hist_width[offset] = 1.0
        hist_center[offset] = 0.0
        hist_bins[offset] = 1

    return {
        "orbital_periods": float(settings["orbital_periods"]),
        "sampling": int(settings["sampling"]),
        "starting_orbit": int(settings["starting_orbit"]),
        "number_orbits": int(settings["number_orbits"]),
        "accuracy": _fortran_float(settings["accuracy"]),
        "psf_count": len(psf_sets),
        "max_psf_gauss": max_psf_gauss,
        "psf_kind": psf_kind,
        "psf_weight": psf_weight,
        "psf_sigma": psf_sigma,
        "aperture_count": aperture_count,
        "ap_begin": ap_begin,
        "ap_size": ap_size,
        "ap_rot": ap_rot,
        "ap_binx": np.ascontiguousarray(ap_binx, dtype=np.int32),
        "ap_biny": np.ascontiguousarray(ap_biny, dtype=np.int32),
        "ap_psf": np.ascontiguousarray(ap_psf, dtype=np.int32),
        "ap_hist_dim": np.ascontiguousarray(ap_hist_dim, dtype=np.int32),
        "hist_width": hist_width,
        "hist_center": hist_center,
        "hist_bins": np.ascontiguousarray(hist_bins, dtype=np.int32),
        "max_bin_size": max_bin_size,
        "bin_type": np.ascontiguousarray(bin_type, dtype=np.int32),
        "bin_size": bin_size,
        "bin_order": bin_order,
    }


def _read_boxed_aperture(path: Path) -> dict[str, Any]:
    lines = _content_lines(path)
    if len(lines) < 4:
        raise ValueError(f"Boxed aperture file {path} has too few data lines.")
    begin = np.fromstring(lines[0], sep=" ", dtype=np.float64)
    size = np.fromstring(lines[1], sep=" ", dtype=np.float64)
    rotation = np.fromstring(lines[2], sep=" ", dtype=np.float64)
    bins = np.fromstring(lines[3], sep=" ", dtype=np.int32)
    if begin.size != 2 or size.size != 2 or rotation.size != 1 or bins.size != 2:
        raise ValueError(f"Boxed aperture file {path} has invalid shape.")
    return {
        "begin": begin,
        "size": size,
        "rotation": float(rotation[0]),
        "binx": int(bins[0]),
        "biny": int(bins[1]),
    }


def _read_binning_order(path: Path) -> np.ndarray:
    lines = _content_lines(path)
    if len(lines) < 2:
        raise ValueError(f"Binning file {path} has too few data lines.")
    size = int(np.fromstring(lines[0], sep=" ", dtype=np.int64)[0])
    values = np.fromstring(" ".join(lines[1:]), sep=" ", dtype=np.int32)
    if values.size < size:
        raise ValueError(
            f"Binning file {path} contains {values.size} values, expected {size}."
        )
    return np.ascontiguousarray(values[:size], dtype=np.int32)


def _fortran_float(value: Any) -> float:
    if isinstance(value, str):
        return float(value.replace("D", "E").replace("d", "e"))
    return float(value)


def _content_lines(path: Path) -> list[str]:
    with path.open("r", encoding="utf-8") as handle:
        return [
            line.strip()
            for line in handle
            if line.strip() and not line.lstrip().startswith("#")
        ]


def _call_orbitstart_memory_in_worker(
    library_path: Path,
    orbit_library: Any,
    cwd: Path,
) -> OrbitStartMemoryResult:
    context = mp.get_context()
    result_queue = context.Queue()
    process = context.Process(
        target=_orbitstart_memory_worker,
        args=(str(library_path), orbit_library, str(cwd), result_queue),
    )
    process.start()
    process.join()
    if process.exitcode != 0:
        raise RuntimeError(
            "orblib_api_run_orbitstart_memory worker exited with code "
            f"{process.exitcode}."
        )
    try:
        kind, payload = result_queue.get_nowait()
    except queue.Empty as exc:
        raise RuntimeError(
            "orblib_api_run_orbitstart_memory worker returned no status."
        ) from exc
    if kind == "error":
        raise RuntimeError(payload)
    return payload


def _orbitstart_memory_worker(
    library_path: str,
    orbit_library: Any,
    cwd: str,
    result_queue: Any,
) -> None:
    try:
        os.chdir(cwd)
        result = _call_orbitstart_memory_function(
            Path(library_path),
            orbit_library,
        )
    except BaseException as exc:
        result_queue.put(("error", repr(exc)))
    else:
        result_queue.put(("ok", result))


def _call_orbitstart_memory_function(
    library_path: Path,
    orbit_library: Any,
    *,
    abi_function_name: str = "orblib_api_abi_version",
    expected_abi_version: int = SHARED_LIBRARY_ABI_VERSION,
    backend_label: str = "Fortran",
    orbitstart_function_name: str = "orblib_api_run_orbitstart_memory",
) -> OrbitStartMemoryResult:
    inputs = _orbitstart_memory_inputs(orbit_library)
    library = _load_checked_shared_library(
        library_path,
        abi_function_name=abi_function_name,
        expected_abi_version=expected_abi_version,
        backend_label=backend_label,
    )
    function = getattr(library, orbitstart_function_name)
    double_p = ctypes.POINTER(ctypes.c_double)
    int_p = ctypes.POINTER(ctypes.c_int)
    function.argtypes = [
        ctypes.c_int,
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
        ctypes.c_double,
        ctypes.c_double,
        ctypes.c_int,
        ctypes.c_double,
        ctypes.c_double,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_int,
        double_p,
        ctypes.c_int,
        double_p,
        int_p,
        double_p,
        int_p,
        int_p,
        int_p,
        int_p,
    ]
    function.restype = None

    max_rows = inputs["max_rows"]
    begin_values = np.empty(max_rows * 9, dtype=np.float64)
    beginbox_values = np.empty(max_rows * 9, dtype=np.float64)
    begin_noreg = np.empty(max_rows, dtype=np.int32)
    beginbox_noreg = np.empty(max_rows, dtype=np.int32)
    rows_written = ctypes.c_int(0)
    box_rows_written = ctypes.c_int(0)
    status = ctypes.c_int(-1)

    function(
        ctypes.c_int(inputs["random_seed"]),
        ctypes.c_int(inputs["ngauss"]),
        inputs["surf_pc"].ctypes.data_as(double_p),
        inputs["sigobs_arcsec"].ctypes.data_as(double_p),
        inputs["qobs"].ctypes.data_as(double_p),
        inputs["psi_obs"].ctypes.data_as(double_p),
        ctypes.c_double(inputs["distance"]),
        ctypes.c_double(inputs["theta"]),
        ctypes.c_double(inputs["phi"]),
        ctypes.c_double(inputs["psi"]),
        ctypes.c_double(inputs["upsilon"]),
        ctypes.c_double(inputs["xmbh"]),
        ctypes.c_double(inputs["softl_arcsec"]),
        ctypes.c_int(inputs["nener"]),
        ctypes.c_double(inputs["rlogmin"]),
        ctypes.c_double(inputs["rlogmax"]),
        ctypes.c_int(inputs["ni2"]),
        ctypes.c_int(inputs["ni3"]),
        ctypes.c_int(inputs["orbit_dithering"]),
        ctypes.c_int(inputs["quad_nr"]),
        ctypes.c_int(inputs["quad_nth"]),
        ctypes.c_int(inputs["quad_nph"]),
        ctypes.c_int(inputs["dm_profile_type"]),
        ctypes.c_int(inputs["n_dmparam"]),
        inputs["dmparam"].ctypes.data_as(double_p),
        ctypes.c_int(max_rows),
        begin_values.ctypes.data_as(double_p),
        begin_noreg.ctypes.data_as(int_p),
        beginbox_values.ctypes.data_as(double_p),
        beginbox_noreg.ctypes.data_as(int_p),
        ctypes.byref(rows_written),
        ctypes.byref(box_rows_written),
        ctypes.byref(status),
    )
    if status.value != 0:
        raise RuntimeError(
            f"{orbitstart_function_name} failed with status "
            f"{status.value}."
        )

    rows = int(rows_written.value)
    box_rows = int(box_rows_written.value)
    return OrbitStartMemoryResult(
        begin_values=begin_values[: rows * 9].reshape(rows, 9).copy(),
        begin_noreg=begin_noreg[:rows].copy(),
        beginbox_values=beginbox_values[: box_rows * 9].reshape(box_rows, 9).copy(),
        beginbox_noreg=beginbox_noreg[:box_rows].copy(),
    )


def _orbitstart_memory_inputs(orbit_library: Any) -> dict[str, Any]:
    if orbit_library.system.is_bar_disk_system():
        raise NotImplementedError(
            "The direct-input orbit-start ABI currently supports only the "
            "non-bar triaxial path."
        )

    system = orbit_library.system
    settings = orbit_library.settings
    parset = orbit_library.parset
    stars = system.get_unique_triaxial_visible_component()
    bh = system.get_component_from_class(physys.Plummer)
    q = parset[f"q-{stars.name}"]
    p = parset[f"p-{stars.name}"]
    u = parset[f"u-{stars.name}"]
    theta, psi, phi = stars.triax_pqu2tpp(p, q, u)

    dark_components = system.get_all_dark_non_plummer_components()
    if len(dark_components) > 1:
        raise ValueError(
            "The direct-input orbit-start ABI supports at most one "
            "non-Plummer dark component."
        )
    if dark_components:
        dark = dark_components[0]
        if isinstance(dark, physys.NFW_m200_c):
            dm_specs, dm_values = dark.get_dh_legacy_strings(parset, system)
        else:
            dm_specs, dm_values = dark.get_dh_legacy_strings(parset)
        dm_profile_type, n_dmparam = [int(value) for value in dm_specs.split()]
        dmparam = np.fromstring(dm_values, sep=" ", dtype=np.float64)
    else:
        dm_profile_type = 0
        n_dmparam = 0
        dmparam = np.zeros(1, dtype=np.float64)
    if n_dmparam == 0:
        dmparam = np.zeros(1, dtype=np.float64)

    mge_data = stars.mge_pot.data
    orbit_dithering = int(settings["dithering"])
    max_rows = (
        int(settings["nE"])
        * int(settings["nI2"])
        * int(settings["nI3"])
        * orbit_dithering**3
    )
    inputs = {
        "random_seed": int(settings["random_seed"]),
        "ngauss": len(mge_data),
        "surf_pc": np.ascontiguousarray(mge_data["I"], dtype=np.float64),
        "sigobs_arcsec": np.ascontiguousarray(mge_data["sigma"], dtype=np.float64),
        "qobs": np.ascontiguousarray(mge_data["q"], dtype=np.float64),
        "psi_obs": np.ascontiguousarray(mge_data["PA_twist"], dtype=np.float64),
        "distance": float(system.distMPc),
        "theta": float(theta),
        "phi": float(phi),
        "psi": float(psi),
        "upsilon": float(parset["ml"]),
        "xmbh": float(parset[f"m-{bh.name}"]),
        "softl_arcsec": float(parset[f"a-{bh.name}"]),
        "nener": int(settings["nE"]),
        "rlogmin": float(settings["logrmin"]),
        "rlogmax": float(settings["logrmax"]),
        "ni2": int(settings["nI2"]),
        "ni3": int(settings["nI3"]),
        "orbit_dithering": orbit_dithering,
        "quad_nr": int(settings["quad_nr"]),
        "quad_nth": int(settings["quad_nth"]),
        "quad_nph": int(settings["quad_nph"]),
        "dm_profile_type": dm_profile_type,
        "n_dmparam": n_dmparam,
        "dmparam": np.ascontiguousarray(dmparam, dtype=np.float64),
        "max_rows": max_rows,
    }
    return _legacy_parameter_pot_precision(inputs)


def _legacy_parameter_pot_precision(inputs: dict[str, Any]) -> dict[str, Any]:
    """Match the precision of the historical ``parameters_pot.in`` writer."""

    quantized = dict(inputs)
    quantized["surf_pc"] = _fixed_decimal_array(quantized["surf_pc"], 2)
    quantized["sigobs_arcsec"] = _fixed_decimal_array(
        quantized["sigobs_arcsec"],
        5,
    )
    quantized["qobs"] = _fixed_decimal_array(quantized["qobs"], 5)
    quantized["psi_obs"] = _fixed_decimal_array(quantized["psi_obs"], 2)
    quantized["theta"] = _fixed_decimal_scalar(quantized["theta"], 9)
    quantized["phi"] = _fixed_decimal_scalar(quantized["phi"], 9)
    quantized["psi"] = _fixed_decimal_scalar(quantized["psi"], 9)
    return quantized


def _fixed_decimal_scalar(value: Any, decimals: int) -> float:
    return float(f"{float(value):.{decimals}f}")


def _fixed_decimal_array(values: np.ndarray, decimals: int) -> np.ndarray:
    return np.ascontiguousarray(
        [float(f"{float(value):.{decimals}f}") for value in values],
        dtype=np.float64,
    )


def run_orbit_library(
    request: OrbitLibraryRequest,
    backend: OrbitLibraryBackend | None = None,
) -> OrbitLibraryResult:
    """Run an orbit-library request through a backend.

    Callers normally pass only ``request``.  The optional ``backend`` argument is
    for tests and experimental backend injection.
    """

    selected_backend = backend or get_backend(request.backend)
    return selected_backend.run(request)
