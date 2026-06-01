# DYNAMITE Scientific Correctness Audit

Date: 2026-06-01

Scope: this audit checks whether the astrophysical and mathematical modelling
assumptions in DYNAMITE are scientifically defensible. It does not judge code
style, packaging, maintainability, or ordinary programming bugs unless they
directly affect the scientific meaning of a model equation.

## Short Conclusion

The core DYNAMITE modelling chain is scientifically grounded: it implements a
standard triaxial Schwarzschild orbit-superposition model using MGE
deprojection, MGE gravitational potentials, orbit libraries, non-negative orbit
weights, and Gauss-Hermite or LOSVD constraints. The central stellar-dynamical
framework matches the methods of Cappellari (2002), van den Bosch et al.
(2008), van der Marel & Franx (1993), and the DYNAMITE mirroring correction
literature.

I did not find evidence that the main stellar MGE deprojection, stellar mass
normalisation, MGE force calculation, NFW halo, Hernquist halo, or
Gauss-Hermite fitting equations are scientifically wrong.

The main scientific caveats are:

1. The triaxial cored logarithmic halo can imply negative density for too-flat
   axis ratios, but DYNAMITE only checks `0 < q <= p <= 1`, not the full
   physical-density domain.
2. The bar/rotating-frame machinery is plausible, but it deserves separate
   benchmark validation against published barred-model orbit libraries before
   being treated with the same confidence as the non-rotating triaxial path.
3. The orbit library completeness and convergence cannot be certified by static
   equation inspection; each science project still needs convergence tests in
   orbit number, integration time, regularisation, and aperture/LOSVD settings.
4. Some halo parameter choices are scientifically conventional but not unique:
   `NFW_m200_c` uses a Dutton & Maccio style relation while the internal
   constants use `H0 = 70`, whereas that quoted Planck-era relation is normally
   stated with `H0 = 67.1`.
5. The code allows or provides options that are modelling priors, not physical
   laws: black-hole softening, fixed/global M/L unless a separate mass MGE is
   supplied, CRcut, and smoothing regularisation.

## Literature Baseline Used

- Cappellari (2002), MGE deprojection and potential: https://academic.oup.com/mnras/article/333/2/400/1019346
- van den Bosch et al. (2008), triaxial Schwarzschild method: https://academic.oup.com/mnras/article/385/2/647/1068433
- Thater et al. (2022), DYNAMITE mirroring correction robustness: https://arxiv.org/abs/2205.04165
- Dutton & Maccio (2014), concentration-mass relation: https://arxiv.org/abs/1402.7073
- Zhao (1996), generalized double-power-law models: https://academic.oup.com/mnras/article/278/2/488/951933
- van der Marel & Franx (1993), Gauss-Hermite LOSVD parameterisation: https://ntrs.nasa.gov/citations/19930050781
- Reference formulas for NFW, Hernquist, logarithmic, and flattened potentials:
  https://galaxiesbook.org/chapters/I-01.-Gravitation_4-Examples-of-spherical-potentials.html and
  https://galaxiesbook.org/chapters/II-01.-Gravitation-in-Galactic-Disks_2-Simple-gravitational-potentials-for-flattened-mass-distributions.html

## Reviewed Model Areas

- Stellar MGE total mass and M/L scaling:
  `dynamite/dynamite/physical_system.py:549-574`
- Triaxial MGE geometry and viewing-angle conversion:
  `dynamite/dynamite/physical_system.py:651-886`
- Projected and intrinsic MGE mass constraints:
  `dynamite/dynamite/mges.py:101-345`, `dynamite/dynamite/mges.py:660-920`
- MGE potential and acceleration:
  `dynamite/legacy_fortran/triaxpotent.f90:90-620`
- Dark halo and black-hole potentials:
  `dynamite/legacy_fortran/dmpotent.f90:30-264`,
  `dynamite/dynamite/physical_system.py:1120-1445`
- Orbit initial-condition sampling and rotating-frame equations:
  `dynamite/legacy_fortran/orbitstart_f.f90:1-304`,
  `dynamite/legacy_fortran/orblib_f_new_mirror.f90:667-710`
