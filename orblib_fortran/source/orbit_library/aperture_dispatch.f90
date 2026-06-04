! Split from orblib_f_new_mirror.f90 without changing module names.

module aperture_routines
    ! Basic aperture routines
    ! This module is the overhead to call the aperture_* functions
    use numeric_kinds
    use aperture
    implicit none
    private

    public :: aperture_setup_direct

    public :: aperture_stop

    ! Inactive file-reading/field-boundary helpers are kept below as comments.
    ! The active Python path passes aperture arrays directly.

contains

    !++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    ! INACTIVE LEGACY ROUTINE: Inactive legacy aperture-file setup: active Python path uses aperture_setup_direct.
    ! Retained as comments for reference; do not call from active direct ABI path.
!     subroutine aperture_setup()
!         use aperture_boxed, only: aperture_boxed_readfile
!         use psf, only: psf_n
!         !----------------------------------------------------------------------
!         integer(kind=i4b)  :: i, handle = 11
!         character(len=80) :: file, string
!         print *, "  **Aperture setup module"
!         print *, "  * How many different apertures?  :"
!         read *, aperture_n
! 
!         allocate (aperture_size(aperture_n))
!         allocate (aperture_start(aperture_n))
!         allocate (aperture_psf(aperture_n))
!         allocate (ap_hist_dim(aperture_n))
!         print *, "  * using ", aperture_n, " aperture(s)"
! 
!         ap_hist0d_n = 0
!         do i = 1, aperture_n
!             print *, "  * What's the filename of the ", i, " aperture file ? :"
!             read *, file
!             print *, "  * Reading ", file
! 
!             open (unit=handle, file=file, action="read", status="old"&
!                  &, position="rewind")
!             string = "#counter_rotation_boxed_aperturefile_version_2"
!             print *, "  * Assuming type ", string
!             call aperture_boxed_readfile(handle, i)
!             close (unit=handle)
!             print *, "  * To which psf does this aperture belong?"
!             read *, aperture_psf(i)
!             if (aperture_psf(i) < 1 .or. aperture_psf(i) > psf_n) then
!                 stop " That PSF does not exist!"
!             end if
! 
!             ! print *, "  * Histogram dimensions for this aperture (0, 1, or 2)?"
!             print *, "  * Histogram dimensions for this aperture (0 or 1)?"
!             read *, ap_hist_dim(i)
!             print *, "  * The histograms are ", ap_hist_dim(i), " dimensional."
!             ! if (ap_hist_dim(i) < 0 .or. ap_hist_dim(i) > 2) then
!             !     stop "  Histogram dimension must be 0, 1, or 2!"
!             if (ap_hist_dim(i) < 0 .or. ap_hist_dim(i) > 1) then
!                 stop "  Histogram dimension must be 0 or 1!"
!             end if
!             if (ap_hist_dim(i) == 0) ap_hist0d_n = ap_hist0d_n + 1
!         end do
!         print *, "  ** aperture setup finished"
! 
!     end subroutine aperture_setup

    !++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    subroutine aperture_setup_direct(aperture_count, ap_begin_input, &
                                     ap_size_input, ap_rot_input, &
                                     ap_binx_input, ap_biny_input, &
                                     aperture_psf_input, ap_hist_dim_input)
        use aperture_boxed, only: aperture_boxed_setup_direct
        use psf, only: psf_n
        integer(kind=i4b), intent(in) :: aperture_count
        real(kind=dp), intent(in), dimension(aperture_count, 2) :: ap_begin_input
        real(kind=dp), intent(in), dimension(aperture_count, 2) :: ap_size_input
        real(kind=dp), intent(in), dimension(aperture_count) :: ap_rot_input
        integer(kind=i4b), intent(in), dimension(aperture_count) :: ap_binx_input
        integer(kind=i4b), intent(in), dimension(aperture_count) :: ap_biny_input
        integer(kind=i4b), intent(in), dimension(aperture_count) :: aperture_psf_input
        integer(kind=i4b), intent(in), dimension(aperture_count) :: ap_hist_dim_input

        print *, "  ** Setting up aperture module from direct Python input"
        call aper_stop()
        aperture_n = aperture_count
        allocate (aperture_size(aperture_n))
        allocate (aperture_start(aperture_n))
        allocate (aperture_psf(aperture_n))
        allocate (ap_hist_dim(aperture_n))
        aperture_psf(:) = aperture_psf_input(:)
        ap_hist_dim(:) = ap_hist_dim_input(:)
        if (minval(aperture_psf(:)) < 1 .or. maxval(aperture_psf(:)) > psf_n) &
            stop " Direct aperture references an unknown PSF"
        if (minval(ap_hist_dim(:)) < 0 .or. maxval(ap_hist_dim(:)) > 1) &
            stop " Direct aperture histogram dimension must be 0 or 1"
        ap_hist0d_n = count(ap_hist_dim(:) == 0)
        call aperture_boxed_setup_direct(aperture_count, ap_begin_input, &
                                         ap_size_input, ap_rot_input, &
                                         ap_binx_input, ap_biny_input)
        print *, "  ** direct aperture setup finished"
    end subroutine aperture_setup_direct

    !++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    subroutine aperture_stop()
        use aperture, only: aper_stop
        use aperture_boxed, only: aper_boxed_stop
        !----------------------------------------------------------------------
        call aper_stop()
        call aper_boxed_stop()

    end subroutine aperture_stop

    !++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    ! INACTIVE LEGACY ROUTINE: Inactive field-boundary helper: active direct orbit-library loop does not call it.
    ! Retained as comments for reference; do not call from active direct ABI path.
!     subroutine aperture_field(pf, minx, maxx, miny, maxy)
!         use aperture, only: aperture_n, aperture_psf
!         use aperture_boxed, only: aperture_boxed_field
!         use psf, only: psf_n
!         integer(kind=i4b), intent(in) :: pf
!         real(kind=dp), intent(out) :: maxx, minx, miny, maxy
!         !----------------------------------------------------------------------
!         logical, save :: initialized = .false.
!         real(kind=dp), dimension(:, :), allocatable, save :: f_x, f_y
!         integer(kind=i4b) :: i, pfn
!         real(kind=dp), dimension(2) :: x, y
! 
!         if (.not. initialized) then
!             allocate (f_x(psf_n, 2), f_y(psf_n, 2))
!             f_x(:, :) = 0.0_dp
!             f_y(:, :) = 0.0_dp
!             do i = 1, aperture_n
!                 pfn = aperture_psf(i)
!                 call aperture_boxed_field(i, x, y)
!                 f_x(pfn, 1) = min(f_x(pfn, 1), x(1))
!                 f_x(pfn, 2) = max(f_x(pfn, 2), x(2))
!                 f_y(pfn, 1) = min(f_y(pfn, 1), y(1))
!                 f_y(pfn, 2) = max(f_y(pfn, 2), y(2))
!             end do
!             initialized = .true.
!         end if
! 
!         minx = f_x(pf, 1)
!         miny = f_y(pf, 1)
!         maxx = f_x(pf, 2)
!         maxy = f_y(pf, 2)
! 
!     end subroutine aperture_field

end module aperture_routines
