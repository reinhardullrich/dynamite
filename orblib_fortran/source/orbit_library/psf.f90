! Split from orblib_f_new_mirror.f90 without changing module names.

module psf
    use numeric_kinds
    implicit none
    private

    ! * Module for the PSF generation.
    ! The way PSF are done in this program is quite simple. We just
    ! take the original point and modify it with a configurable
    ! random gaussian offset (psf_size).

    ! how many psf are there?
    integer(kind=i4b), public                           :: psf_n
    ! kind of psf(psf_n)
    integer(kind=i4b), private, allocatable, dimension(:) :: psf_kind
    ! size of psf for (n,psf)
    real(kind=dp), private, allocatable, dimension(:, :) :: psf_sigma
    ! intensity of the psf(n,psf)
    real(kind=dp), private, allocatable, dimension(:, :) :: psf_iten
    ! (i,j,pf) contains a sigma's in random order for psf pf
    real(kind=dp), private, allocatable, dimension(:, :) :: psf_randomsigma
    ! setupup of psf variables
    public :: psf_setup_direct
    ! generate gaussian psf points of input array.
    public :: psf_gaussian

    public :: psf_stop

    ! Inactive file-reading/calculation helpers are kept below as comments.
    ! The active Python path passes PSF arrays directly.

    ! Generates an array with proportionals sigma's of a MGE-PSF
    private:: psf_sigma_map

contains

    !++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    subroutine psf_stop()
        !----------------------------------------------------------------------
        if (allocated(psf_kind)) then
            deallocate (psf_kind, psf_sigma, psf_iten)
        end if

    end subroutine psf_stop

    !++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    ! INACTIVE LEGACY ROUTINE: Inactive legacy PSF-file setup: active Python path uses psf_setup_direct.
    ! Retained as comments for reference; do not call from active direct ABI path.
