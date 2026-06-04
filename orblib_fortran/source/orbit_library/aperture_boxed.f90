! Split from orblib_f_new_mirror.f90 without changing module names.

module aperture_boxed
    !contains the aperture functions for the square pixel boxed apertures
    use numeric_kinds
    implicit none
    private

    real(kind=dp), private, dimension(:, :), allocatable :: ap_box_size, ap_box_begin
    real(kind=dp), private, dimension(:), allocatable :: ap_box_idx, ap_box_idy
    real(kind=dp), private, dimension(:), allocatable :: ap_box_rot
    integer(kind=i4b), private, dimension(:), allocatable :: ap_box_bx

    ! Inactive file-reading helper is kept below as comments.
    ! The active Python path passes aperture arrays directly.

    !figure out in which aperture the points fit.
    public :: aperture_boxed_find

    public :: aper_boxed_stop

    public :: aperture_boxed_setup_direct
    ! Inactive field-boundary helper is kept below as comments.

contains

    !++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    subroutine aper_boxed_stop()
        !----------------------------------------------------------------------
        if (allocated(ap_box_size)) then
            deallocate (ap_box_size, ap_box_begin, ap_box_idx, ap_box_idy, ap_box_rot)
            deallocate (ap_box_bx)
        end if

    end subroutine aper_boxed_stop

    !++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    ! INACTIVE LEGACY ROUTINE: Inactive legacy aperture-file reader: active Python path passes aperture arrays directly.
    ! Retained as comments for reference; do not call from active direct ABI path.
