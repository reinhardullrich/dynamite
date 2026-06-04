! Split from orblib_f_new_mirror.f90 without changing module names.

module projection
    ! module doing the circular projection of the orbit.
    use numeric_kinds
    implicit none
    private

    ! Number of projections around axis
    integer(kind=i4b), private :: proj_number

    ! Readin the number of rotation to be done.
    public :: projection_setup
    ! Inactive direction-switch helper is kept below as comments.

    ! stop projection module
    public :: projection_stop

    ! Project pos(3,:),vel(3,:) to proj(2,:),lofvel(:)
    ! Using the n'th projection
    private :: project_n

    ! Project pos(3,:),vel(3,:) to proj(2,:),lofvel(:)
    !Done is set to .true. if all projections are finished
    public :: project

    ! amount of symmetry multipication. ( for triaxial galaxies there are
    ! 8 symmetries per orbit, but we do one (1) at a time.)
    integer(kind=i4b), public, parameter :: projection_symmetry = 1

    real(kind=dp), public :: theta_proj, phi_proj, psi_proj

contains

    !++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    subroutine projection_setup()
        use initial_parameters, only: theta_view, phi_view, psi_view
        !----------------------------------------------------------------------
        print *, "  ** Projection setup"
        print *, "  * 8 Projections for Triaxial model"
        proj_number = 8
        print *, "  * Inclination of the model is (theta,phi): ", theta_view, phi_view, psi_view
        theta_proj = theta_view
        phi_proj = phi_view
        psi_proj = psi_view
        print *, theta_proj, phi_proj, psi_proj
        print *, "  ** Projection setup finished"

    end subroutine projection_setup

    ! INACTIVE LEGACY ROUTINE: Inactive direction-switch helper: active direct orbit-library loop does not call it.
    ! Retained as comments for reference; do not call from active direct ABI path.
