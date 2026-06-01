from pathlib import Path

import pytest

from conftest import ARCHIVED_NNLS_FORTRAN_DIR, LEGACY_FORTRAN_DIR


FORTRAN_PROGRAMS_IN_USE = {
    "orbitstart": "orbitstart.f90",
    "orbitstart_bar": "orbitstart_bar.f90",
    "orblib_new_mirror": "orblibprogram.f90",
    "orblib_bar": "orblibprogram_bar.f90",
    "triaxmass": "triaxmass.f90",
    "triaxmass_bar": "triaxmass_bar.f90",
    "triaxmassbin": "triaxmassbin.f90",
    "triaxmassbin_bar": "triaxmassbin_bar.f90",
}

FORTRAN_SUPPORT_SOURCES = [
    "orbitstart_f.f90",
    "orblib_f_new_mirror.f90",
    "triaxmass_f.f90",
    "triaxmassbin_f.f90",
    "ran1_nr.f",
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


@pytest.mark.fortran
def test_fortran_sources_used_by_python_are_present():
    missing = []
    for source in FORTRAN_PROGRAMS_IN_USE.values():
        if not (LEGACY_FORTRAN_DIR / source).is_file():
            missing.append(source)
    for source in FORTRAN_SUPPORT_SOURCES:
        if not (LEGACY_FORTRAN_DIR / source).is_file():
            missing.append(source)
    assert missing == []


@pytest.mark.fortran
def test_archived_nnls_and_galahad_sources_are_not_in_active_fortran_tree():
    active_paths = [
        LEGACY_FORTRAN_DIR / "triaxnnls_noCRcut.f90",
        LEGACY_FORTRAN_DIR / "triaxnnls_CRcut.f90",
        LEGACY_FORTRAN_DIR / "triaxnnls_bar.f90",
        LEGACY_FORTRAN_DIR / "sub" / "nnls95.f",
        LEGACY_FORTRAN_DIR / "sub" / "gausherm.f",
        LEGACY_FORTRAN_DIR / "galahad-2.3",
        LEGACY_FORTRAN_DIR / "hsl",
        LEGACY_FORTRAN_DIR / "cuter",
    ]
    assert [path for path in active_paths if path.exists()] == []

    missing_from_archive = [
        path for path in ARCHIVED_NNLS_FORTRAN_FILES
        if not (ARCHIVED_NNLS_FORTRAN_DIR / path).exists()
    ]
    assert missing_from_archive == []


@pytest.mark.fortran
@pytest.mark.legacy_fortran
def test_legacy_fortran_executables_are_built_and_executable():
    missing_or_not_executable = []
    for executable in FORTRAN_PROGRAMS_IN_USE:
        path = LEGACY_FORTRAN_DIR / executable
        if not path.is_file() or not path.stat().st_mode & 0o111:
            missing_or_not_executable.append(str(Path("legacy_fortran") / executable))
    assert missing_or_not_executable == []