- Projection/mirroring:
  `dynamite/legacy_fortran/orblib_f_new_mirror.f90:825-1040`,
  `dynamite/docs/index.rst:28-36`
- Gauss-Hermite observables and NNLS constraints:
  `dynamite/dynamite/kinematics.py:460-650`,
  `dynamite/dynamite/weight_solvers.py:650-820`,
  `dynamite/legacy_fortran/triaxnnls_noCRcut.f90:470-575`

## Detailed Findings

### 1. Stellar MGE Mass Normalisation Is Correct

DYNAMITE computes total stellar mass as

`M = 2*pi*sum(I_j*q'_j*sigma'_j^2)*M/L`

after converting the observed Gaussian widths from arcsec to physical length
(`dynamite/dynamite/physical_system.py:549-574`). This is the correct projected
2D Gaussian luminosity integral. The conversion factor `distance*pi/0.648` is
equivalent to pc per arcsec for a distance in Mpc.

Scientific status: sound.

### 2. Triaxial MGE Deprojection Matches the Standard Formalism

The code uses the triaxial MGE assumptions:

- intrinsic axes ordered as `0 < q <= p <= 1`;
- shared viewing angles for all Gaussian components;
- parameterisation via `(p, q, u)` or `(theta, phi, psi)`;
- the Cappellari (2002) intrinsic Gaussian width relation.

The Fortran path implements the triaxial deprojection and the intrinsic sigma
relation in `triaxpotent.f90:106-155`. The Python path implements the same
viewing-angle and intrinsic-shape checks in `physical_system.py:651-886` and
`mges.py:758-810`.

This agrees with Cappellari (2002), which explicitly presents triaxial MGE
deprojection, intrinsic axis ratios, and a one-dimensional MGE potential
integral. It also agrees with the van den Bosch et al. (2008) triaxial
Schwarzschild setup.

Scientific status: sound, with the standard caveat that triaxial deprojection
is not unique. A DYNAMITE model is one admissible intrinsic density compatible
with the photometry and selected viewing angles, not a unique inversion of the
image.

### 3. MGE Potential and Forces Are Scientifically Consistent

`triaxpotent.f90` evaluates the triaxial Gaussian potential using the
one-dimensional MGE integral and uses inner/outer approximations for numerical
efficiency. The code explicitly checks the inner and outer approximation
against the direct integral during setup (`triaxpotent.f90:210-237` and
`397-424`). The acceleration integrands (`triaxpotent.f90:585-620`) are the
spatial derivatives of the same potential integral.

The sign convention is a relative-potential convention: the potential stored by
DYNAMITE is positive for finite-mass attractive components, and accelerations
are the gradient of that relative potential. That is consistent for the stellar
MGE, point mass/softened black hole, NFW, and Hernquist components.

Scientific status: sound.

### 4. Projected and Intrinsic Mass Constraints Are Scientifically Appropriate

Projected aperture masses are computed from PSF-convolved Gaussian components
and binned into the observational aperture grid (`mges.py:300-345`). The
circular-Gaussian PSF convolution follows the usual MGE property that Gaussian
convolution remains Gaussian.

Intrinsic masses are integrated over the model's spherical-polar grid, with an
octant calculation multiplied by 8 (`mges.py:841-888`). That is scientifically
valid only for reflection-symmetric triaxial systems. This is exactly the
symmetry assumed by the standard non-rotating triaxial Schwarzschild model.

Scientific status: sound under the stated symmetry assumptions.

### 5. NFW Halo Is Correct, but Its Parameterisation Must Be Interpreted Carefully

The Fortran NFW setup uses

`rho_s = (200/3)*rho_crit*c^3/[ln(1+c)-c/(1+c)]`

and a scale radius derived from `M200 = f * total_stellar_mass`
(`dmpotent.f90:38-57`). The NFW relative potential and acceleration
(`dmpotent.f90:169-177`, `236-253`) are consistent with the standard NFW mass
profile.

Scientific status: formula correct.