!     subroutine projection_change_direction()
!         !----------------------------------------------------------------------
!         real(kind=dp)              :: t1, t2, t3
!         print *, "  ** Projection change direction"
!         print *, "  * deprojection angles are (theta,phi,psi): ", &
!             theta_proj/(pi_d/180.0_dp), phi_proj/(pi_d/180.0_dp), &
!             psi_proj/(pi_d/180.0_dp)
!         print *, "  * Give new angles (theta, phi, psi):"
!         print *, "  * Anwser -501 0 0 to keep current values"
!         read *, t1, t2, t3
!         print *, t1, t2, t3
!         if (t1 > -500) then
!             theta_proj = t1*(pi_d/180.0_dp)
!             phi_proj = t2*(pi_d/180.0_dp)
!             psi_proj = t3*(pi_d/180.0_dp)
!         end if
!         print *, "  * New deprojection angles are (theta,phi,psi): ", &
!             theta_proj/(pi_d/180.0_dp), phi_proj/(pi_d/180.0_dp), &
!             psi_proj/(pi_d/180.0_dp)
! 
!         print *, theta_proj, phi_proj, psi_proj
! 
!     end subroutine projection_change_direction

    !++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    subroutine projection_stop()
        !----------------------------------------------------------------------
        ! empty function

    end subroutine projection_stop

    !++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    subroutine project_n(type, pos, vel, proj, losvel, n)
      use initial_parameters, only :  Omega ! (BT)
        ! use initial_parameters, only : theta_view, phi_view
        ! pos( :, (r,z) )
        real(kind=dp), intent(in), dimension(:, :)   :: pos
        ! vel (:, (r,z,theta))
        real(kind=dp), intent(in), dimension(size(pos, 1), 3) :: vel
        ! proj(:,(x',y'))
        real(kind=dp), intent(out), dimension(size(pos, 1), 2)           :: proj
        ! losvd (:)
        real(kind=dp), intent(out), dimension(size(pos, 1))             :: losvel
        integer(kind=i4b), intent(in)                       :: type, n
        !----------------------------------------------------------------------
        real(kind=dp)              :: t1, t2, t3, theta, phi

        real (kind=dp),dimension(3,8,5) ::vsgn          ! (BT)
        real (kind=dp),dimension(3,8) ::psgn            ! (BT)

        ! Signs of the (vx,vy,vz) for each Projection and type of Orbit
        real(kind=dp), dimension(3, 8, 5), &
            parameter :: vsgn1 = reshape((/ &
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

        !Signs of the x,y,z for each projection  :psgn( [x,y,z], project )
        real(kind=dp), dimension(3, 8), &
            parameter :: psgn1 = reshape((/ &
                                        1, 1, 1, -1, 1, 1, -1, -1, 1, 1, -1, 1, &
                                        1, 1, -1, -1, 1, -1, -1, -1, -1, 1, -1, -1/), (/3, 8/))


        ! Signs of the (vx,vy,vz) for each Projection and type of Orbit
        ! (BT) 4-fold symmetry same as before
        real (kind=dp),dimension(3,8,5),parameter :: vsgn2= reshape((/  &
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
        !Signs of the x,y,z for each projection  :psgn( [x,y,z], project )
        real (kind=dp),dimension(3,8),parameter :: psgn2= reshape((/  &
             1 , 1 , 1   , 1 , 1 , 1   , -1 , -1 , 1 ,  -1 , -1 , 1 , &
             1 , 1 ,-1   , 1 , 1 ,-1  , -1 , -1 ,-1 ,  -1 , -1 ,-1 /),(/3,8/))

        ! Use 8-fold for non-rotating, but 4-fold for rotating (BT)
        vsgn=vsgn1
        psgn=psgn1
        if (Omega /= 0.0_dp ) then
           vsgn=vsgn2
           psgn=psgn2
        endif

        theta = theta_proj
        phi = phi_proj

        ! check orbit type
        if (type > 5 .or. type < 1) stop "project_n: Wrong orbit type"

        ! Use sign matrix for the symmetries.
        ! Using the inverse (transpose) of the projection (eq. 4) of Thesis Ellen.

        ! x'
        t1 = -sin(phi)*psgn(1, n)
        t2 = cos(phi)*psgn(2, n)
        proj(:, 1) = t1*pos(:, 1) + t2*pos(:, 2)

        ! y'
        t1 = -cos(theta)*cos(phi)*psgn(1, n)
        t2 = -cos(theta)*sin(phi)*psgn(2, n)
        t3 = sin(theta)*psgn(3, n)
        proj(:, 2) = t1*pos(:, 1) + t2*pos(:, 2) + t3*pos(:, 3)

        ! v_LOS
        t1 = sin(theta)*cos(phi)*vsgn(1, n, type)
        t2 = sin(theta)*sin(phi)*vsgn(2, n, type)
        t3 = cos(theta)*vsgn(3, n, type)
        losvel(:) = t1*vel(:, 1) + t2*vel(:, 2) + t3*vel(:, 3)

        !xaa = (-sin(phi)*x+cos(phi)*y)*sin(psi)-(-cos(theta)*cos(phi)*x-cos(theta)*sin(phi)*y+sin(theta)*z)*cos(psi);
        !yaa = (-sin(phi)*x+cos(phi)*y)*cos(psi)+(-cos(theta)*cos(phi)*x-cos(theta)*sin(phi)*y+sin(theta)*z)*sin(psi);

        !  t1 = sin(phi)
        !  t3 = cos(phi)
        !  t5 = -t1*x+t3*y
        !  t6 = sin(psi)
        !  t8 = cos(theta)
        !  t13 = sin(theta)
        !  t15 = -t8*t3*x-t8*t1*y+t13*z
        !  t16 = cos(psi)
        !  v(1) = t5*t6-t15*t16
        !  v(2) = t5*t16+t15*t6

        !  v(1) = x*sin(psi)-y*cos(psi)
        !  v(2) = x*cos(psi)+y*sin(psi)

    end subroutine project_n

    !++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    subroutine project(type, pos, vel, proj, lofvel, done, first)
        integer(kind=i4b), intent(in)                        :: type
        real(kind=dp), intent(in), dimension(:, :) :: pos
        real(kind=dp), intent(in), dimension(size(pos, 1), 3) :: vel
        real(kind=dp), intent(out), dimension(size(pos, 1)*projection_symmetry, 2) &
             & :: proj
        real(kind=dp), intent(out), dimension(size(pos, 1)*projection_symmetry) &
             & :: lofvel
        logical, intent(out)                          :: done
        logical, intent(in)                          :: first
        !----------------------------------------------------------------------
        integer(kind=i4b), save :: count = 0

        ! reset counter if this is the first projection for this orbit
        if (first) count = 0
        count = count + 1
        done = .false.

        if (count <= proj_number) then
            call project_n(type, pos, vel, proj, lofvel, count)
        else
            count = proj_number + 1
            done = .true.
            proj(:, :) = 0.0_dp
            lofvel(:) = 0.0_dp
        end if

    end subroutine project

end module projection
