! Split from orblib_f_new_mirror.f90 without changing module names.

module binning
    ! Extension to the histogram module.
    ! This module takes care of possible binning of the histogram.
    use numeric_kinds
    implicit none
    private

    ! set's up the binning array's
    public :: binning_setup_direct
    ! Inactive file-reading bin setup is kept below as comments.
    ! The active Python path passes bin maps directly.

    ! deallocate memory
    public :: binning_stop

    ! bin the aperture
    public :: binning_bin

    ! function for binning of type 1
    private :: binning_add_it_up

    ! Type of binning. (0=no binning) (1=simple binning)
    integer(kind=i4b), private, allocatable, dimension(:)   ::  bin_type

    ! The way the boxes should be binned (order,ap)
    integer(kind=i4b), private, allocatable, dimension(:, :) ::  bin_order

    ! The total amount of boxes in the binned boxes
    ! ( actually maxval(binning_order(ap)) )
    integer(kind=i4b), public, allocatable, dimension(:) :: bin_max

    ! size(bin_order(:,ap),1)
    integer(kind=i4b), private, allocatable, dimension(:)   ::  bin_size

contains

    !++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    subroutine binning_stop()
        !----------------------------------------------------------------------
        if (allocated(bin_type)) then
            deallocate (bin_type)
            deallocate (bin_order)
            deallocate (bin_max)
            deallocate (bin_size)
        end if

    end subroutine binning_stop

    !++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    ! INACTIVE LEGACY ROUTINE: Inactive legacy binning-file setup: active Python path uses binning_setup_direct.
    ! Retained as comments for reference; do not call from active direct ABI path.
!     subroutine binning_setup()
!         use aperture, only: aperture_n
!         use file_tools, only: next_content_line
!         !----------------------------------------------------------------------
!         integer(kind=i4b) :: i
!         character(len=80) :: string
!         print *, "  * Starting Binning setup"
!         allocate (bin_type(aperture_n))
!         allocate (bin_max(aperture_n))
!         allocate (bin_size(aperture_n))
!         bin_max(:) = 0
!         bin_size(:) = 0
! 
!         do i = 1, aperture_n
!             print *, "  * What kind of binning for aperture ", i
!             print *, "    0=none 1=added up"
!             do
!                 read *, bin_type(i)
!                 if (bin_type(i) == 1 .or. bin_type(i) == 0) exit
!                 print *, "   - Input incorrect try again!"
!             end do
!             print *, "  * Type:", bin_type(i)
!         end do
! 
!         print *, "  * Reading binning files"
! 
!         do i = 1, aperture_n
!             if (bin_type(i) == 1) then
!                 print *, "  * Aperture: ", i
!                 print *, "  * Give the filename of the binning file."
!                 read *, string
!                 print *, "  * Opening: ", string
!                 open (unit=30 + i, file=string, action="read", status="old"&
!                   &, position="rewind")
!                 string = next_content_line(30 + i)  ! skip comment lines
!                 read (string, *) bin_size(i)
!                 print *, "  * bins in this aperture:", bin_size(i)
!             end if
!         end do
! 
!         allocate (bin_order(maxval(bin_size(:)), aperture_n))
! 
!         bin_order(:, :) = 0
! 
!         do i = 1, aperture_n
!             if (bin_type(i) == 1) then
!                 print *, "  * Reading data of aperture:", i, bin_size(i)
!                 read (unit=30 + i, fmt=*) bin_order(1:bin_size(i), i)
!                 close (unit=30 + i)
!             end if
!         end do
! 
!         do i = 1, aperture_n
!             if (bin_type(i) == 1) then
!                 bin_max(i) = maxval(bin_order(:, i))
!             end if
!         end do
!         print *, "  ** Binning module setup finished."
! 
!     end subroutine binning_setup

    !++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    subroutine binning_setup_direct(aperture_count, bin_type_input, &
                                    bin_size_input, max_bin_size, &
                                    bin_order_input)
        integer(kind=i4b), intent(in) :: aperture_count, max_bin_size
        integer(kind=i4b), intent(in), dimension(aperture_count) :: bin_type_input
        integer(kind=i4b), intent(in), dimension(aperture_count) :: bin_size_input
        integer(kind=i4b), intent(in), dimension(max_bin_size, aperture_count) :: bin_order_input
        integer(kind=i4b) :: i

        print *, "  * Starting direct Binning setup"
        call binning_stop()
        allocate (bin_type(aperture_count))
        allocate (bin_max(aperture_count))
        allocate (bin_size(aperture_count))
        bin_type(:) = bin_type_input(:)
        bin_size(:) = bin_size_input(:)
        bin_max(:) = 0
        allocate (bin_order(max_bin_size, aperture_count))
        bin_order(:, :) = 0
        do i = 1, aperture_count
            if (bin_type(i) == 1) then
                if (bin_size(i) < 1 .or. bin_size(i) > max_bin_size) &
                    stop " Direct binning has invalid bin size"
                bin_order(1:bin_size(i), i) = bin_order_input(1:bin_size(i), i)
                bin_max(i) = maxval(bin_order(1:bin_size(i), i))
            else if (bin_type(i) /= 0) then
                stop " Direct binning type must be 0 or 1"
            end if
        end do
        print *, "  ** direct Binning module setup finished."
    end subroutine binning_setup_direct

    !++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    subroutine binning_bin(ap, h, newsize)
        integer(kind=i4b), intent(in)                     :: ap
        real(kind=dp), intent(in out), dimension(:, :) :: h
        integer(kind=i4b), intent(out)                    :: newsize
        !----------------------------------------------------------------------
        if (bin_type(ap) == 1) then
            call binning_add_it_up(ap, h, newsize)
        else
            newsize = size(h, 1)
        end if

    end subroutine binning_bin

    !++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    subroutine binning_add_it_up(ap, h, newsize)
        integer(kind=i4b), intent(in)                        :: ap
        integer(kind=i4b), intent(out)                       :: newsize
        real(kind=dp), intent(in out), dimension(:, :)    :: h
        !----------------------------------------------------------------------
        real(kind=dp), dimension(0:bin_max(ap), size(h, 2)) :: t
        integer(kind=i4b)                                    :: i

        newsize = bin_max(ap)
        t(:, :) = 0.0_dp
        ! check boundaries
        if (newsize > size(h, 1)) stop "Error: binning_add_it_up: new bin&
             &s are bigger then the original "
        if (size(h, 1) /= bin_size(ap)) stop " Wrong number of bins in a bin"

        do i = 1, size(h, 1)
            t(bin_order(i, ap), :) = t(bin_order(i, ap), :) + h(i, :)
        end do

        ! If you assume nothing, there is no way to do this without
        ! copying it back.
        h(1:newsize, :) = t(1:newsize, :)

    end subroutine binning_add_it_up

end module binning
