import pytest

from conftest import (
    ARCHIVED_NNLS_FORTRAN_DIR,
    ARCHIVED_ORBGEN_PARTGEN_DIR,
    ORBLIB_FORTRAN_DIR,
    ORBLIB_FORTRAN_SHARED_LIBRARY,
)


FORTRAN_NUMERICS_SOURCES = [
    "source/orblib_c_api.f90",
    "source/initial_parameters.f90",
    "source/orbit_start_library.f90",
    "source/orbit_library/aperture_base.f90",
    "source/orbit_library/aperture_boxed.f90",
    "source/orbit_library/aperture_dispatch.f90",
    "source/orbit_library/intrinsic_qgrid.f90",
    "source/orbit_library/losvd_histograms.f90",
    "source/orbit_library/orbit_integrator.f90",
    "source/orbit_library/orbit_library_runner.f90",
    "source/orbit_library/orbit_output.f90",
    "source/orbit_library/projection.f90",
    "source/orbit_library/psf.f90",
    "source/orbit_library/random_gauss_generator.f90",
    "source/orbit_library/spatial_binning.f90",
    "source/potential/dark_halo_potential.f90",
    "source/potential/interpolated_potential.f90",
    "source/potential/triaxial_stellar_potential.f90",
    "source/numerics/dop853.f",
    "source/numerics/dqxgs.f",
    "source/numerics/ellipint.f90",
    "source/numerics/numeric_kinds_f.f90",
    "source/numerics/numrec_arloc.f",
    "source/numerics/ran1_nr.f90",
    "source/numerics/specfunc_beta.f90",
]

FORTRAN_UNUSED_SOURCES = [
    "unused/Changelog.txt",
    "unused/cutest_makefile",
    "unused/dopri5.f",
    "unused/orbitstart.f90",
    "unused/orbitstart_bar.f90",
    "unused/orblibprogram.f90",
    "unused/orblibprogram_bar.f90",
    "unused/pij.f90",
]

ARCHIVED_NNLS_FORTRAN_FILES = [
    "triaxnnls_noCRcut.f90",
    "triaxnnls_CRcut.f90",
    "triaxnnls_bar.f90",
    "sub/nnls95.f",
    "sub/gausherm.f",
    "galahad-2.3",
    "hsl",
    "cuter",
]

ARCHIVED_MASS_HELPER_FILES = [
    "mass_helpers/triaxmass.f90",
    "mass_helpers/triaxmass_bar.f90",
    "mass_helpers/triaxmass_f.f90",
    "mass_helpers/triaxmassbin.f90",
    "mass_helpers/triaxmassbin_bar.f90",
    "mass_helpers/triaxmassbin_f.f90",
    "mass_helpers/nag.f",
    "mass_helpers/README.md",
]

ARCHIVED_ORBGEN_PARTGEN_FILES = [
    "orbgen_partgen/README_IMPORTANT.txt",
    "orbgen_partgen/orbgen.f90",
    "orbgen_partgen/partgen.f90",
]


@pytest.mark.fortran
def test_fortran_sources_used_by_python_are_present():
    missing = []
    for source in FORTRAN_NUMERICS_SOURCES:
        if not (ORBLIB_FORTRAN_DIR / source).is_file():
            missing.append(source)
    assert missing == []


@pytest.mark.fortran
def test_unused_fortran_sources_are_separated_from_active_sources():
    missing = [
        source for source in FORTRAN_UNUSED_SOURCES
        if not (ORBLIB_FORTRAN_DIR / source).is_file()
    ]
    assert missing == []

    active_files = {
        *FORTRAN_NUMERICS_SOURCES,
    }
    assert not active_files.intersection(FORTRAN_UNUSED_SOURCES)


@pytest.mark.fortran
def test_archived_nnls_and_galahad_sources_are_not_in_active_fortran_tree():
    active_paths = [
        ORBLIB_FORTRAN_DIR / "triaxnnls_noCRcut.f90",
        ORBLIB_FORTRAN_DIR / "triaxnnls_CRcut.f90",
        ORBLIB_FORTRAN_DIR / "triaxnnls_bar.f90",
        ORBLIB_FORTRAN_DIR / "source" / "numerics" / "nnls95.f",
        ORBLIB_FORTRAN_DIR / "source" / "numerics" / "gausherm.f",
        ORBLIB_FORTRAN_DIR / "galahad-2.3",
        ORBLIB_FORTRAN_DIR / "hsl",
        ORBLIB_FORTRAN_DIR / "cuter",
    ]
    assert [path for path in active_paths if path.exists()] == []

    missing_from_archive = [
        path for path in ARCHIVED_NNLS_FORTRAN_FILES
        if not (ARCHIVED_NNLS_FORTRAN_DIR / path).exists()
    ]
    assert missing_from_archive == []


@pytest.mark.fortran
def test_archived_mass_helpers_are_not_in_active_fortran_tree():
    active_paths = [
        ORBLIB_FORTRAN_DIR / "source" / "triaxmass.f90",
        ORBLIB_FORTRAN_DIR / "source" / "triaxmass_bar.f90",
        ORBLIB_FORTRAN_DIR / "source" / "triaxmass_f.f90",
        ORBLIB_FORTRAN_DIR / "source" / "triaxmassbin.f90",
        ORBLIB_FORTRAN_DIR / "source" / "triaxmassbin_bar.f90",
        ORBLIB_FORTRAN_DIR / "source" / "triaxmassbin_f.f90",
        ORBLIB_FORTRAN_DIR / "source" / "numerics" / "nag.f",
    ]
    assert [path for path in active_paths if path.exists()] == []

    missing_from_archive = [
        path for path in ARCHIVED_MASS_HELPER_FILES
        if not (ARCHIVED_NNLS_FORTRAN_DIR / path).exists()
    ]
    assert missing_from_archive == []


@pytest.mark.fortran
def test_archived_orbgen_partgen_sources_are_not_in_active_fortran_tree():
    assert not (ORBLIB_FORTRAN_DIR / "orbgen_partgen").exists()
    assert not (ORBLIB_FORTRAN_DIR / "source" / "orbgen_partgen").exists()

    missing_from_archive = [
        path for path in ARCHIVED_ORBGEN_PARTGEN_FILES
        if not (ARCHIVED_ORBGEN_PARTGEN_DIR / path).exists()
    ]
    assert missing_from_archive == []


@pytest.mark.fortran
@pytest.mark.orblib_fortran
def test_orblib_fortran_shared_library_is_built():
    assert ORBLIB_FORTRAN_SHARED_LIBRARY.is_file()