Interpretation caveat: the parameter `f` is not a local dark-matter fraction
and not a baryon fraction. It is `M200 / total_stellar_mass`. This is a valid
model parameterisation, but users must not read it as the dark fraction within
the observed galaxy aperture.

### 6. `NFW_m200_c` Uses the Right Relation but a Slightly Different H0 Convention

The `NFW_m200_c` class uses the Dutton & Maccio-style relation

`log10(c200) = 0.905 - 0.101*log10(M200/(1e12/h))`

(`physical_system.py:1155-1196`). That is the same published functional form.
However, DUTTON/Maccio's quoted Planck relation is tied to `H0 = 67.1`, while
DYNAMITE constants use `H0 = 70` (`constants.py:3-7`,
`iniparam_f.f90:80-84`).

Scientific status: acceptable as a small cosmology convention difference, but
for precision halo work the cosmology should be made explicit in the analysis.

### 7. Hernquist Halo Formula Is Correct

DYNAMITE's Hernquist option uses a density proportional to

`rho_c * r_c^4 / [r (r+r_c)^3]`

and a relative potential equivalent to

`Psi = G*M/(r+r_c)` with `M = 2*pi*rho_c*r_c^3`.

The Fortran expressions in `dmpotent.f90:59-65`, `178-181`, and `254-258` match
the standard Hernquist potential-density pair, up to DYNAMITE's relative
potential sign convention.

Scientific status: sound.

### 8. Generalised NFW Is Scientifically Plausible, but Parameter Bounds Are Loose

The Python `GeneralisedNFW` model implements a Zhao-style double-power-law
density

`rho(r) = rho_s * r^(-gamma) * (r+r_s)^(gamma-3)`

and normalises `rho_s` from `Mvir`, `c`, and a hypergeometric mass integral
(`physical_system.py:1335-1445`). This is scientifically consistent with the
generalized NFW/Zhao family.

The Python validator requires `c > 0`, `Mvir > 0`, and `gamma <= 1`
(`physical_system.py:1352-1374`), but it does not enforce `gamma >= 0`. Negative
inner slopes are mathematically possible but are not the usual "cusped gNFW"
interpretation. The Fortran path also contains special handling for
`gamma > 1` (`dmpotent.f90:109-130`), despite the Python-level stated limit.

Scientific status: core formula plausible. For science runs, I would explicitly
restrict `0 <= gamma <= 1` unless there is a deliberate physical reason to use a
central hole or a steeper cusp.

### 9. Triaxial Cored Logarithmic Halo Needs a Physical-Density Check

DYNAMITE implements the cored logarithmic halo force for

`Phi = 0.5*Vc^2*ln(Rc^2 + x^2 + y^2/p^2 + z^2/q^2)`

using a relative-potential sign convention (`dmpotent.f90:66-87`,
`182-187`, `259-264`). The apparent negative sign in the stored potential is
not itself a scientific error; it is consistent with integrating equations in a
relative potential.

The scientific issue is the allowed flattening. Flattened logarithmic
potentials are not guaranteed to correspond to non-negative densities
everywhere. DYNAMITE validates only `0 < q <= p <= 1` (`dmpotent.f90:75-77`).
That is necessary but not sufficient. In the axisymmetric limit, a classic
warning is that sufficiently flat logarithmic halos have negative-density
regions; the triaxial case has an allowed region in `(p, q)` space, not simply
all `0 < q <= p <= 1`.

From DYNAMITE's own density expression in the Python helper
(`physical_system.py:1317-1321`), large-radius positivity along the `z` axis
requires approximately:

`q^2 * (1 + 1/p^2) > 1`

For `p = 1`, this gives the familiar axisymmetric condition
`q > 1/sqrt(2) ~= 0.707`. DYNAMITE does not enforce this.

Scientific status: the force law is standard, but the parameter domain is not
scientifically guarded. Any science analysis using `TriaxialCoredLogPotential`
should explicitly verify that the implied density is positive over the spatial
domain being modelled.

