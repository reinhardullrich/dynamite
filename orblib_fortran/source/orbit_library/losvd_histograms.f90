! Split from orblib_f_new_mirror.f90 without changing module names.

module histograms
! Routines for histogram manipulation
    use numeric_kinds
    implicit none
    private

    ! histogram data (aperture,vel)
    real(kind=dp), Dimension(:, :), private, allocatable  :: histogram
    ! hist_basic(n,i) n=aperture number, i=width,center,#bins
    real(kind=dp), Dimension(:, :), public, allocatable  :: hist_basic
    ! Are the velocity bins all the same?
    logical, public                                      :: hist_thesame
    !h_beg,h_end : begin/end of histogram
    !h_bin,width : amount of / width of histogram pixels
    real(kind=dp), Dimension(:), private, allocatable  :: h_beg, h_end, h_width
    integer(kind=i4b), Dimension(:), private, allocatable:: h_bin
    ! h_start(n)  :  where start the first histogram of aperture n
    integer(kind=i4b), Dimension(:), private, allocatable:: h_start
    ! number of polygons/bins in each histogram for each aperture
    integer(kind=i4b), Dimension(:), private, allocatable:: h_blocks
    ! number of histograms
    integer(kind=i4b), private                           :: h_n
    ! number of points stored in histogram ( Used in normalising. )
    real(kind=dp), Dimension(:), private, allocatable     :: h_n_stored
    ! total number of histograms/constraints  after binning
    integer(kind=i4b), private                           :: h_nconstr

    ! routines for writing histogram part of output files
    public :: histogram_write, histogram_setup_write
    public :: histogram_write_compat_sparse

    ! Store velocities in the histogram(n).
    public :: histogram_store

    ! Calculate the velocity bin from the losvd
    public :: histogram_velbin

    ! function to reset the histogram for the next orbit
    public :: histogram_reset

    public :: histogram_stop

    public :: histogram_setup_direct
    ! Inactive legacy file-reading setup/write helpers are kept below as comments.
    ! The active Python path passes histogram/binning arrays directly.

contains

    !++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    subroutine histogram_reset()
        !----------------------------------------------------------------------
        histogram(:, :) = 0.0_dp
        h_n_stored(:) = 0.0_dp

    end subroutine histogram_reset

    !++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    subroutine histogram_setup_write(handle)
        integer(kind=i4b), intent(in) :: handle
        !----------------------------------------------------------------------
        integer(kind=i4b) :: t1
        !write information about the kinematical constraints and velocity histogram
        ! original names: nconstr,nvcube,dvcube
        t1 = hist_basic(1, 3)/2.0_sp ! corrected by Remco 20/JAN/2003
        write (unit=handle) h_nconstr, t1, hist_basic(1, 1)/hist_basic(1, 3)

    end subroutine histogram_setup_write

    !++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    ! INACTIVE LEGACY ROUTINE: Inactive legacy mass-output header helper used only by legacy output_setup.
    ! Retained as comments for reference; do not call from active direct ABI path.
