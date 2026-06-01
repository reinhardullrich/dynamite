from pathlib import Path

import pytest

from conftest import LEGACY_FORTRAN_DIR


FORTRAN_PROGRAMS_IN_USE = {
    "orbitstart": "orbitstart.f90",
    "orbitstart_bar": "orbitstart_bar.f90",
    "orblib_new_mirror": "orblibprogram.f90",
    "orblib_bar": "orblibprogram_bar.f90",
    "triaxmass": "triaxmass.f90",
    "triaxmass_bar": "triaxmass_bar.f90",
    "triaxmassbin": "triaxmassbin.f90",
    "triaxmassbin_bar": "triaxmassbin_bar.f90",
    "triaxnnls_noCRcut": "triaxnnls_noCRcut.f90",
    "triaxnnls_CRcut": "triaxnnls_CRcut.f90",
    "triaxnnls_bar": "triaxnnls_bar.f90",
}

FORTRAN_SUPPORT_SOURCES = [
    "orbitstart_f.f90",
    "orblib_f_new_mirror.f90",
    "triaxmass_f.f90",
    "triaxmassbin_f.f90",
    "sub/nnls95.f",
    "ran1_nr.f",
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
@pytest.mark.legacy_fortran
def test_legacy_fortran_executables_are_built_and_executable():
    missing_or_not_executable = []
    for executable in FORTRAN_PROGRAMS_IN_USE:
        path = LEGACY_FORTRAN_DIR / executable
        if not path.is_file() or not path.stat().st_mode & 0o111:
            missing_or_not_executable.append(str(Path("legacy_fortran") / executable))
    assert missing_or_not_executable == []