Additional note: the Python helper for `TriaxialCoredLogPotential.potential`
unpacks parameters as `(rc, vc, p, q)` even though the class declares
`par_names = ['Vc', 'Rc', 'p', 'q']` (`physical_system.py:1294-1315`). The
legacy Fortran path uses the documented order correctly. I would not use the
Python helper for independent scientific checks until that mismatch is
resolved.

### 10. Black Hole Is Softened, Not a Pure Point Mass

The central black hole term is Plummer-softened:

`Psi_BH = G*M_BH/sqrt(r^2 + softl^2)`

with acceleration proportional to `(r^2 + softl^2)^(-3/2)`
(`dmpotent.f90:163-164`, `227-231`). This is not an exact point-mass black-hole
potential at radii comparable to `softl`.

Scientific status: acceptable if `softl` is much smaller than the relevant
spatial resolution and black-hole sphere of influence. It becomes a scientific
approximation if used near the centre with too-large softening.

### 11. Non-Rotating Orbit Library Is Scientifically Standard

The initial condition generator samples energies logarithmically, then samples
the start-space grid used to cover box and tube orbit families
(`orbitstart_f.f90:67-152`, `184-304`). This follows the orbit-family coverage
logic of triaxial Schwarzschild modelling. Dithering and regular/nonregular
flags are consistent with the van den Bosch et al. approach.

Scientific status: standard for the intended model class. Static inspection
cannot prove that a particular run's orbit library is complete. That must be
tested by increasing `nE`, `nI2`, `nI3`, integration time, and aperture/velocity
resolution until inferred parameters stabilise.

### 12. Rotating Bar Equations Are Plausible but Need Dedicated Validation

For `Omega != 0`, DYNAMITE integrates in a rotating frame:

`xdot = p_x + Omega*y`

`ydot = p_y - Omega*x`

`pdot_x = a_x + Omega*p_y`

`pdot_y = a_y - Omega*p_x`

(`orblib_f_new_mirror.f90:688-703`). These are the canonical equations for a
Hamiltonian of the form

`H = 0.5*(p_x^2+p_y^2+p_z^2) + Phi - Omega*L_z`

up to DYNAMITE's relative-potential sign convention. The energy/Jacobi-like
diagnostic in `computer_energy` also includes an `Omega*L_z` term
(`orblib_f_new_mirror.f90:825-835`).

Scientific status: plausible and internally coherent.

Scientific caveat: `orbitstart_f.f90` explicitly notes that the initial
condition sampling is still in a stationary frame (`orbitstart_f.f90:1-14`) and
constructs a retrograde library by flipping `Vy` (`orbitstart_f.f90:239-267`).
That is a pragmatic barred-galaxy modelling choice. It should be benchmarked
against published barred Schwarzschild tests or known reference models before
using it for strong scientific claims about bar orbital structure.

### 13. Orbit Mirroring Uses the Corrected DYNAMITE Path

The documentation states that the old mirroring bug reported by Quenneville et
al. was corrected in DYNAMITE starting with version 3.0.0 and identifies
`orblib_f_new_mirror.f90` as the corrected implementation
(`docs/index.rst:28-36`). The inspected orbit-library path uses
`orblib_f_new_mirror.f90`, with 8-fold projection for non-rotating triaxial
models and a reduced 4-fold symmetry for rotating bars
(`orblib_f_new_mirror.f90:928-1027`).

Scientific status: consistent with the published correction. This is one of the
strongest pieces of evidence that the current code is scientifically safer than
the older van den Bosch mirroring implementation.

### 14. Gauss-Hermite and LOSVD Treatment Is Scientifically Standard

The Python kinematics code uses the normalized Hermite polynomial convention
and expands LOSVDs around observed `V` and `sigma`
(`kinematics.py:460-650`). The Fortran and Python weight solvers treat `h1` and
`h2` as zero-target constraints with uncertainties derived from `dV` and
`dSigma`, and multiply observed higher-order GH moments by aperture mass
(`triaxnnls_noCRcut.f90:559-575`, `weight_solvers.py:704-725`).

This is scientifically consistent with the standard linear Schwarzschild
fitting trick: orbit observables are mass-weighted LOSVD/GH contributions so
that non-negative orbit weights can be solved linearly.