!     subroutine histogram_setup_write_mass(handle)
!         integer(kind=i4b), intent(in) :: handle
!         !----------------------------------------------------------------------
!         write (unit=handle, fmt="(i5)") h_nconstr
! 
!     end subroutine histogram_setup_write_mass

    !++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    subroutine histogram_write(handle, handle_pops)
        use aperture, only: ap_hist_dim
        use binning, only: binning_bin
        integer(kind=i4b), intent(in) :: handle, handle_pops
        !----------------------------------------------------------------------
        integer(kind=i4b)            :: i, bg, ed
        print *, "  * Normalising and Writing histogram data."

        where (h_n_stored(:) > 0.0_dp)
            h_n_stored(:) = 1.0_dp/h_n_stored(:)
        elsewhere
            h_n_stored(:) = 0.0_dp
        end where

        do i = 1, h_n
            bg = h_start(i)
            ed = h_blocks(i) + h_start(i) - 1
            call binning_bin(i, histogram(bg:ed, 1:h_bin(i)), ed)
            ed = h_start(i) - 1 + ed
            !conversion normalizing
            histogram(bg:ed, 1:h_bin(i)) = h_n_stored(i)*histogram(bg:ed, 1:h_bin(i))
            if (handle_pops > 0 .and. ap_hist_dim(i) == 0) then
                if (h_bin(i) /= 1) stop " 0d histogram must have 1 bin only."
                write (unit=handle_pops) histogram(bg:ed, 1:h_bin(i))
            else
                call histogram_write_compat_sparse(handle, i, histogram(bg:ed, 1:h_bin(i)))
            end if
        end do
    end subroutine histogram_write

    !++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    subroutine histogram_write_compat_sparse(handle, i_hist, t)
        integer(kind=i4b), intent(in) :: handle, i_hist
        real(kind=dp), dimension(:, :), intent(in) :: t
        !----------------------------------------------------------------------
        integer(kind=i4b) :: ap, b, e, i, k, bout, eout
        do ap = 1, size(t, 1)
            b = 2*hist_basic(i_hist, 3)
            e = -2*hist_basic(i_hist, 3)
            do i = 1, size(t, 2)
                if (t(ap, i) > 0.0_dp) then
                    b = min(b, i)
                    e = max(e, i)
                end if
            end do

            ! write the relevant information for all velocity histograms to file
            k = hist_basic(i_hist, 3)/2.0_sp + 1.0_sp
            bout = b - k
            eout = e - k
            write (unit=handle) bout, eout
            if (b <= e) write (unit=handle) t(ap, b:e)
        end do

    end subroutine histogram_write_compat_sparse

    !++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    subroutine histogram_velbin(pf, vel, bin)
        use aperture, only: aperture_psf
        integer(kind=i4b), intent(in) :: pf
        real(kind=dp), dimension(:), intent(in) :: vel
        integer(kind=i4b), dimension(size(vel)), intent(out) :: bin
        !----------------------------------------------------------------------
        integer(kind=i4b) :: i, ap, bins
        real(kind=dp) :: v, beg, width, hend
        ! find an aperture which is in this pf
        do i = 1, h_n
            if (aperture_psf(i) == pf) ap = i
        end do

        beg = h_beg(ap)
        hend = h_end(ap)
        width = h_width(ap)
        bins = h_bin(ap)

        do i = 1, size(vel)
            v = vel(i)
            if (v > beg) then
                if (v < hend) then
                    ! photon lies within the velocity range
                    bin(i) = int(((v - beg)/width)) + 1
                else
                    ! photon lies above the range
                    ! Assign photon to the last velocity bin.
                    bin(i) = bins
                end if
            else
                ! photon lies below the velocity range
                ! assign to first bin
                bin(i) = 1
            end if
        end do

    end subroutine histogram_velbin

    !++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    subroutine histogram_store(ap, n, velb, tot)
        integer(kind=i4b), intent(in)  :: ap
        integer(kind=i4b)                                   :: i, k, v
        integer(kind=i4b), dimension(:), intent(in)  :: n
        integer(kind=i4b), dimension(size(n, 1)), intent(in)  :: velb
        integer(kind=i4b), intent(in)  :: tot
        !----------------------------------------------------------------------
        !update number of points stored (including points not stored)
        ! For normalising.
        h_n_stored(ap) = h_n_stored(ap) + tot

        do i = 1, size(n, 1)
            k = n(i)
            if (k /= 0) then
                k = k + h_start(ap) - 1
                v = velb(i)
                histogram(k, v) = histogram(k, v) + 1.0_dp
            end if
        end do

    end subroutine histogram_store

    !++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    subroutine histogram_stop()
        use binning, only: binning_stop
        !----------------------------------------------------------------------
        if (allocated(h_bin)) then
            deallocate (hist_basic, h_beg, h_end, h_bin, h_width, h_start, histogram)
        end if
        call binning_stop()

    end subroutine histogram_stop

    !++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    ! INACTIVE LEGACY ROUTINE: Inactive legacy histogram-file setup: active Python path uses histogram_setup_direct.
    ! Retained as comments for reference; do not call from active direct ABI path.
