from pathlib import Path

import pytest

from conftest import (
    ARCHIVED_NNLS_FORTRAN_DIR,
    ARCHIVED_ORBGEN_PARTGEN_DIR,
    ORBLIB_FORTRAN_BIN_DIR,
    ORBLIB_FORTRAN_DIR,
)


FORTRAN_PROGRAMS_IN_USE = {
    "orbitstart": "source/orbitstart.f90",
    "orbitstart_bar": "source/orbitstart_bar.f90",
    "orblib_new_mirror": "source/orblibprogram.f90",
    "orblib_bar": "source/orblibprogram_bar.f90",
    "triaxmass": "source/triaxmass.f90",
    "triaxmass_bar": "source/triaxmass_bar.f90",
    "triaxmassbin": "source/triaxmassbin.f90",
    "triaxmassbin_bar": "source/triaxmassbin_bar.f90",
}

FORTRAN_NUMERICS_SOURCES = [
    "source/orbitstart_f.f90",
    "source/orblib_f_new_mirror.f90",
    "source/triaxmass_f.f90",
    "source/triaxmassbin_f.f90",
    "source/ran1_nr.f",
    "source/numerics/dop853.f",
    "source/numerics/dqxgs.f",
    "source/numerics/ellipint.f90",
    "source/numerics/nag.f",
    "source/numerics/numeric_kinds_f.f90",
    "source/numerics/numrec_arloc.f",
    "source/numerics/specfunc_beta.f90",
]

FORTRAN_UNUSED_SOURCES = [
    "source/unused/dopri5.f",
    "source/unused/pij.f90",
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

ARCHIVED_ORBGEN_PARTGEN_FILES = [
    "orbgen_partgen/README_IMPORTANT.txt",
    "orbgen_partgen/orbgen.f90",
    "orbgen_partgen/partgen.f90",
]


@pytest.mark.fortran
def test_fortran_sources_used_by_python_are_present():
    missing = []
    for source in FORTRAN_PROGRAMS_IN_USE.values():
        if not (ORBLIB_FORTRAN_DIR / source).is_file():
            missing.append(source)
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
        *FORTRAN_PROGRAMS_IN_USE.values(),
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
def test_orblib_fortran_executables_are_built_and_executable():
    missing_or_not_executable = []
    for executable in FORTRAN_PROGRAMS_IN_USE:
        path = ORBLIB_FORTRAN_BIN_DIR / executable
        if not path.is_file() or not path.stat().st_mode & 0o111:
            missing_or_not_executable.append(
                str(Path("orblib_fortran") / "bin" / executable)
            )
    assert missing_or_not_executable == []