Scientific status: sound.

### 15. NNLS Weights Are Physically Appropriate

The weight solver imposes non-negative orbit weights and fits total mass,
intrinsic mass, projected aperture mass, and kinematic constraints
(`weight_solvers.py:656-729`). Non-negative superposition is the scientific
core of Schwarzschild modelling.

Scientific status: sound.

### 16. CRcut and Regularisation Are Priors, Not Physics

`CRcut` penalizes/cuts counter-rotating orbit contributions when they strongly
disagree with the observed mean rotation (`weight_solvers.py:731-774`). This is
documented as following Zhu et al. (2018). It can be useful for the
counter-rotating-orbit degeneracy, but it is a scientific prior. It can bias a
real galaxy with genuine counter-rotation, multiple kinematic components, or a
poorly measured velocity field.

Regularisation smooths weights in integral space
(`triaxnnls_noCRcut.f90:579-760`). It is also a prior. It improves stability,
but it can suppress real sharp distribution-function structure.

Scientific status: acceptable if explicitly reported and sensitivity-tested.

## Scientific Assumptions That Must Hold

DYNAMITE is scientifically appropriate when these assumptions are acceptable:

- The stellar system is close to steady-state equilibrium.
- The luminosity density can be represented by a sum of Gaussians.
- A selected triaxial deprojection/viewing geometry is an acceptable member of
  the non-unique deprojection family.
- Reflection symmetry is appropriate for the modelled system, except for the
  special rotating-bar path.
- The gravitational potential is time-independent, or steady in the rotating
  frame for bar models.
- The orbit library is large enough to span the relevant orbit families.
- The M/L structure is represented correctly by either a global `ml` or by the
  supplied separate mass MGE.
- The halo parameterisation is treated as a modelling assumption, not as a
  unique cosmological truth.

## Things I Would Validate Before Publishing Science Results

1. Run convergence tests over orbit-library size: increase `nE`, `nI2`, `nI3`,
   integration time, and velocity histogram resolution until black-hole mass,
   M/L, halo parameters, and intrinsic shape are stable.
2. For any `TriaxialCoredLogPotential` model, evaluate the implied density on a
   3D grid covering and exceeding the observed region; reject parameter sets
   with negative density in the relevant domain.
3. For bar/disk models, compare generated orbit families and LOSVDs against a
   published barred benchmark or a known internal reference run.
4. Repeat fits with and without CRcut when counter-rotation or multiple
   kinematic components are plausible.
5. Repeat fits with different regularisation strengths and report parameter
   sensitivity.
6. If using `NFW_m200_c`, state the cosmology and the exact `H0` convention.
7. Ensure black-hole softening is smaller than the resolution scale and
   dynamically irrelevant outside the innermost unresolved region.
8. Inspect the MGE fit residuals, especially in the centre. A scientifically
   correct MGE solver cannot compensate for an inaccurate photometric model.

## Reference-Output Comparison Status

The repository contains a development test with a saved comparison LOSVD:

- `dynamite/dev_tests/test_orbit_losvds.py`
- `dynamite/dev_tests/data/comparison_losvd.npz`

That is useful evidence that the project has a regression-style orbit-library
comparison path. I did not execute a fresh full orbit-library generation in
this audit because the active Python environment lacks the scientific Python
stack (`numpy` is not importable in the current shell), and compiling/running
the full Fortran orbit tests would require setting up that environment first.

Therefore, this report is a static scientific-equation audit plus literature
comparison. It is not a replacement for a fresh numerical reproduction test.

## Final Scientific Verdict

The non-rotating triaxial Schwarzschild/MGE core is scientifically credible and
largely matches the published method. I would be comfortable treating it as a
valid implementation of the van den Bosch/Cappellari-style triaxial
Schwarzschild model, subject to normal orbit-library convergence tests.

The highest-priority scientific risk is not the core stellar dynamics. It is
parameter-domain and validation risk: especially the cored logarithmic halo
density positivity, bar-model benchmarking, orbit-library convergence, and
regularisation/CRcut sensitivity.