!     subroutine aperture_boxed_readfile(handle, aper_n)
!         use initial_parameters, only: conversion_factor
!         use aperture, only: aperture_size, aperture_start
!         use file_tools, only: next_content_line
!         integer(kind=i4b), intent(in) :: handle, aper_n
!         !----------------------------------------------------------------------
!         integer(kind=i4b), save       :: amount = 0
!         integer(kind=i4b)             :: biny
!         character(len=80)             :: string
!         !temporary array's
!         real(kind=dp), Dimension(:, :), allocatable     :: tr
!         integer(kind=i4b), Dimension(:, :), allocatable :: ti
! 
!         print *, "  * Reading boxed aperture file."
! 
!         amount = amount + 1
! 
!         if (allocated(ap_box_size)) then
!             allocate (tr(amount, 7), ti(amount, 1))
!             tr(:, :) = 0
!             ti(:, :) = 0
!             tr(1:amount - 1, 1:2) = ap_box_size(:, 1:2)
!             tr(1:amount - 1, 3:4) = ap_box_begin(:, 1:2)
!             tr(1:amount - 1, 5) = ap_box_idx(:)
!             tr(1:amount - 1, 6) = ap_box_idy(:)
!             tr(1:amount - 1, 7) = ap_box_rot(:)
!             ti(1:amount - 1, 1) = ap_box_bx(:)
! 
!             deallocate (ap_box_size, ap_box_begin, ap_box_bx)
!             deallocate (ap_box_idx, ap_box_idy, ap_box_rot)
! 
!             allocate (ap_box_size(amount, 2), ap_box_begin(amount, 2))
!             allocate (ap_box_bx(amount), ap_box_idx(amount))
!             allocate (ap_box_idy(amount), ap_box_rot(amount))
! 
!             ap_box_size(:, 1:2) = tr(:, 1:2)
!             ap_box_begin(:, 1:2) = tr(:, 3:4)
!             ap_box_idx(:) = tr(:, 5)
!             ap_box_idy(:) = tr(:, 6)
!             ap_box_rot(:) = tr(:, 7)
!             ap_box_bx(:) = ti(:, 1)
! 
!             deallocate (tr, ti)
!         else
!             allocate (ap_box_size(1, 2), ap_box_begin(1, 2), ap_box_bx(1))
!             allocate (ap_box_idx(1), ap_box_idy(1), ap_box_rot(1))
!         end if
! 
!         print *, "  *  Reading box info"
!         print *, "  *  Order: begin(x,y)"
!         string = next_content_line(handle)
!         read (string, fmt=*) ap_box_begin(amount, 1:2)
!         print *, "      size(x,y) "
!         string = next_content_line(handle)
!         read (string, fmt=*) ap_box_size(amount, 1:2)
!         print *, "      rotation"
!         string = next_content_line(handle)
!         read (string, fmt=*) ap_box_rot(amount)
!         ap_box_rot(amount) = ap_box_rot(amount)*(pi_d/180.0_dp)
!         print *, "      bin(x,y)"
!         string = next_content_line(handle)
!         read (string, fmt=*) ap_box_bx(amount), biny
! 
!         ! convert arcsec into km
!         ap_box_begin(amount, :) = ap_box_begin(amount, :)*conversion_factor
!         ap_box_size(amount, :) = ap_box_size(amount, :)*conversion_factor
! 
!         ap_box_idx(amount) = (ap_box_bx(amount)/ap_box_size(amount, 1))
!         ap_box_idy(amount) = (biny/ap_box_size(amount, 2))
! 
!         aperture_start(aper_n) = amount
!         aperture_size(aper_n) = ap_box_bx(amount)*biny
! 
!         print *, "   Total bins ", aperture_size(aper_n)
!         print *, "   begin      ", ap_box_begin(amount, :)
!         print *, "   size       ", ap_box_size(amount, :)
!         print *, "   rotation   ", ap_box_rot(amount)
!         print *, "   binx       ", ap_box_bx(amount)
!         print *, "   idx,y      ", ap_box_idx(amount), ap_box_idy(amount)
!         print *, " "
!         print *, "  * Finished reading aperture"
! 
!     end subroutine aperture_boxed_readfile

    !++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    subroutine aperture_boxed_setup_direct(aperture_count, ap_begin_input, &
                                           ap_size_input, ap_rot_input, &
                                           ap_binx_input, ap_biny_input)
        use initial_parameters, only: conversion_factor
        use aperture, only: aperture_size, aperture_start
        integer(kind=i4b), intent(in) :: aperture_count
        real(kind=dp), intent(in), dimension(aperture_count, 2) :: ap_begin_input
        real(kind=dp), intent(in), dimension(aperture_count, 2) :: ap_size_input
        real(kind=dp), intent(in), dimension(aperture_count) :: ap_rot_input
        integer(kind=i4b), intent(in), dimension(aperture_count) :: ap_binx_input
        integer(kind=i4b), intent(in), dimension(aperture_count) :: ap_biny_input
        integer(kind=i4b) :: i

        call aper_boxed_stop()
        allocate (ap_box_size(aperture_count, 2), ap_box_begin(aperture_count, 2))
        allocate (ap_box_bx(aperture_count), ap_box_idx(aperture_count))
        allocate (ap_box_idy(aperture_count), ap_box_rot(aperture_count))

        do i = 1, aperture_count
            ap_box_begin(i, :) = ap_begin_input(i, :)*conversion_factor
            ap_box_size(i, :) = ap_size_input(i, :)*conversion_factor
            ap_box_rot(i) = ap_rot_input(i)*(pi_d/180.0_dp)
            ap_box_bx(i) = ap_binx_input(i)
            ap_box_idx(i) = ap_binx_input(i)/ap_box_size(i, 1)
            ap_box_idy(i) = ap_biny_input(i)/ap_box_size(i, 2)
            aperture_start(i) = i
            aperture_size(i) = ap_binx_input(i)*ap_biny_input(i)
        end do
    end subroutine aperture_boxed_setup_direct

    !++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    subroutine aperture_boxed_find(ap, vec, res)
        ! vec is a n*m*2 matrix with vectors.
        ! res is an n*m matrix with has the resulting pixel of each vector
        ! ap is the aperture number.
        use aperture, only: aperture_start
        !use initial_parameters, only : psi_view
        use projection, only: psi_proj
        integer(kind=i4b), intent(in)                          :: ap
        real(kind=dp), dimension(:, :), intent(in)              :: vec
        integer(kind=i4b), dimension(size(vec, 1)), intent(out) :: res
        !----------------------------------------------------------------------
        integer(kind=i4b) :: n, j, bx
        real(kind=dp) :: r1, r2, b1, b2, idx, idy, sx, sy, x, y, t, q
        !real (kind=dp), dimension(size(vec,1)) :: t, q, x, y

        ! The number of this aperture in the memory
        n = aperture_start(ap)

        r1 = cos(-ap_box_rot(n) + pio2_d - psi_proj)
        r2 = sin(-ap_box_rot(n) + pio2_d - psi_proj)

        b1 = ap_box_size(n, 1)
        b2 = ap_box_size(n, 2)
        idx = ap_box_idx(n)
        idy = ap_box_idy(n)
        bx = ap_box_bx(n)
        sx = ap_box_begin(n, 1)
        sy = ap_box_begin(n, 2)

        ! Perform shift after rotation MC, 19/APR/2004
        ! Meanning of ap_box_begin has changed!

        do j = 1, size(vec, 1)
            t = vec(j, 1)
            q = vec(j, 2)
            x = t*r1 - q*r2 - sx
            res(j) = 0!_i4b
            if (x > 0.0_dp .and. x < b1) then
                y = t*r2 + q*r1 - sy
                if (y > 0.0_dp .and. y < b2) then
                    res(j) = int(x*idx) + int(y*idy)*bx + 1!_i4b
                end if
            end if
        end do

    end subroutine aperture_boxed_find

    !++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    ! INACTIVE LEGACY ROUTINE: Inactive field-boundary helper used only by legacy aperture_field.
    ! Retained as comments for reference; do not call from active direct ABI path.
!     subroutine aperture_boxed_field(ap, x, y)
!         use aperture, only: aperture_start
!         integer(kind=i4b), intent(in) :: ap
!         real(kind=dp), intent(out), dimension(:) :: x, y
!         !----------------------------------------------------------------------
!         integer(kind=i4b) :: i, j, n
!         real(kind=dp) :: d, e, f, g, r1, r2
! 
!         ! The number of this aperture in the memory
!         n = aperture_start(ap)
!         r1 = cos(ap_box_rot(n))
!         r2 = sin(ap_box_rot(n))
!         x(:) = 0.0_dp
!         y(:) = 0.0_dp
!         do i = 1, 2
!             f = (i - 1)*ap_box_size(n, 1) + ap_box_begin(n, 1)
!             do j = 1, 2
!                 g = (j - 1)*ap_box_size(n, 2) + ap_box_begin(n, 2)
!                 d = r1*f - r2*g
!                 e = r2*f + r1*g
!                 x(1) = min(d, x(1))
!                 y(1) = min(e, y(1))
!                 x(2) = max(d, x(2))
!                 y(2) = max(e, y(2))
!             end do
!         end do
! 
!     end subroutine aperture_boxed_field

end module aperture_boxed