!     subroutine histogram_setup()
!         use aperture, only: aperture_n, aperture_size, aperture_psf, ap_hist_dim
!         use binning, only: binning_setup, bin_max
!         use psf, only: psf_n
!         !----------------------------------------------------------------------
!         integer(kind=i4b)  :: i, j, ap
!         real(kind=dp)  :: width, center, bins
! 
!         print *, "  * Starting Histogram module"
!         h_n = aperture_n
!         allocate (hist_basic(h_n, 3), h_beg(h_n), h_end(h_n), h_bin(h_n))
!         allocate (h_width(h_n), h_start(h_n), h_n_stored(h_n), h_blocks(h_n))
! 
!         do i = 1, psf_n
!             print *, "  * Give for psf ", i, " the histogram width, center and"
!             print *, "    amount of bins"
!             read *, width, center, bins
!             print *, width, center, bins
!             if (width <= 0) stop " Width to small"
!             if (bins < 1) stop " Too few bins"
!             do j = 1, h_n
!                 if (aperture_psf(j) == i) then
!                     hist_basic(j, 1) = width
!                     hist_basic(j, 2) = center
!                     hist_basic(j, 3) = bins
!                 end if
!             end do
!         end do
! 
!         h_beg(:) = hist_basic(:, 2) - (0.5_dp*hist_basic(:, 1))
!         h_end(:) = hist_basic(:, 2) + (0.5_dp*hist_basic(:, 1))
!         h_bin(:) = hist_basic(:, 3)
!         h_width(:) = hist_basic(:, 1)/hist_basic(:, 3)
! 
!         allocate (histogram(sum(aperture_size(:)), maxval(h_bin(:))))
!         print *, "  * Histogram size : ", size(histogram), "=", size(histogram, 1), "*",&
!              & size(histogram, 2)
! 
!         h_blocks(:) = aperture_size(:)
!         i = 1
! 
!         do ap = 1, h_n
!             h_start(ap) = i
!             i = i + h_blocks(ap)
!         end do
! 
!         call histogram_reset()
!         call binning_setup()
! 
!         ! Figure out how many histograms there are.
!         h_nconstr = 0
!         do ap = 1, h_n
!             if (ap_hist_dim(ap) == 1) then  ! only count 1d histograms (required by LegacyWeightSolver)
!                 if (bin_max(ap) == 0) then
!                     h_nconstr = h_nconstr + aperture_size(ap)
!                 else
!                     h_nconstr = h_nconstr + bin_max(ap)
!                 end if
!             end if
!         end do
! 
!         ! Figure out if all the velocityhistograms are the same.
!         hist_thesame = .true.
!         width = hist_basic(1, 1)
!         center = hist_basic(1, 2)
!         bins = hist_basic(1, 3)
!         do ap = 2, h_n
!             if (width /= hist_basic(ap, 1)) hist_thesame = .false.
!             if (center /= hist_basic(ap, 2)) hist_thesame = .false.
!             if (bins /= hist_basic(ap, 3)) hist_thesame = .false.
!         end do
!         if (hist_thesame) then
!             print *, "  * All velocity-bins are the same"
!         else
!             print *, "  * Velocity-bins are not the same. The standard NNLS will not"
!             print *, "  * understand the ouput correctly (exception: pops data "
!             print *, "  * velocity-bins may differ)."
!         end if
!         print *, "  ** Histogram module setup finished"
! 
!     end subroutine histogram_setup

    !++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    subroutine histogram_setup_direct(hist_width_input, hist_center_input, &
                                      hist_bins_input, aperture_count, &
                                      bin_type_input, bin_size_input, &
                                      max_bin_size, bin_order_input)
        use aperture, only: aperture_n, aperture_size, aperture_psf, ap_hist_dim
        use binning, only: binning_setup_direct, bin_max
        use psf, only: psf_n
        real(kind=dp), intent(in), dimension(psf_n) :: hist_width_input
        real(kind=dp), intent(in), dimension(psf_n) :: hist_center_input
        integer(kind=i4b), intent(in), dimension(psf_n) :: hist_bins_input
        integer(kind=i4b), intent(in) :: aperture_count, max_bin_size
        integer(kind=i4b), intent(in), dimension(aperture_count) :: bin_type_input
        integer(kind=i4b), intent(in), dimension(aperture_count) :: bin_size_input
        integer(kind=i4b), intent(in), dimension(max_bin_size, aperture_count) :: bin_order_input
        integer(kind=i4b)  :: i, j, ap
        real(kind=dp)  :: width, center, bins

        print *, "  * Starting direct Histogram module"
        call histogram_stop()
        h_n = aperture_n
        allocate (hist_basic(h_n, 3), h_beg(h_n), h_end(h_n), h_bin(h_n))
        allocate (h_width(h_n), h_start(h_n), h_n_stored(h_n), h_blocks(h_n))

        do i = 1, psf_n
            width = hist_width_input(i)
            center = hist_center_input(i)
            bins = hist_bins_input(i)
            if (width <= 0) stop " Width to small"
            if (bins < 1) stop " Too few bins"
            do j = 1, h_n
                if (aperture_psf(j) == i) then
                    hist_basic(j, 1) = width
                    hist_basic(j, 2) = center
                    hist_basic(j, 3) = bins
                end if
            end do
        end do

        h_beg(:) = hist_basic(:, 2) - (0.5_dp*hist_basic(:, 1))
        h_end(:) = hist_basic(:, 2) + (0.5_dp*hist_basic(:, 1))
        h_bin(:) = hist_basic(:, 3)
        h_width(:) = hist_basic(:, 1)/hist_basic(:, 3)

        allocate (histogram(sum(aperture_size(:)), maxval(h_bin(:))))
        h_blocks(:) = aperture_size(:)
        i = 1
        do ap = 1, h_n
            h_start(ap) = i
            i = i + h_blocks(ap)
        end do

        call histogram_reset()
        call binning_setup_direct(aperture_count, bin_type_input, &
                                  bin_size_input, max_bin_size, &
                                  bin_order_input)

        h_nconstr = 0
        do ap = 1, h_n
            if (ap_hist_dim(ap) == 1) then
                if (bin_max(ap) == 0) then
                    h_nconstr = h_nconstr + aperture_size(ap)
                else
                    h_nconstr = h_nconstr + bin_max(ap)
                end if
            end if
        end do

        hist_thesame = .true.
        width = hist_basic(1, 1)
        center = hist_basic(1, 2)
        bins = hist_basic(1, 3)
        do ap = 2, h_n
            if (width /= hist_basic(ap, 1)) hist_thesame = .false.
            if (center /= hist_basic(ap, 2)) hist_thesame = .false.
            if (bins /= hist_basic(ap, 3)) hist_thesame = .false.
        end do
        print *, "  ** direct Histogram module setup finished"
    end subroutine histogram_setup_direct

end module histograms
