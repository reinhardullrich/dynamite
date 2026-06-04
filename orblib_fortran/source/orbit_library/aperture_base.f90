! Split from orblib_f_new_mirror.f90 without changing module names.

module aperture
    use numeric_kinds
    implicit none
    private

    ! Total number of apertures
    integer(kind=i4b), public                          :: aperture_n
    ! Number of apertures with 0d histograms (mass only)
    integer(kind=i4b), public                          :: ap_hist0d_n
    ! histogram dimension for each aperture (0=0D, 1=1D, 2=2D)
    integer(kind=i4b), public, allocatable, dimension(:) :: ap_hist_dim

    ! number of bins in aperture
    integer(kind=i4b), public, allocatable, dimension(:) :: aperture_size
    ! Starting point of the aperture in flat array.
    integer(kind=i4b), public, allocatable, dimension(:) :: aperture_start
    ! To which psf does this aperture belong?
    integer(kind=i4b), public, allocatable, dimension(:) :: aperture_psf
    public :: aper_stop

contains

!++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    subroutine aper_stop()
        !--------------------------------------------------------------
        print *, "  * Stopping aperture module"
        if (allocated(aperture_size)) then
            deallocate (aperture_size)
            deallocate (aperture_start)
            deallocate (aperture_psf)
            deallocate (ap_hist_dim)
        end if
        print *, "  * Aperture module stopped"

    end subroutine aper_stop

end module aperture
