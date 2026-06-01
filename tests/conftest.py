import os
import shutil
import subprocess
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
LEGACY_FORTRAN_DIR = REPO_ROOT / "legacy_fortran"


def pytest_collection_modifyitems(config, items):
    skip_slow = pytest.mark.skip(
        reason="set DYNAMITE_RUN_SLOW_TESTS=1 to run slow integration tests"
    )
    skip_legacy_exec = pytest.mark.skip(
        reason=(
            "set DYNAMITE_RUN_LEGACY_EXEC_TESTS=1 to run tests requiring "
            "built legacy Fortran executables"
        )
    )
    for item in items:
        if "slow" in item.keywords and os.environ.get("DYNAMITE_RUN_SLOW_TESTS") != "1":
            item.add_marker(skip_slow)
        if (
            "legacy_fortran" in item.keywords
            and os.environ.get("DYNAMITE_RUN_LEGACY_EXEC_TESTS") != "1"
        ):
            item.add_marker(skip_legacy_exec)


def require_gfortran():
    compiler = shutil.which("gfortran")
    if compiler is None:
        pytest.skip("gfortran is required for this Fortran parity test")
    return compiler


def compile_fortran_driver(tmp_path, driver_source, sources, output_name):
    compiler = require_gfortran()
    driver = tmp_path / f"{output_name}.f90"
    driver.write_text(driver_source)
    executable = tmp_path / output_name
    cmd = [compiler, "-O0", "-g", "-o", str(executable), str(driver)]
    cmd.extend(str(source) for source in sources)
    subprocess.run(cmd, check=True, cwd=REPO_ROOT)
    return executable