!     subroutine psf_setup()
!         use initial_parameters, only: conversion_factor
!         use random_gauss_generator, only: random_gauss_seed
!         !----------------------------------------------------------------------
!         integer(kind=i4b) :: i, j
! 
!         print *, "  ** Setting up PSF module"
!         print *, "  * How many different psf's?"
!         read *, psf_n
!         print *, "   ", psf_n
!         allocate (psf_kind(psf_n))
! 
!         do i = 1, psf_n
!             print *, "  * How many gaussians does the ", i, "psf consist of?"
!             read *, psf_kind(i)
!             print *, psf_kind(i)
!             if (psf_kind(i) < 1) stop "gaussian value too low"
!         end do
! 
!         allocate (psf_sigma(maxval(psf_kind(:)), psf_n))
!         allocate (psf_iten(maxval(psf_kind(:)), psf_n))
! 
!         do i = 1, psf_n
!             print *, "   Intensity, sigma of the gauss for PSF ", i
!             do j = 1, psf_kind(i)
!                 read *, psf_iten(j, i), psf_sigma(j, i)
!                 print *, psf_iten(j, i), psf_sigma(j, i)
!             end do
!         end do
! 
!         ! convert sizes arcsec to km
!         psf_sigma(:, :) = psf_sigma(:, :)*conversion_factor
!         call random_gauss_seed()
!         call psf_sigma_map()
! 
!         print *, "  ** PSF module setup Finished"
! 
!     end subroutine psf_setup

    !++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    subroutine psf_setup_direct(psf_count, max_gauss, psf_kind_input, &
                                psf_iten_input, psf_sigma_input)
        use initial_parameters, only: conversion_factor
        use random_gauss_generator, only: random_gauss_seed
        integer(kind=i4b), intent(in) :: psf_count, max_gauss
        integer(kind=i4b), intent(in), dimension(psf_count) :: psf_kind_input
        real(kind=dp), intent(in), dimension(max_gauss, psf_count) :: psf_iten_input
        real(kind=dp), intent(in), dimension(max_gauss, psf_count) :: psf_sigma_input
        integer(kind=i4b) :: i

        print *, "  ** Setting up PSF module from direct Python input"
        call psf_stop()
        psf_n = psf_count
        allocate (psf_kind(psf_n))
        psf_kind(:) = psf_kind_input(:)
        if (minval(psf_kind(:)) < 1) stop "gaussian value too low"
        allocate (psf_sigma(maxval(psf_kind(:)), psf_n))
        allocate (psf_iten(maxval(psf_kind(:)), psf_n))
        psf_sigma(:, :) = 0.0_dp
        psf_iten(:, :) = 0.0_dp
        do i = 1, psf_n
            psf_iten(1:psf_kind(i), i) = psf_iten_input(1:psf_kind(i), i)
            psf_sigma(1:psf_kind(i), i) = psf_sigma_input(1:psf_kind(i), i)
        end do
        psf_sigma(:, :) = psf_sigma(:, :)*conversion_factor
        call random_gauss_seed()
        call psf_sigma_map()
        print *, "  ** direct PSF module setup Finished"
    end subroutine psf_setup_direct

    !++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    subroutine psf_gaussian(pf, vec, gaus)
        use random_gauss_generator
        integer(kind=i4b), intent(in)               :: pf
        ! input vectors (n,2)
        real(kind=dp), dimension(:, :), intent(in) :: vec
        ! output vectors (n,2)
        real(kind=dp), dimension(:, :), intent(out)::gaus
        !----------------------------------------------------------------------
        real(kind=sp), dimension(size(vec, 1)) :: t
        integer(kind=i4b), dimension(size(vec, 1)) :: ind
        integer(kind=i4b) :: j
        real(kind=dp) :: ran1

        if (psf_kind(pf) == 1) then
            ! One gaussian in this psf
            if (psf_sigma(1, pf) > 1.0_dp) then
                call random_gauss(gaus(:, :))
                gaus(:, :) = vec(:, :) + gaus(:, :)*psf_sigma(1, pf)
            else
                ! psf size is tiny, so no convolution is done.
                gaus(:, :) = vec(:, :)
            end if
        else
            ! MGE PSF. Use the randomsigma to convolve these points
            ! Each sigma has a chance of being used proprotional
            ! to the weight of the corresponding Gaussian component.
            ! M. Cappellari, 14 January 2003
            call random_gauss(gaus(:, :))
            do j = 1, size(vec, 1) ! no forall, want this to be serialized...
                t(j) = ran1(1)
            end do
            ! call random_number(t(:))
            ind = t*(size(vec, 1) - 1) + 1 ! n=size(vec,1) random integers in [1,n]
            forall (j=1:2)
                gaus(:, j) = vec(:, j) + gaus(:, j)*psf_randomsigma(ind(:), pf)
            end forall

        end if

    end subroutine psf_gaussian

    !++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    subroutine psf_sigma_map()
        use integrator, only: integrator_points
        use projection, only: projection_symmetry
        !----------------------------------------------------------------------

        integer(kind=i4b)                          :: pf
        ! input vectors (n,2)
        integer(kind=i4b)                          :: i, j, sizex
        real(kind=dp), dimension(:), allocatable :: weightfl
        integer(kind=i4b), dimension(:), allocatable :: weightint
        ! random sigma's

        print *, "  * Making vectors filled of sigmas for psf convolution."
        sizex = integrator_points*projection_symmetry
        allocate (psf_randomsigma(sizex, psf_n))
        psf_randomsigma(:, :) = 0.0_dp

        do pf = 1, psf_n
            allocate (weightfl(psf_kind(pf)), weightint(psf_kind(pf) + 1))

            ! The weight of each PSF gaussian
            do i = 1, psf_kind(pf)
                weightfl(i) = abs(psf_iten(i, pf))
            end do
            do i = 1, psf_kind(pf)
                ! normalized cumulative sum
                weightint(i + 1) = nint(sum(weightfl(1:i))*((sizex - 1)/sum(weightfl(:)))) + 1
            end do
            ! range [1,sizex]
            weightint(1) = 1_i4b
            weightint(psf_kind(pf) + 1) = sizex

            ! Now we generate an array with the sigmas. Each sigma occurs a
            ! relative weighted amount of times in the array.
            do i = 1, psf_kind(pf)
                do j = weightint(i), weightint(i + 1)
                    psf_randomsigma(j, pf) = psf_sigma(i, pf)
                end do
            end do
            print *, 'Weight divided for psf', pf, ':'
            print *, weightint(:)
            deallocate (weightfl, weightint)
        end do
    end subroutine psf_sigma_map

    !++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    ! INACTIVE LEGACY ROUTINE: Inactive PSF sigma helper: active direct orbit-library loop does not call it.
    ! Retained as comments for reference; do not call from active direct ABI path.
!     subroutine psf_cal_sigma(pf, sigma)
!         integer(kind=i4b), intent(in) :: pf
!         real(kind=dp), intent(out):: sigma
!         !----------------------------------------------------------------------
!         sigma = maxval(psf_sigma(:, pf))
! 
!     end subroutine psf_cal_sigma

end module psf
