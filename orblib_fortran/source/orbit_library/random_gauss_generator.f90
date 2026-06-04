!######################################################################
!
! Written by Remco van den Bosch <bosch@strw.leidenuniv.nl>
! Sterrewacht Leiden, The Netherlands
!
! HISTORY:
!
! V1.4: MC Verification of intrinsic velocity moments calculation.
!     Fixed significant bug in mergrid_store. Slightly revised
!     implementation
!     to make it easier to check. Independent test of the results
!      still needed
! V2.0: RvdB. Fork for the Triaxial orbit library code.
! V2.0.1 : Changed quadrant grid bins to have more bins.
! V2.0.2 : fix 10**rlogmax in bin setup of qgrid_setup
!          add internal moments
! V2.0.3 : change the zeroth moment grid
! V2.0.4 : add zero psf routine
!          fixed projection
! V3.0.0 : Make intrinisic grid size recipe to be able to numerically
!          Fit the intrinsic mass.
!     RvdB, Leiden, oktober/2005
!
!######################################################################
! $Id: orblib_f.f90,v 1.3 2011/10/25 08:48:45 bosch Exp $

! Written by Remco van den Bosch <bosch@strw.leidenuniv.nl>
! Sterrewacht Leiden, The Netherlands

!++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
! Note on rotating bar code:
! The modified or added lines are commented by ! (BT)
! In this file, the modified parts are:
! 1- Integration of orbits in a rotating frame in case of (Omega != 0).
! 2- Applying 4-fold symmetry instead of 8-fold symmetry mirroring and symmetrizing if (Omega != 0).
! 3- if (Omega != 0), Sorting information of each orbit e.g. Circularity and ... during integration.
! created file called  _orb_info.out for each library
!
! adapted from code originally by Behzad Tahmasebzadeh, July 2023
!++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

module random_gauss_generator
    use numeric_kinds
    implicit none
    private

    ! Seeds the NR random generator
    public :: random_gauss_seed

    ! F version of the gaussian random generator
    ! generate gaussians for a n*m*o array with a width
    public :: random_gauss

    !Generate one 2d gaussian deviate with sigma "width"
    private :: gaussdev

contains

! adapted from NR2.
! Internal computation in SP for speed
    !++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    subroutine gaussdev(x)
        real(kind=dp), intent(out), dimension(:) :: x
        !----------------------------------------------------------------------
        real(kind=sp), dimension(2) :: v
        real(kind=sp) :: rsq
        real(kind=dp) :: ran1

        do
            v(1) = ran1(1)
            v(2) = ran1(1)
            ! call random_number(v)
            v = 2.0_sp*v - 1.0_sp
            rsq = sum(v**2)
            if (rsq > 0.0_sp .and. rsq < 1.0_sp) exit
        end do
        x = v*sqrt(-2.0_sp*log(rsq)/rsq)

    end subroutine gaussdev

    !++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    subroutine random_gauss_seed()
        !----------------------------------------------------------------------
        logical, save :: initialized = .false.

        print *, "  * Seeding native Random generator"
        if (.not. initialized) then
            ! START reproducible orbit library
            ! uncomment the following line for stochastic orbit library creation
            !call random_seed()
            ! END reproducible orbit library
            print *, "  * Internal Compiler random functions needs to be checked."
            initialized = .true.
        end if

    end subroutine random_gauss_seed

    !++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    subroutine random_gauss(t)
        real(kind=dp), dimension(:, :), intent(out) :: t
        !----------------------------------------------------------------------
        integer(kind=i4b)                              :: k

        do k = 1, size(t, 1)
            call gaussdev(t(k, :))
        end do

    end subroutine random_gauss

end module random_gauss_generator
