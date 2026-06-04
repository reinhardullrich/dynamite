! Split from orblib_f_new_mirror.f90 without changing module names.

module quadrantgrid
    use numeric_kinds
    implicit none
    private

    real(kind=dp), private, allocatable, dimension(:, :, :, :) :: quadrant_light
    real(kind=dp), private, allocatable, dimension(:) :: quad_lr, quad_lr2
    real(kind=dp), private, allocatable, dimension(:) :: quad_lth, quad_ltan2th
    real(kind=dp), private, allocatable, dimension(:) :: quad_lph, quad_ltanph
    real(kind=dp), private, dimension(3, 8, 5) :: qgrid_vsgn
    real(kind=dp), private, dimension(3, 8) :: qgrid_psgn
    logical, private :: qgrid_rotating_frame = .false.

    ! Signs of the (vx,vy,vz) for each Projection and type of Orbit.
    ! 8-fold symmetry for non-rotating models.
    real(kind=dp), private, dimension(3, 8, 5), &
        parameter :: qgrid_vsgn_nonrotating = reshape((/ &
                                    ! X tubes
                                    1, 1, 1, -1, 1, 1, 1, 1, -1, -1, 1, -1, &
                                    -1, -1, 1, 1, -1, 1, -1, -1, -1, 1, -1, -1, &
                                    ! Y tubes
                                    1, 1, 1, 1, -1, -1, 1, 1, -1, 1, -1, 1, &
                                    -1, -1, 1, -1, 1, -1, -1, -1, -1, -1, 1, 1, &
                                    ! Z tubes
                                    1, 1, 1, 1, -1, -1, -1, -1, 1, -1, 1, -1, &
                                    1, 1, -1, 1, -1, 1, -1, -1, -1, -1, 1, 1, &
                                    ! Boxed
                                    1, 1, 1, -1, 1, 1, -1, -1, 1, 1, -1, 1, &
                                    1, 1, -1, -1, 1, -1, -1, -1, -1, 1, -1, -1, &
                                    ! Stochastic
                                    1, 1, 1, -1, 1, 1, -1, -1, 1, 1, -1, 1, &
                                    1, 1, -1, -1, 1, -1, -1, -1, -1, 1, -1, -1/), (/3, 8, 5/))

    ! Signs of the x,y,z for each projection: psgn([x,y,z], project).
    real(kind=dp), private, dimension(3, 8), &
        parameter :: qgrid_psgn_nonrotating = reshape((/ &
                                    1, 1, 1, -1, 1, 1, -1, -1, 1, 1, -1, 1, &
                                    1, 1, -1, -1, 1, -1, -1, -1, -1, 1, -1, -1/), (/3, 8/))

    ! Signs of the (vx,vy,vz) for each Projection and type of Orbit.
    ! 4-fold symmetry in case of rotating frame.
    real(kind=dp), private, dimension(3, 8, 5), &
        parameter :: qgrid_vsgn_rotating = reshape((/  &
             ! X tubes
             1 , 1 , 1    ,1 , 1 , 1  ,  -1 , -1 ,1  ,   -1 , -1 , 1 , &
             1 ,1 , -1    ,1 ,1 , -1  , -1 ,-1 ,-1  ,  -1 ,-1 , -1 , &
             ! Y tubes
             1 , 1 , 1    , 1 , 1 ,1  ,  1 , 1 ,-1  ,  1 , 1 , -1 , &
             -1 , -1 , 1   ,-1 , -1 ,1  , -1 ,-1 ,-1  , -1 ,-1 , -1 , &
             ! Z tubes
             1 , 1 , 1    , 1 ,1 , 1  , -1 ,-1 , 1  , -1 , -1 , 1 , &
             1 , 1 ,-1    , 1 ,1 ,-1  , -1 ,-1 ,-1  , -1 , -1 ,-1 , &
             ! Boxed
             1 , 1 , 1    ,1 , 1 , 1  , -1 ,-1 , 1  ,  -1 ,-1 , 1 , &
             1 , 1 ,-1    ,1 , 1 ,-1  , -1 ,-1 ,-1  ,  -1 ,-1 ,-1 , &
             ! Stochastic
             1 , 1 , 1    ,1 , 1 , 1  , -1 ,-1 , 1  ,  -1 ,-1 , 1 , &
             1 , 1 ,-1    ,1 , 1 ,-1  , -1 ,-1 ,-1  ,  -1 ,-1 ,-1 /),(/3,8,5/))

    ! Signs of the x,y,z for each projection: psgn([x,y,z], project).
    real(kind=dp), private, dimension(3, 8), &
        parameter :: qgrid_psgn_rotating = reshape((/  &
             1 , 1 , 1   , 1 , 1 , 1   , -1 , -1 , 1 ,  -1 , -1 , 1 , &
             1 , 1 ,-1   , 1 , 1 ,-1  , -1 , -1 ,-1 ,  -1 , -1 ,-1 /),(/3,8/))

    ! Inactive qgrid_stop helper is kept below as comments.
    public  :: qgrid_write
    public  :: qgrid_setup_write
    public  :: qgrid_reset
    ! Store points in the grid.
    public  :: qgrid_store
    public  :: qgrid_setup
