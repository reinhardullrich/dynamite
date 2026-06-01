import subprocess

import numpy as np
import pytest
from scipy import optimize

from conftest import (
    ARCHIVED_NNLS_FORTRAN_DIR,
    LEGACY_FORTRAN_DIR,
    compile_fortran_driver,
)
from dynamite.myrand import MyRand


@pytest.mark.fortran
def test_fortran_ran1_matches_python_myrand(tmp_path):
    driver = """
program ran1_driver
  implicit none
  integer :: i, n, seed
  double precision :: x
  double precision ran1
  external ran1

  read (*, *) seed, n
  do i = 1, n
    if (i .eq. 1) then
      x = ran1(seed)
    else
      x = ran1(1)
    endif
    write (*, '(ES25.16)') x
  enddo
end program ran1_driver
"""
    executable = compile_fortran_driver(
        tmp_path,
        driver,
        [LEGACY_FORTRAN_DIR / "ran1_nr.f"],
        "ran1_driver",
    )
    seed = -4242
    count = 64
    completed = subprocess.run(
        [str(executable)],
        input=f"{seed} {count}\n",
        check=True,
        text=True,
        stdout=subprocess.PIPE,
    )
    fortran_values = np.fromstring(completed.stdout, sep=" ")
    python_rng = MyRand(seed)
    python_values = np.array([python_rng.ran1() for _ in range(count)])
    np.testing.assert_allclose(fortran_values, python_values, rtol=0.0, atol=1e-15)


@pytest.mark.fortran
def test_fortran_nnls95_matches_scipy_nnls_on_small_dense_problem(tmp_path):
    driver = """
program nnls_driver
  implicit none
  integer, parameter :: m = 4, n = 2, mda = 4
  double precision :: a(mda, n), b(m), x(n), rnorm, w(n), zz(m)
  integer :: index(n), mode

  a = reshape((/ &
    1.0d0, 0.0d0, 1.0d0, 0.0d0, &
    0.0d0, 1.0d0, 1.0d0, 1.0d0 /), (/mda, n/))
  b = (/1.0d0, 2.0d0, 2.5d0, 1.0d0/)

  call NNLS(a, mda, m, n, b, x, rnorm, w, zz, index, mode)
  write (*, '(I0,1X,3(ES25.16,1X))') mode, x(1), x(2), rnorm
end program nnls_driver
"""
    executable = compile_fortran_driver(
        tmp_path,
        driver,
        [ARCHIVED_NNLS_FORTRAN_DIR / "sub" / "nnls95.f"],
        "nnls_driver",
    )
    completed = subprocess.run(
        [str(executable)],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
    )
    parts = completed.stdout.split()
    mode = int(parts[0])
    fortran_x = np.array([float(parts[1]), float(parts[2])])
    fortran_rnorm = float(parts[3])

    a = np.array(
        [
            [1.0, 0.0],
            [0.0, 1.0],
            [1.0, 1.0],
            [0.0, 1.0],
        ]
    )
    b = np.array([1.0, 2.0, 2.5, 1.0])
    scipy_x, scipy_rnorm = optimize.nnls(a, b)

    assert mode == 1
    np.testing.assert_allclose(fortran_x, scipy_x, rtol=1e-12, atol=1e-12)
    np.testing.assert_allclose(fortran_rnorm, scipy_rnorm, rtol=1e-12, atol=1e-12)


@pytest.mark.fortran
@pytest.mark.parametrize(
    ("a", "b"),
    [
        (
            np.array(
                [
                    [1.0, 0.0],
                    [0.0, 1.0],
                    [1.0, 1.0],
                    [0.0, 1.0],
                ]
            ),
            np.array([1.0, 2.0, 2.5, 1.0]),
        ),
        (
            np.eye(2),
            np.array([-1.0, 2.0]),
        ),
        (
            np.array(
                [
                    [1.0, 1.0, 0.0],
                    [0.0, 1.0, 1.0],
                    [1.0, 0.0, 1.0],
                    [2.0, 1.0, 0.0],
                ]
            ),
            np.array([1.0, 0.5, 2.0, 2.5]),
        ),
        (
            np.array(
                [
                    [1.0, 0.0, 0.0],
                    [0.0, 1.0, 0.0],
                    [0.0, 0.0, 1.0],
                    [1.0, 1.0, 1.0],
                ]
            ),
            np.zeros(4),
        ),
    ],
)
def test_fortran_nnls95_matches_scipy_nnls_for_reference_cases(tmp_path, a, b):
    driver = """
program nnls_stdin_driver
  implicit none
  integer :: m, n, mda, i, j, mode
  double precision :: rnorm
  double precision, allocatable :: a(:, :), rhs(:), x(:), w(:), zz(:)
  integer, allocatable :: index(:)

  read (*, *) m, n
  mda = m
  allocate(a(mda, n), rhs(m), x(n), w(n), zz(m), index(n))
  do i = 1, m
    do j = 1, n
      read (*, *) a(i, j)
    enddo
  enddo
  do i = 1, m
    read (*, *) rhs(i)
  enddo

  call NNLS(a, mda, m, n, rhs, x, rnorm, w, zz, index, mode)
  write (*, '(I0)') mode
  do i = 1, n
    write (*, '(ES25.16)') x(i)
  enddo
  write (*, '(ES25.16)') rnorm
end program nnls_stdin_driver
"""
    executable = compile_fortran_driver(
        tmp_path,
        driver,
        [ARCHIVED_NNLS_FORTRAN_DIR / "sub" / "nnls95.f"],
        "nnls_stdin_driver",
    )
    lines = [f"{a.shape[0]} {a.shape[1]}"]
    lines.extend(str(value) for value in a.ravel(order="C"))
    lines.extend(str(value) for value in b)
    completed = subprocess.run(
        [str(executable)],
        input="\n".join(lines) + "\n",
        check=True,
        text=True,
        stdout=subprocess.PIPE,
    )
    output = completed.stdout.split()
    mode = int(output[0])
    fortran_x = np.array([float(value) for value in output[1 : 1 + a.shape[1]]])
    fortran_rnorm = float(output[1 + a.shape[1]])

    scipy_x, scipy_rnorm = optimize.nnls(a, b)

    assert mode == 1
    np.testing.assert_allclose(fortran_x, scipy_x, rtol=1e-11, atol=1e-11)
    np.testing.assert_allclose(fortran_rnorm, scipy_rnorm, rtol=1e-11, atol=1e-11)