contains

    !++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    ! INACTIVE LEGACY ROUTINE: Inactive qgrid cleanup helper: active shutdown does not call it.
    ! Retained as comments for reference; do not call from active direct ABI path.
!     subroutine qgrid_stop()
!         !----------------------------------------------------------------------
!         if (allocated(quadrant_light)) then
!             deallocate (quadrant_light)
!             deallocate (quad_lr, quad_lth, quad_lph)
!             deallocate (quad_lr2, quad_ltan2th, quad_ltanph)
!         end if
! 
!     end subroutine qgrid_stop

    !++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    subroutine qgrid_reset()
        !----------------------------------------------------------------------
        quadrant_light(:, :, :, :) = 0.0_dp
    end subroutine qgrid_reset

    !++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    subroutine qgrid_setup()
        use initial_parameters, only: Omega, rLogMin, rLogMax, sigobs_km &
                                      , quad_nr, quad_nth, quad_nph
        !----------------------------------------------------------------------
        integer(kind=i4b) :: i
        print *, "  ** Octant grid module setup"

        print *, "  ** Grid dimension:"
        print *, quad_nr, quad_nth, quad_nph

        allocate (quadrant_light(16, quad_nph, quad_nth, quad_nr))
        allocate (quad_lr(quad_nr + 1), quad_lr2(quad_nr + 1))
        allocate (quad_lth(quad_nth + 1), quad_ltan2th(quad_nth + 1))
        allocate (quad_lph(quad_nph + 1), quad_ltanph(quad_nph + 1))

        ! Define a grid in such a way that the boundaries define all possible bins
        ! This also means that there are N+1 boundaries for N bins.

        do i = 2, quad_nr
            quad_lr(i) = 10.0_dp**(rlogmin + (rLogMax - rlogmin + alog10(0.5))*(i - 1.0) &
                                   /(quad_nr - 0.0))
        end do
        quad_lr(1) = 0.0_dp
        quad_lr(quad_nr + 1) = max(10.0_dp**rLogMax*100.0_dp, maxval(sigobs_km)*10.0_dp)

        ! make a lr_squared array for quick computation
        quad_lr2(:) = quad_lr(:)**2_dp

        ! Define the angular bins
        do i = 2, quad_nth
            quad_lth(i) = pio2_d*(i - 1.0_dp)/(quad_nth)
        end do
        quad_lth(1) = 0.0_dp
        quad_lth(quad_nth + 1) = pio2_d

        ! define the angular bins
        do i = 2, quad_nph
            quad_lph(i) = pio2_d*(i - 1.0_dp)/(quad_nph)
        end do
        quad_lph(1) = 0.0_dp
        quad_lph(quad_nph + 1) = pio2_d

        ! make a lr_squared and tan arrays for quick computation
        quad_lr2(:) = quad_lr(:)**2.0_dp
        quad_ltanph(:) = tan(quad_lph(:))
        quad_ltan2th(:) = tan(quad_lth(:))**2.0_dp

        qgrid_rotating_frame = Omega /= 0.0_dp
        qgrid_vsgn = qgrid_vsgn_nonrotating
        qgrid_psgn = qgrid_psgn_nonrotating
        if (qgrid_rotating_frame) then
            qgrid_vsgn = qgrid_vsgn_rotating
            qgrid_psgn = qgrid_psgn_rotating
        end if

        call qgrid_reset()

    end subroutine qgrid_setup

    !++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    subroutine qgrid_store(proj, vel, type)
        ! proj (n, (x,y,z) )
        real(kind=dp), dimension(:, :), intent(in) :: proj, vel
        integer(kind=i4b), intent(in)                       :: type
        !----------------------------------------------------------------------
        real(kind=dp)      :: r2, theta, phi, x, y, z, vx, vy, vz
        integer(kind=i4b) :: i, j, n1, n2, n3, store_type
        integer(kind=i4b), save ::ir = 1, ith = 1, iph = 1

        ! Hunt assumes open boundaries, but our boundaries are closed
        ! So we dont give the outer boundaries to hunt.

        n1 = size(quad_lr) - 1
        n2 = size(quad_lth) - 1
        n3 = size(quad_lph) - 1

        select case (type)
        case (1)
            store_type = 0
        case (3)
            store_type = 1
        case default
            store_type = 2
        end select

        do i = 1, size(proj, 1) ! loop over photons

            j = qgrid_positive_octant_projection_index(proj(i, 1), proj(i, 2), proj(i, 3), qgrid_rotating_frame)
            if (j == 0) cycle

            x = proj(i, 1)*qgrid_psgn(1, j)
            y = proj(i, 2)*qgrid_psgn(2, j)
            z = proj(i, 3)*qgrid_psgn(3, j)
            vx = vel(i, 1)*qgrid_vsgn(1, j, type)
            vy = vel(i, 2)*qgrid_vsgn(2, j, type)
            vz = vel(i, 3)*qgrid_vsgn(3, j, type)

            r2 = (x*x + y*y + z*z)
            theta = (x*x + y*y)/(z*z) ! sqrt atan
            phi = y/x               ! atan

            call hunt(quad_lr2(2:n1), n1 - 1, r2, ir)
            call hunt(quad_ltan2th(2:n2), n2 - 1, theta, ith)
            call hunt(quad_ltanph(2:n3), n3 - 1, phi, iph)

            ! store properties of the photon in the grid
            quadrant_light(1:13, iph + 1, ith + 1, ir + 1) = &
                quadrant_light(1:13, iph + 1, ith + 1, ir + 1) + &
                (/1.0_dp, x, y, z, vx, vy, vz, vx*vx, vy*vy, vz*vz, vx*vy, vy*vz, vz*vx/)

            ! store orbit type
            quadrant_light(14 + store_type, iph + 1, ith + 1, ir + 1) = &
                quadrant_light(14 + store_type, iph + 1, ith + 1, ir + 1) + 1
        end do

    end subroutine qgrid_store

    pure function qgrid_positive_octant_projection_index(x, y, z, rotating_frame) result(projection_index)
        real(kind=dp), intent(in) :: x, y, z
        logical, intent(in) :: rotating_frame
        integer(kind=i4b) :: projection_index
        integer(kind=i4b) :: x_index, y_index, z_index, xy_index
        integer(kind=i4b), parameter :: nonrotating_projection(2, 2, 2) = reshape((/ &
            7_i4b, 8_i4b, 6_i4b, 5_i4b, &
            3_i4b, 4_i4b, 2_i4b, 1_i4b /), (/2, 2, 2/))
        integer(kind=i4b), parameter :: rotating_projection(2, 2) = reshape((/ &
            7_i4b, 5_i4b, 3_i4b, 1_i4b /), (/2, 2/))

        projection_index = 0_i4b

        ! The old loop never stored x==0 or z==0 because the selected octant
        ! requires x > 0 and z > 0 before dividing by x and z.
        if (x == 0.0_dp .or. z == 0.0_dp) return

        z_index = merge(2_i4b, 1_i4b, z > 0.0_dp)

        if (rotating_frame) then
            if (x > 0.0_dp .and. y >= 0.0_dp) then
                xy_index = 2_i4b
            else if (x < 0.0_dp .and. y <= 0.0_dp) then
                xy_index = 1_i4b
            else
                return
            end if
            projection_index = rotating_projection(xy_index, z_index)
        else
            x_index = merge(2_i4b, 1_i4b, x > 0.0_dp)
            y_index = merge(2_i4b, 1_i4b, y >= 0.0_dp)
            projection_index = nonrotating_projection(x_index, y_index, z_index)
        end if

    end function qgrid_positive_octant_projection_index

    !++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    subroutine qgrid_setup_write(hdl)
        integer(kind=i4b), intent(in) :: hdl
        !----------------------------------------------------------------------
        ! Write the information about the meridional plane grid. .

        ! remember that N bins have N+1 boundaries
        write (unit=hdl) size(quadrant_light, 1), size(quad_lph) - 1, size(quad_lth) - 1, size(quad_lr) - 1
        write (unit=hdl) quad_lr(:)
        write (unit=hdl) quad_lth(:)
        write (unit=hdl) quad_lph(:)

    end subroutine qgrid_setup_write

    !++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    subroutine qgrid_write(hdl)
        integer(kind=i4b), intent(in):: hdl
        real(kind=dp) :: norm
        !----------------------------------------------------------------------

        print *, "  * Writing intrisic moment octant"

        where (quadrant_light(1, :, :, :) /= 0.0_dp)
            quadrant_light(2, :, :, :) = quadrant_light(2, :, :, :)/quadrant_light(1, :, :, :)
            quadrant_light(3, :, :, :) = quadrant_light(3, :, :, :)/quadrant_light(1, :, :, :)
            quadrant_light(4, :, :, :) = quadrant_light(4, :, :, :)/quadrant_light(1, :, :, :)
            quadrant_light(5, :, :, :) = quadrant_light(5, :, :, :)/quadrant_light(1, :, :, :)
            quadrant_light(6, :, :, :) = quadrant_light(6, :, :, :)/quadrant_light(1, :, :, :)
            quadrant_light(7, :, :, :) = quadrant_light(7, :, :, :)/quadrant_light(1, :, :, :)
            quadrant_light(8, :, :, :) = quadrant_light(8, :, :, :)/quadrant_light(1, :, :, :)
            quadrant_light(9, :, :, :) = quadrant_light(9, :, :, :)/quadrant_light(1, :, :, :)
            quadrant_light(10, :, :, :) = quadrant_light(10, :, :, :)/quadrant_light(1, :, :, :)
            quadrant_light(11, :, :, :) = quadrant_light(11, :, :, :)/quadrant_light(1, :, :, :)
            quadrant_light(12, :, :, :) = quadrant_light(12, :, :, :)/quadrant_light(1, :, :, :)
            quadrant_light(13, :, :, :) = quadrant_light(13, :, :, :)/quadrant_light(1, :, :, :)
        end where

        ! Properly normalize the light
        ! by dividing by the total number of photons
        ! contributing to each grid element.

        norm = sum(quadrant_light(1, :, :, :))

        where (quadrant_light(1, :, :, :) /= 0.0_dp)
            quadrant_light(1, :, :, :) = quadrant_light(1, :, :, :)/norm
            quadrant_light(14, :, :, :) = quadrant_light(14, :, :, :)/norm ! orbtype
            quadrant_light(15, :, :, :) = quadrant_light(15, :, :, :)/norm ! orbtype
            quadrant_light(16, :, :, :) = quadrant_light(16, :, :, :)/norm ! orbtype
        end where

        ! write the light quadrant information
        write (unit=hdl) quadrant_light(:, :, :, :)

    end subroutine qgrid_write

end module quadrantgrid
